"""Bounded AST/OOXML controls under pinned Pandoc and the actual enrich method."""
import argparse
import base64
import copy
import json
from pathlib import Path
import subprocess
import sys
import zipfile
from lxml import etree
from docx.oxml.ns import qn
from table_recipe import HERE, ROOT, IMAGE, LUA, sha

sys.path.insert(0, str(ROOT / 'scripts'))
from check_submission_preview_native import compare_docx


def table(rows=3, cols=2, value='N/A', extra='', header=True):
    values = [[('Item' if i == 0 else 'Value') if j == 0 and header else value for i in range(cols)] for j in range(rows)]
    def row(cells, tag): return '<tr>' + ''.join('<' + tag + '>' + c + '</' + tag + '>' for c in cells) + '</tr>'
    return '<table' + extra + '>' + ('<thead>' + row(values[0], 'th') + '</thead>' if header else '') + '<tbody>' + ''.join(
        row(v, 'td') for v in values[int(header):]) + '</tbody></table>'


def wrap(value, qid='q-ethical-issues'):
    return '<div id="' + qid + '" class="question"><h3>9. Ethics?</h3><div class="answer"><div class="answer-detail"><p>Before.</p>' + value + '<p>After.</p></div></div></div>'


def cases():
    simple = table()
    return [
        ('short', wrap(simple), 1), ('chinese', wrap(table(value='沿岸觀測資料，0。')), 1),
        ('two-rows', wrap(table(rows=2)), 1), ('four-rows', wrap(table(rows=4)), 1),
        ('four-columns', wrap(table(cols=4)), 1), ('no-header', wrap(table(header=False)), 1),
        ('cell-boundary', wrap(table(value='x ' * 40)), 1), ('cjk-boundary', wrap(table(value='中' * 40)), 1),
        ('cell-too-long', wrap(table(value='x ' * 41)), 0), ('cjk-too-wide', wrap(table(value='中' * 41)), 0),
        ('many-rows', wrap(table(rows=40)), 0), ('five-rows', wrap(table(rows=5)), 0),
        ('five-columns', wrap(table(cols=5)), 0), ('one-row', wrap(table(rows=1)), 0),
        ('one-column', wrap(table(cols=1)), 0), ('large-total', wrap(table(rows=4, cols=4, value='x ' * 39)), 0),
        ('multi-paragraph', wrap(table(value='<p>First.</p><p>Second.</p>')), 0),
        ('list-cell', wrap(table(value='<ul><li>A.</li><li>B.</li></ul>')), 0),
        ('nested-table', wrap(table(value=table(rows=2))), 0),
        ('hard-break', wrap(table(value='First<br>Second')), 0),
        ('code', wrap(table(value='<code>Original.csv</code>')), 0),
        ('rowspan', wrap(simple.replace('<td>N/A</td>', '<td rowspan="2">N/A</td>', 1)), 0),
        ('colspan', wrap(simple.replace('<th>Item</th><th>Value</th>', '<th colspan="2">Item</th>')), 0),
        ('caption', wrap(simple.replace('<table>', '<table><caption>Original.</caption>')), 0),
        ('attributed-table', wrap(table(extra=' data-original="yes"')), 0),
        ('attributed-cell', wrap(simple.replace('<td>', '<td data-original="yes">', 1)), 0),
        ('other-question', wrap(simple, 'q-required-resources'), 0),
        ('nested-answer', wrap('<div>' + simple + '</div>'), 0),
        ('nested-question-lookalike', wrap(wrap(simple)), 0),
        ('other-question-lookalike', '<div class="question" id="q-other">' + wrap(simple) + '</div>', 0),
        ('authored-marker', wrap('<p>&lt;!--DSW:SE:short-table:v1:begin--&gt;</p>' + simple), 1),
        ('html-marker', wrap('<!--DSW:SE:short-table:v1:begin-->' + simple + '<!--DSW:SE:short-table:v1:end-->'), 1),
        ('hyperlink', wrap(table(value='<a href="https://example.org/keep?a=1&amp;b=2">Original.csv</a>')), 1),
        ('inline-emphasis', wrap(table(value='Keep <em>exact</em>: 0 / N/A.')), 1),
        ('long-token', wrap(table(value='a' * 41)), 0),
        ('adjacent-tables', wrap(simple + table(rows=40) + table(rows=2)), 0),
        ('mixed-separated', wrap(simple + '<p>Middle.</p>' + table(rows=40) + '<p>End.</p>' + table(rows=2)), 2),
    ]


def xml_delta(before, after, expected):
    """Independent XML projection: only direct row properties + nonfinal style."""
    a, b = [copy.deepcopy(n) for n in [before, after]]
    changed = 0
    left = list(a.iter(qn('w:tbl'))); right = list(b.iter(qn('w:tbl'))); assert len(left) == len(right)
    for old, new in zip(left, right):
        if etree.tostring(old) == etree.tostring(new): continue
        rows = new.findall(qn('w:tr')); original = old.findall(qn('w:tr'))
        assert 2 <= len(rows) <= 4 and len(rows) == len(original)
        assert len(list(new.iter(qn('w:tbl')))) == 1
        for index, (row, original_row) in enumerate(zip(rows, original)):
            pr = row.find(qn('w:trPr')); assert pr is not None
            keep = pr.findall(qn('w:cantSplit')); assert len(keep) == 1 and not keep[0].attrib and len(keep[0]) == 0
            pr.remove(keep[0])
            if original_row.find(qn('w:trPr')) is None:
                assert not len(pr) and not pr.attrib; row.remove(pr)
            for cell in row.findall(qn('w:tc')):
                assert len(list(cell.iter(qn('w:p')))) == 1
                if index < len(rows) - 1:
                    style = cell.find('.//' + qn('w:pStyle')); assert style.get(qn('w:val')) == 'PilotTableLead'
                    style.set(qn('w:val'), 'Compact')
        assert etree.tostring(old) == etree.tostring(new), 'Other table XML changed'
        changed += 1
    assert changed == expected, (changed, expected)
    assert etree.tostring(a) == etree.tostring(b), 'Word content outside tables changed'
    return changed


def inspect(folder):
    compare_docx(folder / 'before.docx', folder / 'noop.docx')
    # A real no-op rewrite preserves even the core timestamps, not just content.
    with zipfile.ZipFile(folder / 'before.docx') as a, zipfile.ZipFile(folder / 'noop.docx') as b:
        assert {n: a.read(n) for n in a.namelist()} == {n: b.read(n) for n in b.namelist()}
    with zipfile.ZipFile(folder / 'before.docx') as a, zipfile.ZipFile(folder / 'after.docx') as b:
        assert set(a.namelist()) == set(b.namelist())
        for name in a.namelist():
            if name not in ['word/document.xml', 'docProps/core.xml']: assert a.read(name) == b.read(name), name
        trees = [etree.fromstring(z.read('word/document.xml')) for z in [a, b]]
    def sections(tree):
        result = {}; name = None
        for node in tree.find(qn('w:body')):
            text = ''.join(node.itertext())
            if text.startswith('CASE: '): name = text[6:]; result[name] = etree.Element('case')
            if name is not None: result[name].append(copy.deepcopy(node))
        return result
    left, right = [sections(tree) for tree in trees]; rows = []
    for name, _, count in cases():
        try: changed = xml_delta(left[name], right[name], count)
        except AssertionError as error: raise AssertionError((name, str(error))) from error
        rows.append(dict(case=name, changed_tables=changed, passed=True))
    return rows


def run(package, output):
    assert not output.exists(); output.mkdir(parents=True); output.chmod(0o777)
    html = ''.join('<h2>CASE: ' + name + '</h2>' + source for name, source, _ in cases())
    assets = {}
    with zipfile.ZipFile(package) as z:
        for name in ['pilot.lua', 'preservation-reading.lua', 'reference.docx']:
            assets[name] = base64.b64encode(z.read('template/assets/src/word/' + name)).decode()
    assets['short-tables.lua'] = base64.b64encode((HERE / 'short-tables.lua').read_bytes()).decode()
    payload = dict(html=html, assets=assets, xml=(HERE / 'short-tables.xml.j2').read_text())
    (output / 'input.html').write_text(html)
    subprocess.run(['docker', 'run', '--rm', '--network', 'none', '--read-only', '--tmpfs', '/tmp:rw,size=512m',
        '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '-i', '-v', str(HERE.resolve()) + ':/probe:ro',
        '-v', str(output.resolve()) + ':/out', '--entrypoint', 'python', IMAGE, '/probe/engine_runner.py'],
        input=json.dumps(payload).encode(), check=True, timeout=180)
    rows = inspect(output)
    report = dict(passed=True, native_checked=False, release_acceptance=False, image=IMAGE, rows=rows,
                  no_op_all_components_identical=True, package_sha256=sha(package.read_bytes()),
                  source_sha256={n: sha((HERE / n).read_bytes()) for n in ['short-tables.lua', 'short-tables.xml.j2', 'engine_runner.py', 'table_probe.py']},
                  artifacts={p.name: sha(p.read_bytes()) for p in output.iterdir() if p.is_file()})
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(passed=True, cases=len(rows), changed_tables=sum(r['changed_tables'] for r in rows))))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--package', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True); a = p.parse_args(); run(a.package, a.output)
