"""Explicit local-only package prototype; never a source release or a new version."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import zipfile

BASELINE_SHA = {
    'english.zip': '8e8d036c2623fed7a58035112a6d59d20f3a86ee32fcd36af55a14f32ac43387',
    'chinese.zip': '14aa9f648afb1e295d4066b2eb41db0ccb1db1f26d8c067169d6d8262d4db26d',
}
ORDINARY = '''{%- macro ordinary(header, rows) -%}
<table class="resource-table"><colgroup><col class="resource-purpose"><col class="resource-budget"><col class="resource-funding"></colgroup><thead>{{ header }}</thead><tbody>{% for row in rows %}{{ row.original }}{% endfor %}</tbody></table>
{%- endmacro -%}'''
SHORT = ORDINARY.replace(
    '<table class="resource-table">', '{%- set original -%}<table class="resource-table">', 1).replace(
    '\n{%- endmacro -%}', '''{%- endset -%}
{%- import 'src/pdf/short-resource-rows.html.j2' as shortRows -%}
{{- shortRows.table(original, rows) -}}
{%- endmacro -%}''', 1)
BODY = '</tr></thead><tbody><tr><td colspan="3">{{ row.purpose }}'
KEPT_BODY = BODY.replace('<tbody>', '<tbody style="break-inside: avoid">', 1)
TAIL = '\n/* Local prototype: keep the final purpose fragment with its allocation. */\nhtml body .pdf-resource-reading tbody > tr > td > .answer-detail[data-fact-id="resource-justification"] { break-after: avoid; }\n'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def patch_budget(source):
    assert source.count(ORDINARY) == source.count(BODY) == 1
    result = source.replace(ORDINARY, SHORT, 1).replace(BODY, KEPT_BODY, 1)
    assert project_budget(result) == source
    return result


def project_budget(source):
    assert source.count(SHORT) == source.count(KEPT_BODY) == 1
    return source.replace(SHORT, ORDINARY, 1).replace(KEPT_BODY, BODY, 1)


def patch_package(data):
    result = copy.deepcopy(data)
    files = {f['fileName']: f for f in result['files']}
    assert len(files) == len(result['files'])
    files['src/budget-reading.html.j2']['content'] = patch_budget(files['src/budget-reading.html.j2']['content'])
    assert TAIL not in files['src/layout.css']['content']
    files['src/layout.css']['content'] += TAIL
    projected = copy.deepcopy(result)
    restore = {f['fileName']: f for f in projected['files']}
    restore['src/budget-reading.html.j2']['content'] = project_budget(restore['src/budget-reading.html.j2']['content'])
    restore['src/layout.css']['content'] = restore['src/layout.css']['content'][:-len(TAIL)]
    assert projected == data, 'Every other package field and file must remain unchanged'
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--without-capture', action='store_true',
                   help='Native control run on the same tables-only worker, without the mixed-only observer')
    a = p.parse_args()
    assert not a.output.exists()
    manifest = json.loads((a.baseline / 'manifest.json').read_text())
    assert manifest['status'] == 'candidate'
    assert manifest['source']['version'] == manifest['translation']['version'] == '0.3.42'
    for name, expected in BASELINE_SHA.items():
        assert digest((a.baseline / name).read_bytes()) == expected
    a.output.mkdir(parents=True)
    report = {'prototype_only': True, 'release_acceptance': False, 'source_repo_modified': False,
              'version_modified': False, 'baseline_package_sha256': BASELINE_SHA,
              'recipe_sha256': digest(Path(__file__).read_bytes()), 'packages': {}}
    for name in BASELINE_SHA:
        with zipfile.ZipFile(a.baseline / name) as before, zipfile.ZipFile(a.output / name, 'w') as after:
            original = json.loads(before.read('template/template.json'))
            patched = patch_package(original)
            for entry in before.infolist():
                value = before.read(entry.filename)
                if entry.filename == 'template/template.json':
                    value = json.dumps(patched, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
                after.writestr(entry, value)
        report['packages'][name] = {'sha256': digest((a.output / name).read_bytes()),
            'changed_files': ['src/budget-reading.html.j2', 'src/layout.css']}
    manifest.update(status='runtime-experiment', release_acceptance=False,
                    prototype=report, baseline_build=str(a.baseline.resolve()))
    for name, row in report['packages'].items():
        manifest['sha256'][name] = row['sha256']
    manifest['runtime_variant'] = {'name': 'python-markdown-tables' if a.without_capture else 'tables-only-with-capture-observer',
        'capture_observer_attached': not a.without_capture,
        'image_id': 'sha256:6d3cbcab3294e760a4d92e27bec72d4fb23a0adb2cc1734d981478688741ab11'}
    (a.output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    (a.output / 'prototype.json').write_text(json.dumps(report, indent=2) + '\n')
    print(a.output)


if __name__ == '__main__':
    main()
