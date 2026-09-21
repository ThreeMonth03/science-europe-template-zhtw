"""Bounded structural/Pandoc controls; these are not native page acceptance."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from bs4 import BeautifulSoup
from jinja2 import ChoiceLoader, DictLoader, Environment, FileSystemLoader
from markupsafe import Markup

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from mixed_budget_trial import TABLE, fragments


def recipe():
    spec = importlib.util.spec_from_file_location('large_groups_recipe', Path(__file__).with_name('prototype.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def units(blocks):
    values = []
    for block in blocks:
        if block['t'] == 'Div':
            values.extend({'t': 'Div', 'c': [copy.deepcopy(block['c'][0]), [child]]} for child in units(block['c'][1]))
        else: values.append(copy.deepcopy(block))
    return values


def expand(table):
    result = []; pending = []
    def flush():
        if pending:
            item = copy.deepcopy(table); item['c'][4][0][3] = copy.deepcopy(pending)
            result.append(item); pending.clear()
    for row in table['c'][4][0][3]:
        parts = units(row[1][0][4][1:])
        if len(parts) < 12:
            if len(pending) == 32: flush()
            pending.append(row); continue
        flush(); item = copy.deepcopy(table); out = item['c']
        out[0][1].append('long-resource-table'); out[0][2].append(['custom-style', 'PilotLongBudget'])
        identity = copy.deepcopy(row); identity[1][0][4] = [copy.deepcopy(row[1][0][4][0])]
        out[3][1] = [copy.deepcopy(table['c'][3][1][0]), identity]; out[4][0][3] = []
        for part in parts:
            cell = copy.deepcopy(row[1][0]); cell[3] = 3; cell[4] = [part]
            out[4][0][3].append([copy.deepcopy(row[0]), [cell]])
        result.append(item)
    flush(); return result


def expected(node):
    if isinstance(node, list):
        result = []
        for value in node:
            if isinstance(value, dict) and value.get('t') == 'Table': result.extend(expand(value))
            else: result.append(expected(value))
        return result
    if isinstance(node, dict): return {k: expected(v) for k, v in node.items()}
    return node


def pdf_controls(english):
    r = recipe()
    sys.path.insert(0, str(ROOT / 'experiments/mixed-budget-header'))
    from prototype import patch_budget
    old = patch_budget((english / 'src/budget-reading.html.j2').read_text())
    patched = old.replace(r.COUNT, r.PER_ROW, 1).replace(r.SHORT, r.BATCHED, 1)
    env = Environment(loader=ChoiceLoader([DictLoader({'src/budget-reading.html.j2': patched}), FileSystemLoader(english)]),
                      extensions=['jinja2.ext.do'], autoescape=True)
    render = env.get_template('src/budget-reading.html.j2').module.render
    base = BeautifulSoup((ROOT / 'reviews/2026-09-21-mixed-boundary-controls/after/renders/mixed-bound-33-last-review-english.html').read_text(), 'html.parser')
    original_rows = base.select('.resource-table tbody > tr')
    results = []
    for count in [32, 33, 34, 64, 65, 66]:
        soup = copy.deepcopy(base); tbody = soup.select_one('.resource-table tbody'); tbody.clear()
        for n in range(count - 1):
            row = copy.deepcopy(original_rows[0]); row['data-item-id'] = f'owned-{n}'
            row.select_one('strong').string = f'Owned resource [{n}]'; tbody.append(row)
        tbody.append(copy.deepcopy(original_rows[-1]))
        source = str(soup); match = list(TABLE.finditer(source)); assert len(match) == 1
        header, rows = fragments(match[0][0])
        result = BeautifulSoup(str(render(Markup(match[0][0]), header, rows)), 'html.parser')
        ordinary = result.select('table:not(.pdf-resource-reading)')
        assert [len(t.select('tbody > tr')) for t in ordinary] == [min(32, count - 1 - i) for i in range(0, count - 1, 32)]
        assert len(result.select('.pdf-resource-reading')) == 1
        assert [tr['data-item-id'] for t in ordinary for tr in t.select('tbody > tr')] == [f'owned-{n}' for n in range(count - 1)]
        assert all([c.get_text() for c in t.select('thead th')] == [c.get_text() for c in soup.select('.resource-table thead th')] for t in ordinary)
        results.append(dict(resources=count, ordinary_groups=[len(t.select('tbody > tr')) for t in ordinary], expanded_long=1))
    return results


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--english', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); assert not a.output.exists(); a.output.mkdir(parents=True)
    sys.path.insert(0, str(a.english.resolve() / 'scripts'))
    from probe_budget_word import RUNNER, IMAGE, fixture
    from probe_long_budget_word import cases, HANDLER
    tests = [(n, h, True if n == 'too-many-resources' else ok) for n, h, ok in cases()]
    for count in [32, 33, 34, 64, 65, 66]:
        soup = BeautifulSoup(fixture(rows=count), 'html.parser')
        last = soup.select('tbody tr')[-1].select_one('.answer-detail')
        for n in range(20):
            node = soup.new_tag('p'); node.string = f'Original detail [{n}].'; last.append(node)
        tests.append((f'mixed-{count}', str(soup), True))
    large = next(h for n, h, _ in tests if n == 'mixed-65')
    tests += [('large-invalid-metadata', large.replace('Institute.', '<ul><li>Funder.</li></ul>', 1), False),
              ('large-invalid-purpose', large.replace('Original detail [0].', '<img src="no-fetch.png" alt="Keep">'), False),
              ('large-no-long', fixture(rows=65), False)]
    old = (a.english / 'src/word/pilot.lua').read_text(); revised = recipe().patch_word(old)
    html = ''.join('<div id="' + n + '">' + h + '</div>' for n, h, _ in tests)
    outputs = []
    for name, lua in [('disabled', old.replace(HANDLER, '')), ('before', old), ('after', revised)]:
        ast = json.loads(subprocess.check_output(['docker', 'run', '--rm', '--network', 'none', '-i', '--entrypoint', 'python', IMAGE, '-c', RUNNER],
                          input=json.dumps(dict(lua=lua, html=html)).encode()))
        outputs.append({b['c'][0][0]: b for b in ast['blocks']})
        (a.output / (name + '.json')).write_text(json.dumps(outputs[-1], ensure_ascii=False, separators=(',', ':')) + '\n')
    rows = []
    for name, _, eligible in tests:
        disabled, before, after = [o[name] for o in outputs]
        assert after == (expected(disabled) if eligible else disabled), name
        if name != 'too-many-resources' and not name.startswith('mixed-'):
            assert before == after, ('Historical safety guard changed', name)
        rows.append(dict(case=name, eligible=eligible, changed_from_previous=before != after, passed=True))
    report = dict(passed=True, native_export=False, release_acceptance=False, rows=rows,
        pdf_groups=pdf_controls(a.english), checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        worker_image=IMAGE, recipe_sha256=hashlib.sha256(Path(__file__).with_name('prototype.py').read_bytes()).hexdigest())
    (a.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(passed=True, pandoc_cases=len(rows), pdf_group_cases=len(report['pdf_groups']))))


if __name__ == '__main__': main()
