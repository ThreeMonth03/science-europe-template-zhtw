"""Source-level marked-notice trial; never filter rendered HTML or user answers.

Only the frozen 0.3.43 packages are inputs. Unmarked placeholders are deliberately
outside this trial, and neither package version nor committed source is changed.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from artifact_utils import sha

BASE = {'english.zip': '7694516b1e279e2e50771c888c9f8034c24e66c02125f5a46d5a7defd38e8357',
        'chinese.zip': '9b4ca1638ae35067c13efb78622689abc07feb2416b772132c273671274c0403'}
GAP = re.compile(r'<p\b[^>]*class="data-gap[^\"]*"[^>]*>.*?</p>', re.S)
START = "{% if output_profile|default('review') != 'submission' %}"
END = '{% endif %}'
FILES = ('src/questions/', 'src/quality-control.html.j2', 'src/post-project-archive.html.j2',
         'src/preservation-publication-reason.html.j2')
PHRASES = {
    'english': {'restrictions': 'Restrictions apply to this dataset.',
                'software': 'Software is required to use this dataset.',
                'quality-other': 'Other quality control methods are planned for <strong>{{ qualityName }}</strong>.'},
    'chinese': {'restrictions': '此資料集有使用限制。',
                'software': '使用此資料集需要軟體工具。',
                'quality-other': '本計畫將對 <strong>{{ qualityName }}</strong> 採取其他品質管控方法。'},
}


def summary(name, source, language):
    """Keep affirmative facts that happen to share a paragraph with a notice."""
    fact = re.search(r'data-fact-id="([^"]+)"', source)
    fact = fact[1] if fact else None
    if name == 'src/quality-control.html.j2' and fact == 'quality-other':
        return '<p class="quality-summary" data-fact-id="quality-other" data-status="partial">' + PHRASES[language]['quality-other'] + '</p>'
    if name == 'src/quality-control.html.j2' and fact == 'quality-control':
        # A name is context, not an affirmative quality-control decision.
        return '<p class="quality-context"><strong>{{ qualityName }}</strong></p>'
    if name == 'src/questions/12-access-data.html.j2' and fact == 'required-software-list':
        return '<p data-requirement-id="SE-5c" data-fact-id="required-software-list" data-status="partial">' + PHRASES[language]['software'] + '</p>'
    if name == 'src/questions/01-how-data.html.j2' and fact is None:
        assert 'data-status="missing-output"' in source
        return '<p data-fact-id="reuse-restrictions" data-status="partial">' + PHRASES[language]['restrictions'] + '</p>'
    return ''


def patch_source(name, source, language):
    if not name.startswith(FILES): return source, []
    operations = []
    for match in GAP.finditer(source):
        original = match[0]
        alternate = summary(name, original, language)
        replacement = START + original + ('{% else %}' + alternate if alternate else '') + END
        operations.append(dict(start=match.start(), end=match.end(), before=original, after=replacement,
                               retained_fact=bool(alternate), kind='marked-notice'))
    if name == 'src/questions/02-what-data.html.j2':
        values = list(re.finditer(r'<p class="collection-summary">.*?</p>', source, re.S))
        missing = [m for m in values if 'collectionSentences' not in m[0]]
        assert len(missing) == 1
        match = missing[0]
        replacement = START + match[0] + '{% else %}<p class="collection-context"><strong>{{ collectionName }}</strong></p>' + END
        operations.append(dict(start=match.start(), end=match.end(), before=match[0], after=replacement,
                               retained_fact=True, kind='unmarked-collection-context'))
    result = source
    for op in sorted(operations, key=lambda op: op['start'], reverse=True):
        assert result[op['start']:op['end']] == op['before']
        result = result[:op['start']] + op['after'] + result[op['end']:]
    return result, operations


def patch(data, language):
    result = copy.deepcopy(data); inventory = {}
    assert data['version'] == '0.3.43'
    for file in result['files']:
        file['content'], operations = patch_source(file['fileName'], file['content'], language)
        if operations: inventory[file['fileName']] = operations
    return result, inventory


def project(data, inventory):
    result = copy.deepcopy(data)
    files = {f['fileName']: f for f in result['files']}
    for name, operations in inventory.items():
        # Derive new offsets from the original offsets, not fuzzy text matching.
        ordered = sorted(operations, key=lambda op: op['start']); delta = 0; spans = []
        for op in ordered:
            spans.append((op['start'] + delta, op)); delta += len(op['after']) - len(op['before'])
        value = files[name]['content']
        for start, op in reversed(spans):
            assert value[start:start + len(op['after'])] == op['after']
            value = value[:start] + op['before'] + value[start + len(op['after']):]
        files[name]['content'] = value
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); assert not a.output.exists()
    manifest = json.loads((a.baseline / 'manifest.json').read_text())
    assert manifest['status'] == 'runtime-experiment' and manifest['source']['version'] == '0.3.43'
    assert manifest['runtime_variant']['name'] == 'python-markdown-tables'
    a.output.mkdir(parents=True)
    report = dict(prototype_only=True, release_acceptance=False, global_switch_complete=False,
                  source_repo_modified=False, translation_tree_modified=False, version_modified=False,
                  recipe_sha256=sha(Path(__file__)), packages={})
    for language in ['english', 'chinese']:
        name = language + '.zip'; assert sha(a.baseline / name) == BASE[name]
        with zipfile.ZipFile(a.baseline / name) as before, zipfile.ZipFile(a.output / name, 'w') as after:
            old = json.loads(before.read('template/template.json')); new, inventory = patch(old, language)
            assert project(new, inventory) == old, 'Unrelated package change'
            for entry in before.infolist():
                value = before.read(entry.filename)
                if entry.filename == 'template/template.json':
                    value = json.dumps(new, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
                after.writestr(entry, value)
        report['packages'][name] = dict(baseline_sha256=BASE[name], sha256=sha(a.output / name), operations=inventory)
        manifest['sha256'][name] = report['packages'][name]['sha256']
    manifest.update(prototype=report, baseline_build=str(a.baseline.resolve()))
    # These are patched packages, not the runtime-copy helper's identical candidate.
    manifest.pop('identical_package_sha256', None)
    (a.output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    (a.output / 'prototype.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(a.output)


if __name__ == '__main__': main()
