"""Bind stock/patched-worker comparisons to identical packages and fixtures."""
import argparse
import hashlib
import json
import re
from pathlib import Path

from bs4 import BeautifulSoup


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized(value):
    return re.sub(r'\s+', '', value)


def markers(soup):
    return [(q['id'], [(n.get('data-item-id'), n.get('data-fact-id'), n.get('data-status'))
                      for n in q.select('[data-item-id], [data-fact-id], [data-status]')])
            for q in soup.select('.question')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--variant', type=Path, required=True)
    parser.add_argument('--cases', nargs='+', default=['populated', 'stress', 'structured', 'structured-partial'])
    args = parser.parse_args()
    hashes = {}
    for name in ('english.zip', 'chinese.zip'):
        hashes[name] = sha(args.baseline / name)
        assert hashes[name] == sha(args.variant / name), 'Package bytes differ'
    assert json.loads((args.variant / 'manifest.json').read_text())['status'] == 'runtime-experiment'
    rows = []
    for case in args.cases:
        for language in ('english', 'chinese'):
            for fmt in ('html', 'pdf', 'docx'):
                name = f'{case}-{language}.{fmt}.fixture.json'
                a, b = [json.loads((root / 'renders' / name).read_text()) for root in (args.baseline, args.variant)]
                for key in ('recipe_sha256', 'events_sha256', 'km_sha256', 'package_sha256'):
                    assert a[key] == b[key], (name, key)
            name = f'{case}-{language}.html'
            a, b = [BeautifulSoup((root / 'renders' / name).read_text(), 'html.parser') for root in (args.baseline, args.variant)]
            assert markers(a) == markers(b), (name, 'fact markers differ')
            # Table syntax is intentionally different. Compare every other question
            # verbatim except whitespace; Q1 is checked for markers and native table.
            for qa in a.select('.question'):
                if qa['id'] != 'q-how-data':
                    assert normalized(qa.get_text()) == normalized(b.find(id=qa['id']).get_text()), (name, qa['id'])
            assert not a.select_one('#q-how-data .answer-detail table')
            table = b.select_one('#q-how-data .answer-detail table')
            assert table is not None
            # Every rendered table-cell value was present in the stock Q1 text.
            for cell in table.select('th, td'):
                assert normalized(cell.get_text()) in normalized(a.find(id='q-how-data').get_text())
            rows.append({'case': case, 'language': language, 'identical_inputs': True,
                         'fact_markers_unchanged': True, 'q2_to_q15_text_unchanged': True,
                         'provenance_table_cells_retained': True})
    report = {'checks': rows, 'package_sha256': hashes, 'selected_comparison_passed': True,
              'release_acceptance': False, 'checker_sha256': sha(Path(__file__)),
              'limits': ['Q1 full prose equivalence is not asserted', 'Visual review and complete Science Europe coverage are separate'],
              'artifact_sha256': {side: {str(p.relative_to(root)): sha(p) for p in sorted((root / 'renders').iterdir()) if p.is_file()}
                                  for side, root in [('stock', args.baseline), ('tables', args.variant)]}}
    (args.variant / 'runtime-comparison.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'compared_case_language_pairs': len(rows), 'selected_comparison_passed': True}))


if __name__ == '__main__':
    main()
