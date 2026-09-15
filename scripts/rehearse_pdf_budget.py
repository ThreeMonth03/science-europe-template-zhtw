"""Disposable full-width PDF budget layout, not native DSW evidence."""
import argparse
import copy
import json
from pathlib import Path
from bs4 import BeautifulSoup
from artifact_utils import sha

CSS = '''
html body #q-required-resources .pdf-resource-reading { break-inside: auto; }
html body .pdf-resource-reading thead td { background: #eef2f4; }
html body .pdf-resource-reading tbody td { border-top: none; }
'''


def transform(soup):
    table = soup.select_one('#q-required-resources .resource-table')
    original = copy.deepcopy(table)
    rows = table.select('tbody > tr'); assert len(rows) == 2
    cells = rows[0].find_all('td', recursive=False); assert len(cells) == 3
    assert len(cells[0].select('.answer-detail > p')) > 60
    reading = copy.deepcopy(table); reading['class'].append('pdf-resource-reading')
    reading['data-item-id'] = rows[0]['data-item-id']
    identity = copy.deepcopy(rows[0]); del identity['data-item-id']
    first = identity.find('td'); title = copy.deepcopy(first.find('p', recursive=False)); first.clear(); first.append(title)
    reading.thead.append(identity)
    reading.tbody.clear(); row = soup.new_tag('tr'); cell = soup.new_tag('td', colspan='3')
    purpose = copy.deepcopy(cells[0]); purpose.find('p', recursive=False).extract()
    for node in list(purpose.contents): cell.append(node.extract())
    row.append(cell); reading.tbody.append(row)
    tail = copy.deepcopy(table); tail.tbody.clear(); tail.tbody.append(copy.deepcopy(rows[1]))
    table.replace_with(reading); reading.insert_after(tail)
    return original


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True); p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(); a.out.mkdir(parents=True, exist_ok=False)
    report = {'release_acceptance': False, 'checker_sha256': sha(Path(__file__)), 'rows': []}
    for language in ['english', 'chinese']:
        path = a.source / f'budget-long-{language}.html'
        soup = BeautifulSoup(path.read_text(), 'html.parser'); old_questions = [str(q) for q in soup.select('.question')]
        transform(soup); soup.style.append(CSS)
        assert old_questions[:14] == [str(q) for q in soup.select('.question')][:14]
        out = a.out / f'budget-long-{language}.html'; out.write_text(str(soup))
        report['rows'].append({'language': language, 'source_sha256': sha(path), 'html_sha256': sha(out)})
    (a.out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(a.out)


if __name__ == '__main__': main()
