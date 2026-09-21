"""Review five exact prose units and package the isolated full-source rehearsal."""
import argparse
from collections import Counter
from dataclasses import asdict
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile
import yaml
from asset_recipe import ROOT, HERE, XML, LUA, baseline, helper, patch, sha
from source_rehearsal import write, git, ENGLISH_COMMIT, TOOL_COMMIT
from dsw_document_template_tool.translation_tree import sync_translation_tree, audit_translation_tree, audit_translated_template_structure
from dsw_document_template_tool._translation_tree.document import parse_translation_document, parse_sentence_text
from dsw_document_template_tool._translation_tree.manifest import load_tree_manifest

sys.path.insert(0, str(ROOT / 'scripts'))
from build import package_timestamp, localize_format_names
from artifact_utils import canonicalize_zip
from probe_pdf_budget_translation import pair

TRANSLATIONS = {
    'Project {index}': '計畫 {index}',
    'Resource {index}': '資源 {index}',
    'Software tool {index}': '軟體工具 {index}',
    'An alternative legal basis was selected.': '本計畫已選擇其他法律依據。',
    '(no name given)': '（計畫名稱尚未提供）',
}
REMOVED = ('(no name given) {projectItemNumberReply}', '（計畫名稱尚未提供）{projectItemNumberReply}')


def finish(english, tooling, output):
    assert git(english, 'rev-parse', 'HEAD') == ENGLISH_COMMIT and git(tooling, 'rev-parse', 'HEAD') == TOOL_COMMIT
    assert not (output / 'reviewed').exists() and not (output / 'translated').exists()
    preflight = json.loads((output / 'translation-preflight.json').read_text())
    proof = json.loads((output / 'source-proof.json').read_text())
    adapted = bool(proof.get('source_adaptations'))
    translations = dict(TRANSLATIONS)
    before = Counter(pair(p.read_text()) for p in (ROOT / 'translation/tree').rglob('translation.md'))
    duplicate_recovery = {}
    if adapted:
        translations.pop('(no name given)')
        translations['Project {i}{projectItemNumberReply}'] = '計畫 {i}{projectItemNumberReply}'
        for sentence in ['Currency: {projectCostItemCurrencyReply}.', 'Information not provided: how this cost will be covered.']:
            values = {target for source, target in before if source == sentence}
            assert len(values) == 1, 'Only identical reviewed translations may resolve duplicate-unit migration'
            duplicate_recovery[sentence] = values.pop()
    expected_blanks = Counter(translations.keys())
    if adapted:
        expected_blanks.update({'Currency: {projectCostItemCurrencyReply}.': 3,
                               'Information not provided: how this cost will be covered.': 2})
    assert Counter(v['sentence'] for v in preflight['blanks']) == expected_blanks
    reviewed = output / 'reviewed'; shutil.copytree(output / 'merged', reviewed)
    for unit in preflight['blanks']:
        path = reviewed / unit['document_path']; text = path.read_text()
        assert text.count('~~~jinja\n\n~~~') == 1
        value = {**translations, **duplicate_recovery}[unit['sentence']]
        path.write_text(text.replace('~~~jinja\n\n~~~', '~~~jinja\n' + value + '\n~~~', 1))
    issues = audit_translation_tree(tree_dir=reviewed, source_dir=output / 'expanded'); assert not issues
    after = Counter(pair(p.read_text()) for p in (reviewed / 'tree').rglob('translation.md'))
    assert sum(before.values()) == 762 and sum(after.values()) == (767 if adapted else 766)
    assert before - after == (Counter() if adapted else Counter({REMOVED: 1}))
    assert after - before == Counter(translations.items())
    assert sum((before & after).values()) == (762 if adapted else 761)
    translation_proof = dict(before_units=762, after_units=sum(after.values()), retained_pairs=sum((before & after).values()),
        removed=[] if adapted else [list(REMOVED)], added=[list(p) for p in translations.items()],
        duplicate_recovery=duplicate_recovery,
        original_tree_sha256={str(p.relative_to(ROOT / 'translation')): sha(p.read_bytes()) for p in (ROOT / 'translation').rglob('translation.md')},
        reviewed_tree_sha256={str(p.relative_to(reviewed)): sha(p.read_bytes()) for p in reviewed.rglob('translation.md')})
    write(output, 'translation-delta.json', translation_proof)
    config = yaml.safe_load((ROOT / 'pipeline.yml').read_text()); target = config['translation']
    translated = output / 'translated'
    sync_translation_tree(tree_dir=reviewed, source_dir=output / 'expanded', output_dir=translated,
        source_lang='en', target_lang='zh_Hant', template_organization_id=target['organization_id'],
        template_id=target['template_id'], template_name=target['name'], template_version=str(target['version']),
        public_readme_path=ROOT / 'PACKAGE_README.md')
    metadata = json.loads((translated / 'template.json').read_text())
    localize_format_names(metadata, target['format_names']); write(translated, 'template.json', metadata)
    issues = audit_translated_template_structure(source_dir=output / 'expanded', output_dir=translated)
    write(output, 'structure-audit.json', [asdict(v) for v in issues]); assert not issues
    for name in [LUA, XML]:
        assert (output / 'source' / name).read_bytes() == (translated / name).read_bytes()
    units = load_tree_manifest(reviewed)['units']; assert len(units) == sum(after.values())
    assert all(parse_translation_document(document_path=reviewed / u['document_path'], source_lang='en', target_lang='zh_Hant').strip() for u in units)
    packages = {}; timestamp = package_timestamp(english)
    for language, folder in [('english', 'en'), ('chinese', 'translated')]:
        prepared = output / folder; package = output / (language + '.zip'); assert not package.exists()
        for command in [['verify', str(prepared)], ['package', str(prepared), '--output', str(package)]]:
            result = subprocess.run([str(tooling / '.venv/bin/dsw-tdk'), '--no-config', *command], capture_output=True, text=True)
            with (output / (language + '-build.log')).open('a') as stream: stream.write(result.stdout + result.stderr)
            assert result.returncode == 0, result.stdout + result.stderr
        canonicalize_zip(package, timestamp)
        with zipfile.ZipFile(package) as z:
            data = json.loads(z.read('template/template.json')); expected = patch(baseline(language), language)
            actual_files = {f['fileName']: f['content'] for f in data['files']}
            wanted_files = {f['fileName']: f['content'] for f in expected['files']}
            assert actual_files.keys() == wanted_files.keys()
            assert XML not in actual_files and z.read('template/assets/' + XML) == helper()
            assert next(a for a in data['assets'] if a['fileName'] == XML)['contentType'] == 'application/xml'
            differences = [n for n in actual_files if actual_files[n] != wanted_files[n]]
            if language == 'english':
                projected = dict(actual_files)
                for name, operation in proof.get('source_adaptations', {}).items():
                    assert projected[name].count(operation['after']) == 1
                    projected[name] = projected[name].replace(operation['after'], operation['before'], 1)
                assert projected == wanted_files, 'English adaptation must reverse to exact native prototype'
            packages[language] = dict(sha256=sha(package.read_bytes()), changed_jinja_vs_prototype=differences,
                asset_sha256={n: sha(z.read(n)) for n in z.namelist() if n.startswith('template/assets/')})
    result = dict(passed=True, full_source_rehearsal=True, source_integrated=False, native_checked=False,
        source_version='0.3.44', package_timestamp=timestamp, machine_helper_translation_units=0,
        translation_units=len(units), retained_translation_pairs=sum((before & after).values()), packages=packages,
        checker_sha256=sha(Path(__file__).read_bytes()), release_acceptance=False)
    write(output, 'source-build.json', result)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['english', 'tooling', 'output']: p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args(); print(json.dumps(finish(a.english.resolve(), a.tooling.resolve(), a.output.resolve()), ensure_ascii=False))
