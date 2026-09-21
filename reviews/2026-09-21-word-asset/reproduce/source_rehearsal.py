"""Full-source translation rehearsal in fresh output folders, not source edits."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import shutil
import subprocess
import sys
from asset_recipe import ROOT, HERE, ARCHIVE, LUA, XML, OLD_XML, WORD_FORMATS, baseline, helper, patch, sha
from dsw_document_template_tool.template_transform import expand_template_dir
from dsw_document_template_tool.translation_tree import export_translation_tree, merge_translation_tree, audit_translation_tree
from dsw_document_template_tool._translation_tree.manifest import load_tree_manifest
from dsw_document_template_tool._translation_tree.document import parse_translation_document, parse_sentence_text

ENGLISH_COMMIT = '41bb0ac59e86f5591b641a001a04240375426545'
TOOL_COMMIT = '25e339fbdfb1d20796471055790aad6a4226b6ed'
FILES = ['src/macros.html.j2', 'src/projects.html.j2', 'src/questions/09-ethical-issues.html.j2',
         'src/questions/12-access-data.html.j2', 'src/questions/15-required-resources.html.j2']


def git(root, *args): return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


def write(root, name, value):
    path = root / name; path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def adapt_prose(source):
    """Expose named sentence lists and whole label branches to the translator."""
    operations = {}
    path = source / 'src/questions/09-ethical-issues.html.j2'; value = path.read_text()
    before = "<div class=\"answer-detail\"><p class=\"answer-lead\" style=\"margin-bottom: 0\">{{ sentences[:ethicsLead.first]|join(' ') }}</p>{{ sentences[ethicsLead.first:]|join(' ') }}</div>"
    after = ("{% set ethicsLeadSentences = sentences[:ethicsLead.first] %}{% set ethicsBodySentences = sentences[ethicsLead.first:] %}"
             "<div class=\"answer-detail\"><p class=\"answer-lead\" style=\"margin-bottom: 0\">{{ ethicsLeadSentences|join(' ') }}</p>{{ ethicsBodySentences|join(' ') }}</div>")
    assert value.count(before) == 1; path.write_text(value.replace(before, after, 1))
    operations[str(path.relative_to(source))] = dict(before=before, after=after)
    path = source / 'src/questions/15-required-resources.html.j2'; value = path.read_text()
    condition = "output_profile|default('review') == 'submission' and not projectItemNameReply"
    name = '{{ projectItemNameReply if projectItemNameReply else "(no name given)" }}'
    suffix = '{{ " - " + projectItemNumberReply if projectItemNumberReply}} </strong></p>'
    before = '<p><strong>{% if ' + condition + ' %}{{ macros.projectLabel(projectItems.index(i) + 1) }}{% else %}' + name + '{% endif %}' + suffix
    after = ('{% if ' + condition + ' %}<p><strong>Project {{ projectItems.index(i) + 1 }}' + suffix
             + '{% else %}<p><strong>' + name + suffix + '{% endif %}')
    assert value.count(before) == 1; path.write_text(value.replace(before, after, 1))
    operations[str(path.relative_to(source))] = dict(before=before, after=after)
    return operations


def run(english, tooling, output, adapt=False):
    assert not output.exists()
    assert git(english, 'rev-parse', 'HEAD') == ENGLISH_COMMIT and not git(english, 'status', '--porcelain')
    assert git(tooling, 'rev-parse', 'HEAD') == TOOL_COMMIT and not git(tooling, 'status', '--porcelain')
    assert not git(ROOT, 'status', '--porcelain', '--', 'translation', 'pipeline.yml')
    source = output / 'source'; source.mkdir(parents=True)
    shutil.copytree(english / 'src', source / 'src')
    for name in ['template.json', 'LICENSE']: shutil.copy2(english / name, source / name)
    shutil.copy2(english / 'PACKAGE_README.md', source / 'README.md')
    sys.path.insert(0, str(ROOT / 'experiments/entity-labels'))
    from entity_recipe import baseline as source_baseline
    old = {f['fileName']: f['content'] for f in source_baseline('english')['files']}
    new = {f['fileName']: f['content'] for f in baseline('english')['files']}
    assert sorted(n for n in old if old[n] != new[n]) == sorted(FILES)
    for name in FILES:
        assert (source / name).read_text() == old[name]
        (source / name).write_text(new[name])
    adaptations = adapt_prose(source) if adapt else {}
    (source / LUA).write_bytes((ARCHIVE / 'reproduce/short-tables.lua').read_bytes())
    (source / XML).write_bytes(helper())
    metadata = json.loads((source / 'template.json').read_text()); original = json.loads(json.dumps(metadata))
    target = patch(baseline('english'), 'english')
    for fmt in metadata['formats']:
        if fmt['uuid'] in WORD_FORMATS:
            wanted = next(f for f in target['formats'] if f['uuid'] == fmt['uuid'])
            assert fmt['steps'] == wanted['steps'][:1] + [{**wanted['steps'][1], 'options': {
                **wanted['steps'][1]['options'], 'args': wanted['steps'][1]['options']['args'].removesuffix(' --lua-filter=' + LUA)}}]
            fmt['steps'] = wanted['steps']
    write(source, 'template.json', metadata)
    original_files = {str(p.relative_to(english)): sha(p.read_bytes()) for p in (english / 'src').rglob('*') if p.is_file()}
    candidate_files = {str(p.relative_to(source)): sha(p.read_bytes()) for p in (source / 'src').rglob('*') if p.is_file()}
    assert set(candidate_files) - set(original_files) == {LUA, XML}
    assert {n for n in original_files if original_files[n] != candidate_files[n]} == set(FILES)
    proof = dict(prototype_only=True, source_integrated=False, english_commit=ENGLISH_COMMIT, tooling_commit=TOOL_COMMIT,
        chinese_commit=git(ROOT, 'rev-parse', 'HEAD'), before_source_sha256=original_files, after_source_sha256=candidate_files,
        before_metadata=original, after_metadata=metadata, source_adaptations=adaptations,
        source_script_sha256=sha(Path(__file__).read_bytes()), prepare_layout_sha256=sha((english / 'scripts/prepare_layout.py').read_bytes()))
    write(output, 'source-proof.json', proof)
    font = tooling / 'src/dsw_document_template_tool/resources/fonts/NotoSansTC-Variable.ttf'
    for language in ['en', 'zh-Hant']:
        prepared = output / language; shutil.copytree(source, prepared)
        subprocess.run([sys.executable, str(english / 'scripts/prepare_layout.py'), '--template', str(prepared),
                        '--font', str(font), '--language', language], check=True)
        for license_file in font.parent.glob('*.txt'): shutil.copy2(license_file, prepared / 'src/fonts' / license_file.name)
    expanded = output / 'expanded'; fresh = output / 'fresh'; merged = output / 'merged'
    expand_template_dir(source_dir=output / 'zh-Hant', output_dir=expanded, profile='science-europe')
    export_translation_tree(source_dir=expanded, output_dir=fresh, source_lang='en', target_lang='zh_Hant')
    migration = merge_translation_tree(old_tree_dir=ROOT / 'translation', new_tree_dir=fresh, output_dir=merged,
                                     source_lang='en', target_lang='zh_Hant')
    write(output, 'migration.json', asdict(migration))
    issues = audit_translation_tree(tree_dir=merged, source_dir=expanded)
    write(output, 'translation-audit.json', [asdict(v) for v in issues]); assert not issues
    for name in [LUA, XML]:
        assert (source / name).read_bytes() == (output / 'en' / name).read_bytes() == (expanded / name).read_bytes()
    units = load_tree_manifest(merged)['units']
    assert not any(u['source_file'] in [LUA, XML, OLD_XML] for u in units)
    blanks = []
    for u in units:
        path = merged / u['document_path']
        if not parse_translation_document(document_path=path, source_lang='en', target_lang='zh_Hant').strip():
            blanks.append(dict(document_path=u['document_path'], source_file=u['source_file'],
                sentence=parse_sentence_text(document_path=path, source_lang='en')))
    result = dict(full_source_rehearsal=True, source_integrated=False, translation_units=len(units),
                  machine_helper_translation_units=0, blanks=blanks, native_checked=False)
    write(output, 'translation-preflight.json', result)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['english', 'tooling', 'output']: p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--adapt-prose', action='store_true')
    a = p.parse_args(); print(json.dumps(run(a.english.resolve(), a.tooling.resolve(), a.output.resolve(), a.adapt_prose), ensure_ascii=False))
