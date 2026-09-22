"""Translate the English overlay with the pinned normal tools; never patch Chinese Jinja.

Creates unique, non-release package identities in a new output directory. The
production pipeline lock, translation tree, source, layout and archives are not
modified. No project data or network is used by this experiment.
"""
import argparse
from collections import Counter
from dataclasses import asdict
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from artifact_utils import sha, canonicalize_zip
from build import git, localize_format_names
from probe_pdf_budget_translation import pair
from submission_reading_integration import check_package
from dsw_document_template_tool.template_transform import expand_template_dir
from dsw_document_template_tool.translation_tree import (
    export_translation_tree, merge_translation_tree, sync_translation_tree,
    audit_translation_tree, audit_translated_template_structure)
from dsw_document_template_tool._translation_tree.document import (
    parse_sentence_text, parse_translation_document, replace_translation_text)
import dsw_document_template_tool
import yaml


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def translation_delta(before, after):
    words = json.loads((HERE / 'translations.json').read_text())
    old, new = Counter(before), Counter(after)
    assert len(before) == 767 and len(after) == 773
    assert not old - new, 'A previous translation occurrence was changed/lost'
    assert new - old == Counter(words.items()), 'Unexpected translation change'
    return dict(retained=767, added=6, total=773, added_pairs=sorted(words.items()))


def check_baseline(baseline, config):
    """Verify immutable artifacts, not the HEAD of today's experiment branch."""
    manifest = json.loads((baseline / 'manifest.json').read_text())
    assert manifest['status'] == 'candidate'
    assert manifest['source'] == config['source'] and manifest['translation'] == config['translation']
    assert manifest['translation_units'] == 767 and not manifest['untranslated_units']
    assert manifest['translation_tree_sha256'] == {
        str(p.relative_to(ROOT / 'translation')): sha(p) for p in (ROOT / 'translation').rglob('translation.md')}
    for language, folder in [('english', 'en'), ('chinese', 'translated')]:
        path = baseline / (language + '.zip')
        assert sha(path) == manifest['sha256'][path.name]
        check_package(path, baseline / folder, language, manifest['package_timestamp'])


def run(english, tooling, baseline, output):
    assert not output.exists(), 'Never overwrite evidence or previous outputs'
    config = yaml.safe_load((ROOT / 'pipeline.yml').read_text())
    assert git(tooling, 'rev-parse', 'HEAD') == config['tooling']['commit']
    assert not git(tooling, 'status', '--porcelain')
    assert Path(dsw_document_template_tool.__file__).resolve().is_relative_to(tooling / 'src')
    check_baseline(baseline, config)
    sys.path.insert(0, str(english / 'experiments/full-km-followups'))
    from followup_recipe import overlay, BASELINE, INSERTIONS, IDENTIFIER_CSS
    from followup_probe import check
    assert BASELINE == config['source']['commit']
    raw = {str(p.relative_to(english)): p.read_bytes() for p in (english / 'src').rglob('*') if p.is_file()}
    changed = overlay(raw, english)
    output.mkdir(parents=True)
    for name in ['en', 'zh-Hant']:
        shutil.copytree(baseline / name, output / name)
        for filename, value in changed.items():
            if filename in raw and value == raw[filename]: continue
            target = output / name / filename
            if filename == 'src/layout.css':
                # Prepared CSS has deterministic language/font additions.
                # Keep every old byte and append just the reviewed scoped rule.
                value = target.read_bytes() + IDENTIFIER_CSS
            elif filename in raw: assert target.read_bytes() == raw[filename]
            target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(value)
        metadata_path = output / name / 'template.json'
        metadata = json.loads(metadata_path.read_text())
        metadata.update(templateId='science-europe-followups-prototype', version='0.3.46',
            name='Science Europe — full-KM followup prototype (not for submission)')
        write(metadata_path, metadata)
    expanded = output / 'expanded'
    expand_template_dir(source_dir=output / 'zh-Hant', output_dir=expanded,
        profile=config['tooling']['profile'], exclude_profile_paths=tuple(config['tooling']['exclude_profile_paths']))
    export_translation_tree(source_dir=expanded, output_dir=output / 'fresh', source_lang='en', target_lang='zh_Hant')
    tree = output / 'translation'
    report = merge_translation_tree(old_tree_dir=ROOT / 'translation', new_tree_dir=output / 'fresh',
        output_dir=tree, source_lang='en', target_lang='zh_Hant')
    write(output / 'migration.json', asdict(report))
    words = json.loads((HERE / 'translations.json').read_text()); added = []
    for document in tree.rglob('translation.md'):
        translation = parse_translation_document(document_path=document, source_lang='en', target_lang='zh_Hant')
        if translation.strip(): continue
        source = parse_sentence_text(document_path=document, source_lang='en')
        assert source in words, ('Unexpected untranslated unit', source)
        replace_translation_text(document_path=document, target_lang='zh_Hant', translation_text=words[source])
        added.append(source)
    # An identical label may already have a reviewed translation elsewhere.
    # The multiset delta below still verifies all six new occurrences exactly.
    assert not Counter(added) - Counter(words.keys())
    delta = translation_delta([pair(p.read_text()) for p in (ROOT / 'translation').rglob('translation.md')],
                              [pair(p.read_text()) for p in tree.rglob('translation.md')])
    assert not audit_translation_tree(tree_dir=tree, source_dir=expanded)
    sync_translation_tree(tree_dir=tree, source_dir=expanded, output_dir=output / 'translated',
        source_lang='en', target_lang='zh_Hant', template_organization_id=config['translation']['organization_id'],
        template_id='science-europe-followups-prototype-zhtw', template_name='Science Europe 完整問卷分支修補原型（非提交版）',
        template_version='0.3.46', public_readme_path=ROOT / 'PACKAGE_README.md')
    metadata_path = output / 'translated/template.json'
    metadata = json.loads(metadata_path.read_text())
    localize_format_names(metadata, config['translation']['format_names']); write(metadata_path, metadata)
    assert not audit_translated_template_structure(source_dir=expanded, output_dir=output / 'translated')
    previous_manifest = json.loads((baseline / 'manifest.json').read_text())
    result = dict(status='prototype', prototype_only=True, source_integrated=False, release_acceptance=False,
        baseline_source_commit=BASELINE, tooling_commit=config['tooling']['commit'], translation_delta=delta,
        experiment_checkouts={name: dict(commit=git(root, 'rev-parse', 'HEAD'), dirty=bool(git(root, 'status', '--porcelain')))
            for name, root in [('english', english), ('chinese', ROOT)]},
        baseline_packages={n: sha(baseline / n) for n in ['english.zip', 'chinese.zip']},
        changed_source_files=sorted([*INSERTIONS, 'src/layout.css']), added_source_files=sorted(set(changed) - set(raw)),
        checks={}, sha256={}, recipe_sha256=sha(Path(__file__)),
        overlay_sha256={str(p.relative_to(english)): sha(p) for p in (english / 'experiments/full-km-followups').rglob('*') if p.is_file() and '__pycache__' not in p.parts},
        translation_recipe_sha256=sha(HERE / 'translations.json'))
    tdk = tooling / '.venv/bin/dsw-tdk'
    for language, folder in [('english', 'en'), ('chinese', 'translated')]:
        prepared = output / folder
        for operation in [[str(tdk), '--no-config', 'verify', str(prepared)],
                          [str(tdk), '--no-config', 'package', str(prepared), '--output', str(output / (language + '.zip'))]]:
            subprocess.run(operation, check=True, capture_output=True)
        canonicalize_zip(output / (language + '.zip'), previous_manifest['package_timestamp'])
        with zipfile.ZipFile(output / (language + '.zip')) as archive:
            package = json.loads(archive.read('template/template.json'))
            with zipfile.ZipFile(baseline / (language + '.zip')) as old:
                assets = [n for n in archive.namelist() if n != 'template/template.json']
                assert set(assets) == set(old.namelist()) - {'template/template.json'}
                for name in assets:
                    expected = old.read(name) + (IDENTIFIER_CSS if name == 'template/assets/src/layout.css' else b'')
                    assert archive.read(name) == expected, ('Unreviewed asset drift', name)
        sources = {f['fileName']: f['content'] for f in package['files']}
        rows = check(english, sources)
        result['checks'][language] = len(rows)
        result['sha256'][language + '.zip'] = sha(output / (language + '.zip'))
        write(output / (language + '-branch-checks.json'), rows)
    write(output / 'manifest.json', result)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for key in ['english', 'tooling', 'baseline', 'output']: p.add_argument('--' + key, type=Path, required=True)
    a = p.parse_args(); result = run(a.english.resolve(), a.tooling.resolve(), a.baseline.resolve(), a.output.resolve())
    print(json.dumps(dict(passed=True, prototype_only=True, checks=result['checks'], translation_delta=result['translation_delta'])))
