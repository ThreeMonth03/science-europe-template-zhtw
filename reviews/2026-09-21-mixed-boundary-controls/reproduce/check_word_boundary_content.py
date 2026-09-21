"""Preserve incomplete Word paragraph evidence without calling it lost text.

For the 32/33-resource stress cases, raw PDF painting order and repeated table
headers can interrupt a paragraph. An unchanged DOCX and pixel-identical LO
preview prove no regression, NOT complete content/layout acceptance. Keep the
unverified paragraphs visible until a separate column-aware proof is available.
"""
from collections import Counter
import subprocess
from check_word_short_budget_outputs import paragraph_texts, word_pages
from mixed_row_content import compact


def assess(counts, text):
    unresolved = [dict(text=p, expected=n, contiguous_matches=text.count(p))
                  for p, n in counts.items() if text.count(p) < n]
    return dict(expected_paragraphs=sum(counts.values()),
        contiguous_paragraph_occurrences=sum(min(n, text.count(p)) for p, n in counts.items()),
        unresolved_paragraphs=unresolved, all_paragraphs_verified=not unresolved,
        complete_content_acceptance=False, layout_acceptance=False,
        method='raw-text-paragraph-counts-no-column-reordering')


def inspect(document, preview, soup):
    count = len(soup.select('#q-required-resources .resource-table tbody > tr'))
    assert count in [32, 33]
    raw = subprocess.check_output(['pdftotext', '-raw', str(preview), '-'], text=True)
    bbox = subprocess.check_output(['pdftotext', '-bbox-layout', str(preview), '-'])
    text = ''.join(word_pages(raw, bbox))
    counts = Counter(compact(p) for p in paragraph_texts(document, soup) if compact(p))
    result = assess(counts, text)
    result['resource_count'] = count
    result['long_tables'] = [dict(rows=len(t.rows), style=t.style.name) for t in document.tables
                             if 'MIX-LONG-09-PARA-' in t._tbl.xml]
    assert len(result['long_tables']) == 1
    return result
