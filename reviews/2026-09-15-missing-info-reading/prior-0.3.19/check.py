"""Bounded QA report, explicitly distinguishes rendering/content/layout outcomes."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import subprocess
import sys
from bs4 import BeautifulSoup
from lxml import etree
from audit import HERE, ROOT, EN, digest, cases, IDS
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_runtime_outputs import markers
from check_narrative_outputs import compact, page_bounds
from check_budget_spacing_outputs import pdf_raw_page_texts, line_box_overlaps


def inspect(build, case, language):
    name = case + '-' + language; html = build / 'renders' / (name + '.html'); pdf = html.with_suffix('.pdf')
    soup = BeautifulSoup(html.read_text(), 'html.parser'); pages = pdf_raw_page_texts(pdf)
    bbox = subprocess.check_output(['pdftotext', '-bbox-layout', str(pdf), '-'])
    xml = etree.fromstring(bbox); all_text = ''.join(pages)
    row = {'case': case, 'language': language, 'pages': len(pages), 'errors': [], 'reading_issues': [], 'questions': [],
           'gap_nodes': [], 'artifact_sha256': {str(p.relative_to(build)): digest(p) for p in [html, pdf, html.with_suffix('.html.fixture.json'), pdf.with_suffix('.pdf.fixture.json')]}}
    locale = 'en' if language == 'english' else 'zh-Hant'; recipe = HERE / 'fixtures' / locale / (case + '.json')
    events = recipe.with_name(case + '.events.json')
    for fmt in ['html', 'pdf']:
        metadata = json.loads(html.with_suffix('.' + fmt + '.fixture.json').read_text())
        assert metadata['recipe_sha256'] == digest(recipe) and metadata['events_sha256'] == digest(events)
        assert metadata['package_sha256'] == digest(build / (language + '.zip'))
    try: page_bounds(pdf)
    except AssertionError as e: row['errors'].append({'code': 'text-out-of-page', 'detail': str(e)})
    overlaps = line_box_overlaps(bbox); row['metric_box_overlaps'] = overlaps
    row['blank_pages'] = [i for i, text in enumerate(pages, 1) if not text]
    if row['blank_pages']: row['reading_issues'].append({'code': 'empty-page', 'pages': row['blank_pages']})
    if '\ufffd' in all_text: row['errors'].append({'code': 'replacement-character'})
    if soup.select('p p, p div, p ul, p ol, p table'): row['errors'].append({'code': 'invalid-block-in-paragraph'})
    questions = soup.select('.question'); assert len(questions) == 15
    assert len(soup.select('#dmp-content > section')) == 6
    for section in soup.select('#dmp-content > section'):
        text = compact(section.h2.get_text())
        assert all_text.count(text) == 1, ('Missing/duplicated section heading', text)
    for question in questions:
        heading = compact(question.h3.get_text()); answer = question.select_one('.answer')
        locations = [i for i, page in enumerate(pages, 1) if heading in page]
        if len(locations) != 1: row['errors'].append({'code': 'question-heading-missing-or-duplicated', 'question': question['id'], 'pages': locations})
        if not answer or not compact(answer.get_text()): row['errors'].append({'code': 'empty-question-body', 'question': question['id']})
        first = next((node for node in answer.select('p') if compact(node.get_text())), None) if answer else None
        first_text = compact(first.get_text())[:120] if first else ''
        together = bool(locations and first_text and first_text in pages[locations[0]-1])
        record = {'id': question['id'], 'heading_page': locations, 'first_answer_with_heading': together,
                  'gap_count': len(question.select('.data-gap')), 'answer_text': answer.get_text(' ', strip=True) if answer else ''}
        row['questions'].append(record)
        if not together: row['reading_issues'].append({'code': 'heading-first-answer-separation', 'question': question['id'], 'pages': locations})
    gaps = soup.select('#dmp-content .data-gap')
    counts = Counter(compact(g.get_text()) for g in gaps)
    for text, count in counts.items():
        actual = all_text.count(text)
        if actual < count: row['errors'].append({'code': 'missing-gap-text', 'text': text, 'expected': count, 'actual': actual})
    for gap in gaps:
        text = compact(gap.get_text()); locations = [i for i, page in enumerate(pages, 1) if text in page]
        item = gap.find_parent(attrs={'data-item-id': True}); q = gap.find_parent(class_='question')
        row['gap_nodes'].append({'question': q['id'], 'fact': gap.get('data-fact-id'), 'status': gap.get('data-status'),
                                 'item': item.get('data-item-id') if item else None, 'text': gap.get_text(' ', strip=True), 'complete_on_pages': locations})
        if not locations: row['reading_issues'].append({'code': 'gap-split-across-pages', 'question': q['id'], 'text': gap.get_text(' ', strip=True)})
    gap_texts = set(counts)
    for number, page in enumerate(pages, 1):
        if page in gap_texts:
            row['reading_issues'].append({'code': 'isolated-single-gap-page', 'page': number})
    authored = [compact(p.get_text()) for p in soup.select('#dmp-content .answer-detail p') if compact(p.get_text())]
    missing_authored = [text for text, count in Counter(authored).items() if all_text.count(text) < count]
    row['authored_paragraphs_checked'] = len(authored)
    if missing_authored: row['errors'].append({'code': 'authored-paragraph-text-not-retained', 'paragraphs': missing_authored})
    if case == 'empty':
        for q in row['questions']:
            if not q['gap_count']: row['errors'].append({'code': 'empty-answer-without-visible-gap', 'question': q['id']})
        for fact in ['new-data', 'reuse-sources', 'specialist-expertise', 'hardware-software']:
            node = soup.select_one('[data-fact-id="' + fact + '"]'); assert node and node.get('data-status') == 'missing'
        group = [g for g in row['gap_nodes'] if g['question'] == 'q-required-resources']
        group_pages = sorted({p for g in group for p in g['complete_on_pages']})
        if len(group_pages) > 1:
            row['reading_issues'].append({'code': 'short-missing-answer-group-split', 'question': 'q-required-resources', 'pages': group_pages})
    if case == 'negative':
        for fact in ['new-data', 'reuse-sources', 'specialist-expertise', 'hardware-software']:
            node = soup.select_one('[data-fact-id="' + fact + '"]'); assert node and node.get('data-status') == 'explicit-no'
            assert compact(node.get_text()) in all_text
    if case == 'personal-data-partial':
        question = soup.select_one('#q-personal-data')
        row['partial_followup'] = {'question': 'q-personal-data', 'unanswered_reachable_fields': ['cpersGdprSafeguardsQUuid'],
                                 'gap_count': len(question.select('.data-gap')), 'answer': question.select_one('.answer').get_text(' ', strip=True)}
        if not row['partial_followup']['gap_count']:
            row['errors'].append({'code': 'unanswered-followups-have-no-gap-indicator', 'question': 'q-personal-data',
                                   'fields': row['partial_followup']['unanswered_reachable_fields']})
    if case in ['partial', 'budget-mixed-gaps'] or case.startswith('budget-long-no-'):
        budget = soup.select_one('#q-required-resources .resource-table'); assert budget
        table_rows = budget.select('tbody > tr')
        assert '0' in table_rows[-1].find_all('td', recursive=False)[1].get_text()
        assert '0TWD' in all_text
        if case != 'budget-long-no-amount': assert '5000' in all_text
        supplied = [compact(n.get_text()) for n in budget.select('[data-status="complete"]') if n.get('data-fact-id') in ['resource-amount-value', 'resource-currency']]
        assert all(value in all_text for value in supplied)
        row['supplied_partial_amounts_retained'] = supplied
    if case.startswith('budget-long-no-'):
        first = soup.select_one('.resource-table tbody > tr'); cells = first.find_all('td', recursive=False)
        identity = {'resource': compact(cells[0].select_one('p strong').get_text()),
                    'budget': compact(cells[1].get_text()), 'funding': compact(cells[2].get_text())}
        purposes = [compact(p.get_text()) for p in first.select('.answer-detail p') if 'BUDGET-PARA-' in p.get_text()]
        assert len(purposes) == 60; purpose_pages = set()
        for text in purposes:
            locations = [i for i, page in enumerate(pages, 1) if text in page]
            assert len(locations) == 1, ('Missing, split or duplicate original paragraph', text, locations)
            purpose_pages.update(locations)
        deficits = [{'page': i, 'missing': [key for key, value in identity.items() if value not in pages[i-1]]} for i in sorted(purpose_pages)]
        deficits = [d for d in deficits if d['missing']]
        row['long_budget'] = {'purpose_pages': sorted(purpose_pages), 'complete_purpose_paragraphs': 60, 'identity_deficits': deficits}
        if deficits: row['reading_issues'].append({'code': 'missing-resource-context-on-continuations', 'deficits': deficits})
        lines = [compact(''.join(n.itertext())) for n in xml.findall('.//{*}line')]
        row['long_budget']['single_line_paragraphs'] = sum(lines.count(t) == 1 for t in purposes)
    row['rendered_gap_text_retained'] = not any(e['code'] == 'missing-gap-text' for e in row['errors'])
    row['automated_content_checks_passed'] = not row['errors']
    return row, soup


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--build', type=Path, required=True); p.add_argument('--extra-cases', nargs='*', default=[]); a = p.parse_args()
    report = {'release_acceptance': False, 'version': '0.3.19', 'scope': 'Native bilingual PDF missing-info QA; synthetic only',
              'checker_sha256': digest(Path(__file__)), 'fixture_script_sha256': digest(HERE / 'audit.py'), 'rows': [],
              'extra_fixture_script_sha256': digest(HERE / 'extra_case.py'),
              'helper_sha256': {name: digest(ROOT / 'scripts' / name) for name in ['compare_runtime_outputs.py', 'check_narrative_outputs.py', 'check_budget_spacing_outputs.py']},
              'package_sha256': {n: digest(a.build / n) for n in ['english.zip', 'chinese.zip']},
              'limitations': ['Retained visible gap text does not prove every unanswered branch is mapped',
                              'First-answer placement is a bounded prefix check, not a universal visual quality score',
                              'Metric boxes are not glyph outlines; manual image review is separate',
                              'Known patched local Markdown worker, not stock production acceptance',
                              'No template edits, release, or production access']}
    target = HERE / 'missing-info-report.json'; assert not target.exists()
    renders = json.loads((HERE / 'render-results.json').read_text())['rows'] + json.loads((HERE / 'extra-render-results.json').read_text())
    assert len(renders) == 36 and all(r['rendered'] for r in renders)
    report['all_renders_succeeded'] = True; report['native_pdf_count'] = sum(r['format'] == 'pdf' for r in renders)
    for name in list(cases('en')) + a.extra_cases:
        soups = []
        for language in ['english', 'chinese']:
            row, soup = inspect(a.build, name, language); report['rows'].append(row); soups.append(soup)
            print(json.dumps({k: row[k] for k in ['case', 'language', 'pages', 'errors', 'reading_issues']}, ensure_ascii=False), flush=True)
        assert markers(soups[0]) == markers(soups[1]), 'Bilingual fact/status/ownership differs'
    report['all_selected_content_checks_passed'] = all(r['automated_content_checks_passed'] for r in report['rows'])
    report['all_selected_reading_checks_passed'] = all(not r['reading_issues'] for r in report['rows'])
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__': main()
