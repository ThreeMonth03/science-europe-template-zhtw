"""Native 0.3.19 PDF-only reading; compare matching 0.3.18 synthetic exports."""
import argparse
import json
from pathlib import Path
import subprocess
import zipfile
from bs4 import BeautifulSoup, Tag, Comment
from docx import Document
from lxml import etree
from artifact_utils import sha
from check_budget_outputs import compare_word, question_body
from check_budget_spacing_outputs import pdf_raw_page_texts, long_page_checks, line_box_overlaps
from check_long_budget_outputs import page_texts
from check_word_rhythm_outputs import assert_styles, compare_questions, inspect_preview
from check_narrative_outputs import compact, page_bounds


def normalize_owned_indent(soup):
    for p in soup.select('.resource-table > tbody > tr > td:first-child > p'):
        if not p.attrs and not p.find(True) and p.get_text().strip().startswith('支援項目：'):
            p.string = p.get_text().strip()
    return soup


def visible(node):
    """Fixture HTML reading order, including native PDF list bullets."""
    if isinstance(node, Comment): return ''
    if not isinstance(node, Tag): return str(node)
    return ('•' if node.name == 'li' else '') + ''.join(visible(child) for child in node.children)


def question_pages(pages, soup):
    first = compact(soup.select_one('.question h3').get_text())
    assert sum(page.count(first) for page in pages) == 1
    index = next(i for i, page in enumerate(pages) if first in page)
    return [''] * index + [pages[index].split(first, 1)[1]] + pages[index+1:]


def exact_long_sequence(pages, soup):
    """Only verified page-prefix repeated headers may be removed from the PDF."""
    table = soup.select_one('.resource-table'); rows = table.select('tbody > tr')
    assert len(rows) == 2, 'Oracle is deliberately limited to the two-resource fixture'
    cells = rows[0].find_all('td', recursive=False)
    title = cells[0].find('p', recursive=False)
    header = compact(visible(table.thead))
    identity = compact(visible(title) + ''.join(visible(c) for c in cells[1:]))
    purpose = compact(''.join(visible(c) for c in cells[0].children if c is not title))
    tail = compact(visible(rows[1]))
    heading = compact(soup.select_one('#q-required-resources h4').get_text())
    assert sum(page.count(heading) for page in pages) == 1
    start = next(i for i, page in enumerate(pages) if heading in page)
    first = pages[start].split(heading, 1)[1]
    assert first.startswith(header + identity), 'Budget must begin with original labels and resource identity'
    result = first[len(header):]; repeated = 0
    for page in pages[start+1:]:
        if 'BUDGET-PARA-' in page:
            assert page.startswith(header + identity), 'Continuation must begin with full original identity'
            result += page[len(header + identity):]; repeated += 1
        else:
            result += page
    assert repeated > 0, 'Fixture must exercise continuation headers'
    assert result == identity + purpose + header + tail, 'PDF purpose/list/allocation/tail sequence changed'
    return repeated


def complete_marker_lines(data, soup):
    lines = [compact(''.join(n.itertext())) for n in etree.fromstring(data).findall('.//{*}line')]
    purposes = [compact(p.get_text()) for p in soup.select('.resource-table .answer-detail p') if 'BUDGET-PARA-' in p.get_text()]
    assert len(purposes) == 60
    assert all(lines.count(p) == 1 for p in purposes), 'Expected full-width fixture paragraphs on single lines'
    return len(purposes)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['build', 'prior']: p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--cases', nargs='+', required=True); a = p.parse_args()
    helpers = ['artifact_utils.py', 'check_budget_outputs.py', 'check_budget_spacing_outputs.py',
               'check_long_budget_outputs.py', 'check_word_rhythm_outputs.py', 'check_narrative_outputs.py',
               'check_identifier_outputs.py', 'check_identifier_followup_outputs.py', 'compare_runtime_outputs.py']
    report = {'selected_checks_passed': False, 'release_acceptance': False, 'rows': [],
              'checker_sha256': sha(Path(__file__)),
              'helper_sha256': {n: sha(Path(__file__).with_name(n)) for n in helpers},
              'package_sha256': {n: sha(a.build/n) for n in ['english.zip', 'chinese.zip']},
              'prior_package_sha256': {n: sha(a.prior/n) for n in ['english.zip', 'chinese.zip']},
              'artifact_sha256': {str(f.relative_to(a.build)): sha(f) for folder in ['renders', 'word-preview'] for f in sorted((a.build/folder).glob('*')) if f.is_file()},
              'prior_artifact_sha256': {str(f.relative_to(a.prior)): sha(f) for folder in ['renders', 'word-preview'] for f in sorted((a.prior/folder).glob('*')) if f.is_file()},
              'limits': ['Selected synthetic fixtures, not whole-DMP or Microsoft Word acceptance',
                         'Long sequence oracle covers the declared two-resource fixture only',
                         'Complex or missing-header data conservatively retain the legacy layout',
                         'Metric-box overlap comparison is not a complete visual score',
                         'Stock Markdown-table failures remain release blockers']}
    target = a.build / 'pdf-budget-reading-report.json'; assert not target.exists(), 'Never overwrite evidence'
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
                soups = [normalize_owned_indent(BeautifulSoup(path.with_suffix('.html').read_text(), 'html.parser')) for path in [old, new]]
                count = compare_questions(*soups)
                documents = [Document(path.with_suffix('.docx')) for path in [old, new]]
                assert_styles(documents[1]); compare_word(*documents, False)
                with zipfile.ZipFile(old.with_suffix('.docx')) as z1, zipfile.ZipFile(new.with_suffix('.docx')) as z2:
                    assert z1.read('word/styles.xml') == z2.read('word/styles.xml'), 'Word styles changed'
                previews = [root / 'word-preview' / (name + '.pdf') for root in [a.prior, a.build]]
                before_word, after_word = [page_texts(path) for path in previews]
                assert question_pages(before_word, soups[0]) == question_pages(after_word, soups[1]), 'Word content or pagination changed'
                old_pdf, new_pdf = [path.with_suffix('.pdf') for path in [old, new]]
                row = {'case': case, 'language': language, 'question_comparisons': count,
                       'question_word_xml_unchanged': True, 'word_pagination_unchanged': True,
                       'prior_pdf_pages': page_bounds(old_pdf), 'pdf_pages': page_bounds(new_pdf),
                       'prior_word_pages': len(before_word), 'word_pages': inspect_preview(previews[1])}
                boxes = [subprocess.check_output(['pdftotext', '-bbox-layout', str(path), '-']) for path in [old_pdf, new_pdf]]
                assert line_box_overlaps(boxes[0]) == line_box_overlaps(boxes[1]), 'New PDF metric-box overlap'
                row['unchanged_pdf_metric_box_overlaps'] = line_box_overlaps(boxes[1])
                if case == 'budget-long':
                    before, after = [pdf_raw_page_texts(path) for path in [old_pdf, new_pdf]]
                    heading = compact(soups[0].select_one('#q-required-resources h4').get_text())
                    assert ''.join(question_pages(before, soups[0])).split(heading, 1)[0] == ''.join(question_pages(after, soups[1])).split(heading, 1)[0], 'Q1-Q14 or Q15 overview changed'
                    row['pdf'] = long_page_checks(after, soups[1], True)
                    row['pdf']['verified_continuation_headers'] = exact_long_sequence(after, soups[1])
                    row['pdf']['single_line_purpose_paragraphs'] = complete_marker_lines(boxes[1], soups[1])
                    row['word'] = long_page_checks(after_word, soups[1], True)
                    assert row['pdf_pages'] < row['prior_pdf_pages'], 'Expected reduced long-budget pagination'
                else:
                    assert question_body(old_pdf, soups[0]) == question_body(new_pdf, soups[1]), 'Control PDF text changed'
                    assert row['pdf_pages'] == row['prior_pdf_pages'], 'Control PDF pagination changed'
                row['passed'] = True; report['rows'].append(row)
    except Exception as e:
        report['failure'] = str(e); target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n'); raise
    report['selected_checks_passed'] = True
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'passed': True, 'pairs': len(report['rows']), 'question_comparisons': sum(r['question_comparisons'] for r in report['rows'])}))


if __name__ == '__main__': main()
