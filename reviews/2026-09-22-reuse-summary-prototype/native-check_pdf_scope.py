"""Supplement: facts and authored blocks must occur in Q1, not just elsewhere."""
from collections import Counter
import itertools
import json
from pathlib import Path
from bs4 import BeautifulSoup
import check

ROOT = Path(__file__).resolve().parent
manifest = json.loads((ROOT / 'manifest.json').read_text())
oracle = json.loads((ROOT / 'authored-oracle.json').read_text())
rows = []
for case, locale, profile in itertools.product(manifest['cases'], ['en', 'zh-Hant'], ['review', 'submission']):
    context = json.loads((ROOT / 'candidate/contexts' / (case + '.json')).read_text())
    expected = check.expected(context, locale)
    folder = ROOT / 'candidate/renders' / f'{case}-{locale}-{profile}'
    html = BeautifulSoup((folder / 'document.html').read_text(), 'html.parser')
    start, end = [check.compact(html.select_one('#' + q + ' > h3').get_text()) for q in ['q-how-data', 'q-what-data']]
    fragments = Counter()
    for state in expected.values():
        fragments.update(check.compact(text) for _, text in state['facts'])
        if state['detail'] and state['filled']:
            authored = BeautifulSoup(oracle[case][state['detail']], 'html.parser')
            fragments.update(check.compact(n.get_text()) for n in authored.select('p, li, tr') if n.get_text().strip())
    for kind, filename in [('pdf', 'document.pdf'), ('word_preview', 'word-preview/document.pdf')]:
        _, _, text = check.layout(folder / filename)
        assert text.count(start) == text.count(end) == 1, 'Ambiguous PDF question boundary'
        first, last = text.index(start), text.index(end)
        assert first < last
        question = text[first:last]
        for fragment, count in fragments.items():
            assert question.count(fragment) >= count, 'Q1 lost text even if another question retains it'
        rows.append(dict(case=case, locale=locale, profile=profile, kind=kind, passed=True, fragment_occurrences=sum(fragments.values())))
assert len(rows) == 56
with (ROOT / 'pdf-scope-checks.json').open('x') as stream:
    stream.write(json.dumps(dict(passed=True, rows=rows), indent=2) + '\n')
print(json.dumps(dict(passed=True, scoped_documents=len(rows))))
