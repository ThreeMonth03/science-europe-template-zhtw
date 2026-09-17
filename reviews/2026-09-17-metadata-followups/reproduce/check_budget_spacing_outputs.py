"""Native 0.3.17 -> 0.3.18: style-only budget spacing, same synthetic answers."""
import argparse
import json
from pathlib import Path
import subprocess
import zipfile
from bs4 import BeautifulSoup
from docx import Document
from docx.oxml.ns import qn
from lxml import etree
from artifact_utils import sha
from check_budget_outputs import xml, compare_word, question_body
from check_long_budget_outputs import page_texts
from check_word_rhythm_outputs import assert_styles, compare_questions, inspect_preview
from check_narrative_outputs import compact, page_bounds


def compare_style_roots(before, after):
    """Remove only the exact new long-table margin override, then compare all styles."""
    matches = [s for s in after if s.get(qn('w:styleId')) == 'PilotLongBudget']
    assert len(matches) == 1
    style = matches[0]; props = style.findall(qn('w:tcPr'))
    assert len(props) == 1
    expected = etree.Element(qn('w:tcPr'), nsmap=props[0].nsmap)
    margins = etree.SubElement(expected, qn('w:tcMar'))
    for edge in ['top', 'bottom']:
        etree.SubElement(margins, qn('w:' + edge), attrib={qn('w:w'): '28', qn('w:type'): 'dxa'})
    assert xml(props[0]) == xml(expected), 'Only 28-twip top/bottom margins are allowed'
    style.remove(props[0])
    assert xml(before) == xml(after), 'Another reference style changed'


def compare_styles(old, new):
    with zipfile.ZipFile(old) as a, zipfile.ZipFile(new) as b:
        compare_style_roots(etree.fromstring(a.read('word/styles.xml')), etree.fromstring(b.read('word/styles.xml')))


def line_box_overlaps(data):
    """PDF font-metric boxes are not ink bounds; record, don't declare collisions."""
    found = []
    for block in etree.fromstring(data).findall('.//{*}block'):
        lines = block.findall('{*}line')
        for index, left in enumerate(lines):
            for right in lines[index+1:]:
                width = min(float(left.get('xMax')), float(right.get('xMax'))) - max(float(left.get('xMin')), float(right.get('xMin')))
                height = min(float(left.get('yMax')), float(right.get('yMax'))) - max(float(left.get('yMin')), float(right.get('yMin')))
                if width > .5 and height > .5:
                    found.append((compact(''.join(left.itertext())), compact(''.join(right.itertext())), round(width, 3), round(height, 3)))
    return sorted(found)


def pdf_body_without_table_headers(path, soup):
    """Strip only exact header lines and verified numeric page footers, not answers."""
    header = compact(soup.select_one('.resource-table thead').get_text())
    raw = subprocess.check_output(['pdftotext', '-layout', str(path), '-'], text=True).split('\f')
    if not raw[-1].strip(): raw.pop()
    content = []
    for number, page in enumerate(raw, 1):
        lines = [line for line in page.splitlines() if line.strip()]
        assert lines and compact(lines[-1]) == f'{number}/{len(raw)}', 'Unverified PDF footer'
        content.extend(line for line in lines[:-1] if compact(line) != header)
    first = compact(soup.select_one('.question h3').get_text())
    whole = compact('\n'.join(content)); assert whole.count(first) == 1
    return whole.split(first, 1)[1]


def pdf_raw_page_texts(path):
    # Native PDF emits each cell's content contiguously in raw order; layout
    # extraction interleaves a two-line funding name with the purpose column.
    pages = subprocess.check_output(['pdftotext', '-raw', str(path), '-'], text=True).split('\f')
    if not pages[-1].strip(): pages.pop()
    result = []
    for number, page in enumerate(pages, 1):
        lines = [line for line in page.splitlines() if line.strip()]
        assert lines and compact(lines[-1]) == f'{number}/{len(pages)}'
        result.append(compact('\n'.join(lines[:-1])))
    return result


def long_page_checks(pages, soup, repeating_identity):
    resource = soup.select_one('.resource-table tbody tr')
    cells = resource.find_all('td', recursive=False)
    title = compact(cells[0].select_one('p strong').get_text())
    identity = [title] + [compact(c.get_text()) for c in cells[1:]]
    headers = [compact(c.get_text()) for c in soup.select('.resource-table thead th')]
    purposes = [compact(p.get_text()) for p in resource.select('.answer-detail p') if 'BUDGET-PARA-' in p.get_text()]
    assert len(purposes) == 60
    locations = []
    for purpose in purposes:
        hits = [i for i, page in enumerate(pages, 1) if purpose in page]
        assert len(hits) == 1, ('Missing, duplicated or split purpose paragraph', purpose)
        assert all(h in pages[hits[0]-1] for h in headers), 'Missing column headers'
        if repeating_identity:
            assert all(value in pages[hits[0]-1] for value in identity), 'Missing repeating resource identity'
        locations.extend(hits)
    heading = compact(soup.select_one('#q-required-resources h4').get_text())
    first = compact(resource.select_one('.answer-detail p').get_text())
    starts = [i for i, page in enumerate(pages, 1) if all(value in page for value in [heading, first, purposes[0]] + identity)]
    assert len(starts) == 1, 'Budget heading must start with resource identity and purpose'
    tail = soup.select('.resource-table tbody tr')[-1]
    tail_title = compact(tail.select_one('p strong').get_text())
    tail_pages = [i for i, page in enumerate(pages, 1) if tail_title in page]
    assert len(tail_pages) == 1
    assert '0TWD' in pages[tail_pages[0]-1], 'Zero budget must survive'
    return {'purpose_pages': sorted(set(locations)), 'complete_purpose_paragraphs': len(purposes),
            'budget_start_page': starts[0], 'tail_resource_page': tail_pages[0],
            'tail_shares_last_purpose_page': tail_pages[0] == max(locations)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['build', 'prior']: p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--cases', nargs='+', required=True); a = p.parse_args()
    helpers = ['artifact_utils.py', 'check_budget_outputs.py', 'check_long_budget_outputs.py',
               'check_word_rhythm_outputs.py', 'check_narrative_outputs.py', 'check_identifier_outputs.py',
               'check_identifier_followup_outputs.py', 'compare_runtime_outputs.py']
    report = {'selected_checks_passed': False, 'release_acceptance': False, 'rows': [],
              'checker_sha256': sha(Path(__file__)),
              'helper_sha256': {n: sha(Path(__file__).with_name(n)) for n in helpers},
              'package_sha256': {n: sha(a.build/n) for n in ['english.zip', 'chinese.zip']},
              'prior_package_sha256': {n: sha(a.prior/n) for n in ['english.zip', 'chinese.zip']},
              'artifact_sha256': {str(f.relative_to(a.build)): sha(f) for folder in ['renders', 'word-preview'] for f in sorted((a.build/folder).glob('*')) if f.is_file()},
              'prior_artifact_sha256': {str(f.relative_to(a.prior)): sha(f) for folder in ['renders', 'word-preview'] for f in sorted((a.prior/folder).glob('*')) if f.is_file()},
              'limits': ['Selected synthetic fixtures only; not full DMP acceptance',
                         'Word previews use LibreOffice, not Microsoft Word',
                         'Native PDF still has narrow purpose columns and no repeating resource identity',
                         'PDF line-box checks require no new metric-box overlaps; existing boxes are not ink-collision evidence',
                         'PDF >=12 direct purpose blocks hint does not cover every long answer',
                         'Stock Markdown-table failures remain blocked']}
    target = a.build / 'budget-spacing-report.json'
    assert not target.exists(), 'Never overwrite evidence'
    try:
        for case in a.cases:
            for language in ['english', 'chinese']:
                name = case + '-' + language
                old, new = [root / 'renders' / name for root in [a.prior, a.build]]
                for fmt in ['html', 'pdf', 'docx']:
                    fixtures = [json.loads(path.with_suffix('.' + fmt + '.fixture.json').read_text()) for path in [old, new]]
                    for key in ['recipe_sha256', 'events_sha256', 'km_sha256']: assert fixtures[0][key] == fixtures[1][key]
                    assert fixtures[0]['package_sha256'] == report['prior_package_sha256'][language + '.zip']
                    assert fixtures[1]['package_sha256'] == report['package_sha256'][language + '.zip']
                soups = [BeautifulSoup(path.with_suffix('.html').read_text(), 'html.parser') for path in [old, new]]
                count = compare_questions(*soups)
                documents = [Document(path.with_suffix('.docx')) for path in [old, new]]
                assert_styles(documents[1]); compare_styles(old.with_suffix('.docx'), new.with_suffix('.docx'))
                compare_word(*documents, False)  # Exact Q1-Q15 XML, styles, relationships and paragraph boundaries.
                old_pdf, new_pdf = [path.with_suffix('.pdf') for path in [old, new]]
                previews = [root / 'word-preview' / (name + '.pdf') for root in [a.prior, a.build]]
                before_pages, after_pages = [page_texts(path) for path in previews]
                row = {'case': case, 'language': language, 'question_comparisons': count,
                       'question_word_xml_unchanged': True,
                       'prior_pdf_pages': page_bounds(old_pdf), 'pdf_pages': page_bounds(new_pdf),
                       'prior_word_pages': len(before_pages), 'word_pages': inspect_preview(previews[1])}
                boxes = [line_box_overlaps(subprocess.check_output(['pdftotext', '-bbox-layout', str(path), '-'])) for path in [old_pdf, new_pdf]]
                assert boxes[0] == boxes[1], 'New or changed PDF line metric-box overlap requires review'
                row['unchanged_pdf_metric_box_overlaps'] = boxes[1]
                if case == 'budget-long':
                    assert pdf_body_without_table_headers(old_pdf, soups[0]) == pdf_body_without_table_headers(new_pdf, soups[1]), 'PDF answer text/order changed'
                    q1 = compact(soups[0].select_one('.question h3').get_text())
                    q15 = compact(soups[0].select_one('#q-required-resources h3').get_text())
                    assert ''.join(before_pages).split(q1, 1)[1].split(q15, 1)[0] == ''.join(after_pages).split(q1, 1)[1].split(q15, 1)[0]
                    row['pdf'] = long_page_checks(pdf_raw_page_texts(new_pdf), soups[1], False)
                    row['pdf']['paragraph_location_extraction'] = 'pdftotext -raw; exact content within one page'
                    row['word'] = long_page_checks(after_pages, soups[1], True)
                    assert row['word']['tail_shares_last_purpose_page'], 'Short tail resource stranded on its own page'
                    assert row['pdf_pages'] < row['prior_pdf_pages'] and row['word_pages'] <= row['prior_word_pages']
                else:
                    assert question_body(old_pdf, soups[0]) == question_body(new_pdf, soups[1]), 'Control PDF text changed'
                    assert row['pdf_pages'] == row['prior_pdf_pages'], 'Control PDF pagination changed'
                    assert before_pages == after_pages, 'Control Word pagination/text changed'
                row['passed'] = True; report['rows'].append(row)
    except Exception as e:
        report['failure'] = str(e); target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n'); raise
    report['selected_checks_passed'] = True
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'passed': True, 'pairs': len(report['rows']), 'question_comparisons': sum(r['question_comparisons'] for r in report['rows'])}))


if __name__ == '__main__':
    main()
