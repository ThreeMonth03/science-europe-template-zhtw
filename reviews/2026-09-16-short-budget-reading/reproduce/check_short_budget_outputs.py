"""Native bilingual 0.3.24 -> 0.3.25 checks, including unchanged Word bodies."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import zipfile
from bs4 import BeautifulSoup
from docx import Document
from lxml import etree
from artifact_utils import sha
from check_budget_outputs import body, xml
from check_budget_spacing_outputs import pdf_raw_page_texts
from check_word_rhythm_outputs import inspect_preview
from compare_runtime_outputs import markers

CASES = ['empty', 'negative', 'personal-transfer-complete', 'partial', 'budget-long-no-currency', 'budget-mixed-gaps', 'budget-many']
NEW_BASELINES = {'budget-mixed-gaps', 'budget-many'}
AFFECTED = {'partial', 'budget-mixed-gaps'}


def question_pages(pages, soup):
    heading = ''.join(soup.select_one('.question h3').get_text().split())
    index = next(i for i, text in enumerate(pages) if heading in text)
    return [pages[index].split(heading, 1)[1]]+pages[index+1:]


def prompt_lines(pdf, text):
    compact = lambda s: ''.join(s.split())
    target = compact(text); found = []
    data = etree.fromstring(subprocess.check_output(['pdftotext', '-bbox-layout', str(pdf), '-']))
    for number, page in enumerate(data.findall('.//{*}page'), 1):
        # Poppler may split each table line into its own block. Follow the same
        # left edge geometrically, not XML block order or interleaved columns.
        lines = sorted([(float(n.get('yMin')), float(n.get('xMin')), compact(''.join(n.itertext()))) for n in page.findall('.//{*}line')])
        for y, x, text in lines:
            if not text or not target.startswith(text): continue
            column = [(yy, value) for yy, xx, value in lines if yy >= y and abs(xx-x) < .75]
            joined = ''; previous = y
            for index, (yy, value) in enumerate(column[:6], 1):
                if yy-previous > 22.5: break
                joined += value; previous = yy
                if joined == target: found.append({'page': number, 'line_count': index}); break
                if not target.startswith(joined): break
    assert len(found) == 1, (text, found)
    return found[0]


def positioned_partial_lists(pages, bbox, soup):
    """Restore two verified generated bullets to their visual list-item order.

    WeasyPrint paints outside markers last on a page. Moving the budget onto
    that page changes raw extraction order, not the rendered list or its text.
    This oracle is intentionally limited to the known synthetic partial fixture.
    """
    compact = lambda s: ''.join(s.split())
    assert '•' not in soup.get_text(), 'Authored bullets require a different oracle'
    items = [compact(n.get_text()) for n in soup.select('#q-required-resources [data-fact-id="specialist-expertise-detail"] li')]
    assert len(items) == len(set(items)) == 2
    nodes = etree.fromstring(bbox).findall('.//{*}page'); assert len(nodes) == len(pages)
    result = list(pages); found = []
    for index, node in enumerate(nodes):
        lines = [compact(''.join(n.itertext())) for n in node.findall('.//{*}line')]
        present = [item for item in items if '•'+item in lines]
        if not present: continue
        assert all(lines.count('•'+item) == 1 for item in present)
        count = len(present)
        assert sum(n.text == '•' for n in node.findall('.//{*}word')) == count
        assert result[index].endswith('•'*count)
        source = result[index][:-count]; assert '•' not in source
        for item in present:
            assert source.count(item) == 1
            source = source.replace(item, '•'+item, 1)
        result[index] = source; found.extend(present)
    assert sorted(found) == sorted(items)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ['build', 'prior', 'extra-prior', 'english']: p.add_argument('--'+key, type=Path, required=True)
    p.add_argument('--output', type=Path); a = p.parse_args()
    sys.path.insert(0, str(a.english.resolve()/'scripts'))
    import check_missing_info_outputs as missing
    missing.HERE = a.english.resolve()
    target = a.output or a.build/'short-budget-report.json'; assert not target.exists()
    report = {'selected_checks_passed': False, 'release_acceptance': False, 'version': '0.3.25', 'rows': [],
        'checker_sha256': sha(Path(__file__)), 'package_sha256': {n: sha(a.build/n) for n in ['english.zip', 'chinese.zip']},
        'helper_sha256': {n: sha(Path(__file__).with_name(n)) for n in ['artifact_utils.py', 'check_missing_info_outputs.py', 'check_budget_outputs.py', 'check_budget_spacing_outputs.py', 'check_word_rhythm_outputs.py', 'compare_runtime_outputs.py']},
        'limits': ['Seven synthetic cases per language, not all possible questionnaires',
            'LibreOffice preview, not Microsoft Word acceptance', 'Reviewed local Markdown-tables worker; stock worker remains a release gate']}
    try:
        for case in CASES:
            soups = []
            for language in ['english', 'chinese']:
                prior = a.extra_prior if case in NEW_BASELINES else a.prior
                stem = case+'-'+language; old = prior/'renders'/stem; new = a.build/'renders'/stem
                row, soup = missing.inspect(a.build, case, language); soups.append(soup)
                left = BeautifulSoup(old.with_suffix('.html').read_text(), 'html.parser')
                assert len(left.select('.question')) == 15
                assert [str(q) for q in left.select('.question')] == [str(q) for q in soup.select('.question')]
                assert not soup.select('.pdf-short-budget'), 'Non-PDF must not have the PDF-only hint'
                for fmt in ['html', 'pdf', 'docx']:
                    before = json.loads(old.with_suffix('.'+fmt+'.fixture.json').read_text()); after = json.loads(new.with_suffix('.'+fmt+'.fixture.json').read_text())
                    for key in ['recipe_sha256', 'events_sha256', 'km_sha256']: assert before[key] == after[key]
                    assert before['package_sha256'] == sha(prior/(language+'.zip'))
                    assert after['package_sha256'] == report['package_sha256'][language+'.zip']
                before_pages = pdf_raw_page_texts(old.with_suffix('.pdf')); after_pages = pdf_raw_page_texts(new.with_suffix('.pdf'))
                row['prior_pages'] = len(before_pages)
                assert row['pages'] <= row['prior_pages'], (case, language, 'Page growth')
                comparison_pages = [before_pages, after_pages]
                if case == 'partial':
                    comparison_pages = [positioned_partial_lists(pages, subprocess.check_output(['pdftotext', '-bbox-layout', str(path.with_suffix('.pdf')), '-']), html)
                        for pages, path, html in [(before_pages, old, left), (after_pages, new, soup)]]
                    row['geometrically_verified_training_list_markers'] = 2
                old_body = question_pages(comparison_pages[0], left); new_body = question_pages(comparison_pages[1], soup)
                assert ''.join(old_body) == ''.join(new_body), 'PDF question text changed'
                if case not in AFFECTED:
                    assert old_body == new_body and row['pages'] == row['prior_pages'], 'Control pagination changed'
                if case == 'partial':
                    prompt = soup.select_one('[data-fact-id="resource-amount"]').get_text()
                    row['prompt_before'] = prompt_lines(old.with_suffix('.pdf'), prompt)
                    row['prompt_after'] = prompt_lines(new.with_suffix('.pdf'), prompt)
                    assert (row['prompt_before']['line_count'], row['prompt_after']['line_count']) == ((4, 2) if language == 'english' else (2, 1))
                    assert (row['prior_pages'], row['pages']) == ((5, 5) if language == 'english' else (5, 4))
                documents = [Document(f.with_suffix('.docx')) for f in [old, new]]
                assert [xml(n) for n in body(documents[0])] == [xml(n) for n in body(documents[1])], 'Word body changed'
                links = lambda d: sorted(r.target_ref for r in d.part.rels.values() if r.is_external)
                assert links(documents[0]) == links(documents[1])
                with zipfile.ZipFile(old.with_suffix('.docx')) as x, zipfile.ZipFile(new.with_suffix('.docx')) as y:
                    assert x.read('word/styles.xml') == y.read('word/styles.xml')
                preview = a.build/'word-preview'/(stem+'.pdf'); old_preview = prior/'word-preview'/(stem+'.pdf')
                row['word_pages'] = inspect_preview(preview); row['prior_word_pages'] = inspect_preview(old_preview)
                assert row['word_pages'] == row['prior_word_pages']
                row['exact_question_html_pdf_text_and_word_body'] = True
                row['prior_artifact_sha256'] = {str(f): sha(f) for f in [old.with_suffix('.'+fmt+extra) for fmt in ['html', 'pdf', 'docx'] for extra in ['', '.fixture.json']]+[old_preview]}
                for f in [new.with_suffix('.docx'), new.with_suffix('.docx.fixture.json'), preview]: row['artifact_sha256'][str(f.relative_to(a.build))] = sha(f)
                report['rows'].append(row)
                print(json.dumps({k: row[k] for k in ['case', 'language', 'prior_pages', 'pages', 'word_pages', 'errors', 'reading_issues']}), flush=True)
            assert markers(soups[0]) == markers(soups[1])
        report['selected_checks_passed'] = len(report['rows']) == len(CASES)*2 and all(not r['errors'] and not r['reading_issues'] for r in report['rows'])
    except Exception as e:
        report['failure'] = str(e); raise
    finally: target.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    assert report['selected_checks_passed'], 'See preserved diagnostics'


if __name__ == '__main__': main()
