"""Local-only row-safe large-budget trial on the exact previous header prototype."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'experiments/mixed-budget-header'))
from prototype import SHORT  # Executed as __main__, imported module is the prior recipe.

COUNT = '{%- if rows|length <= 32 -%}{{ classify(row, result) }}{%- endif -%}'
PER_ROW = '{{ classify(row, result) }}'
BATCHED = SHORT.replace('{%- macro ordinary(header, rows) -%}', '''{%- macro ordinary(header, rows) -%}
{%- if rows|length > 32 -%}
  {%- for group in rows|batch(32) -%}{{ ordinary(header, group) }}{%- endfor -%}
{%- else -%}''', 1).replace('{%- endmacro -%}', '{%- endif -%}\n{%- endmacro -%}', 1)
WORD_COUNT = 'if #rows == 0 or #rows > 32 then return tbl end'
WORD_ROWS = 'if #rows == 0 then return tbl end'
WORD_PENDING = 'if not plans[index].long then pending:insert(row:clone())'
WORD_BATCHED = '''if not plans[index].long then
        if #pending == 32 then flush() end
        pending:insert(row:clone())'''


def digest(value): return hashlib.sha256(value).hexdigest()


def patch(data):
    changed = copy.deepcopy(data)
    files = {f['fileName']: f for f in changed['files']}
    budget = files['src/budget-reading.html.j2']['content']
    assert budget.count(COUNT) == budget.count(SHORT) == 1
    files['src/budget-reading.html.j2']['content'] = budget.replace(COUNT, PER_ROW, 1).replace(SHORT, BATCHED, 1)
    assert project(changed) == data, 'Only the count dispatch and ordinary grouping may change'
    return changed


def project(data):
    restored = copy.deepcopy(data); files = {f['fileName']: f for f in restored['files']}
    budget = files['src/budget-reading.html.j2']['content']
    assert budget.count(PER_ROW) == budget.count(BATCHED) == 1
    files['src/budget-reading.html.j2']['content'] = budget.replace(PER_ROW, COUNT, 1).replace(BATCHED, SHORT, 1)
    return restored


def patch_word(word):
    assert word.count(WORD_COUNT) == word.count(WORD_PENDING) == 1
    result = word.replace(WORD_COUNT, WORD_ROWS, 1).replace(WORD_PENDING, WORD_BATCHED, 1)
    assert result.count(WORD_ROWS) == result.count(WORD_BATCHED) == 1
    assert result.replace(WORD_ROWS, WORD_COUNT, 1).replace(WORD_BATCHED, WORD_PENDING, 1) == word
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); assert not a.output.exists()
    frozen = json.loads((ROOT / 'reviews/2026-09-21-mixed-boundary-controls/provenance/prototype.json').read_text())
    manifest = json.loads((a.baseline / 'manifest.json').read_text())
    assert manifest['status'] == 'runtime-experiment'
    assert manifest['source']['version'] == manifest['translation']['version'] == '0.3.42'
    a.output.mkdir(parents=True)
    report = dict(prototype_only=True, release_acceptance=False, version_modified=False,
                  source_repo_modified=False, recipe_sha256=digest(Path(__file__).read_bytes()), packages={})
    for name in ['english.zip', 'chinese.zip']:
        assert digest((a.baseline / name).read_bytes()) == frozen['packages'][name]['sha256']
        with zipfile.ZipFile(a.baseline / name) as before, zipfile.ZipFile(a.output / name, 'w') as after:
            original = json.loads(before.read('template/template.json')); patched = patch(original)
            for entry in before.infolist():
                value = before.read(entry.filename)
                if entry.filename == 'template/template.json':
                    value = json.dumps(patched, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
                elif entry.filename == 'template/assets/src/word/pilot.lua':
                    value = patch_word(value.decode()).encode()
                after.writestr(entry, value)
        report['packages'][name] = dict(sha256=digest((a.output / name).read_bytes()),
            baseline_sha256=frozen['packages'][name]['sha256'],
            changed_files=['src/budget-reading.html.j2', 'src/word/pilot.lua'])
        manifest['sha256'][name] = report['packages'][name]['sha256']
    manifest.update(prototype=report, baseline_build=str(a.baseline.resolve()))
    (a.output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    (a.output / 'prototype.json').write_text(json.dumps(report, indent=2) + '\n')
    print(a.output)


if __name__ == '__main__': main()
