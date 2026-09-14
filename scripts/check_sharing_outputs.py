"""Check Q10/Q11 paragraph ownership, date typography and bounded 0.3.5 comparisons."""
import argparse
from collections import Counter
import json
import re
import subprocess
from pathlib import Path
from xml.etree import ElementTree as ET
from bs4 import BeautifulSoup
from docx import Document
from check_narrative_outputs import compact, page_bounds, pdf_text, sha
from check_polish_outputs import canonical_word_dates
from compare_runtime_outputs import markers

REVIEWED_ZH = {
    '資料再次使用者可向聯絡人申請取用資料。': '欲再次使用資料者，可向聯絡人申請取用。',
    '資料再次使用者可向本計畫的資料存取委員會申請取用。': '欲再次使用資料者，可向本計畫的資料存取委員會申請取用。',
    '這些條件將作為開放後設資料的一部分發布。': '這些取用條件將納入公開的後設資料。',
    '即使原始資料已不存在，後設資料仍會持續提供。': '即使資料已不存在，仍會持續提供後設資料。',
    '我們已在專案中編列預算，用於支付所使用資料儲存庫的費用。': '本計畫已編列預算，支付資料儲存庫的服務費。',
    '我們已預留預算，以支應準備資料發布所需的時間與人力。': '已預留預算，以支應資料發布準備工作所需的時間與人力。',
    '專案專用資料儲存庫。': '本計畫專用的資料儲存庫。',
}


def direct_runs(container):
    runs, pending = [], []
    for node in list(container.find_all(recursive=False)) + [None]:
        if node is not None and node.name == 'p' and 'data-gap' not in node.get('class', []):
            pending.append(node.get_text())
        elif pending:
            runs.append(pending); pending = []
    return runs


def assert_date_lines(xml, dates, start, end):
    lines = [' '.join(w.text or '' for w in line.findall('{*}word')) for line in ET.fromstring(xml).findall('.//{*}line')]
    first = next(i for i,line in enumerate(lines) if compact(line).startswith(start))
    last = next(i for i,line in enumerate(lines[first+1:], first+1) if compact(line).startswith(end))
    scoped = lines[first:last]
    for date, count in Counter(dates).items():
        pattern = re.compile(r'(?<![A-Za-z0-9-])' + re.escape(date).replace(r'\-', '[-\u2011]') + r'(?![A-Za-z0-9]|\.[A-Za-z0-9])')
        found = sum(len(pattern.findall(line)) for line in scoped)
        assert found >= count, ('date split within Q10', date, count, found)


def compare_prior(old, new, language):
    assert markers(old) == markers(new), 'Unplanned old/new fact-marker change'
    count = 0
    for question in old.select('.question'):
        qid = question['id']; current = new.find(id=qid)
        assert current is not None
        before = compact(question.get_text())
        if language == 'chinese' and qid in ('q-share-restrictions', 'q-data-preservation'):
            for source, target in REVIEWED_ZH.items(): before = before.replace(compact(source), compact(target))
            if qid == 'q-share-restrictions':
                for entry in question.select('.license-entry:not(.joined-policy)'):
                    for link in entry.select('a'):
                        href = link.get('href')
                        assert current.select_one(f'a[href="{href}"]') is not None
                        before = before.replace(compact('使用限制的詳細資訊：' + link.get_text() + '.'), compact('使用限制的詳細資訊：' + link.get_text() + '。'))
        assert before == compact(current.get_text()), (language, qid, 'Unplanned prose change')
        # Authored content is not covered by the fixed-prose replacement list.
        assert [compact(n.get_text()) for n in question.select('.answer-detail')] == [compact(n.get_text()) for n in current.select('.answer-detail')], (language, qid, 'Authored block changed')
        count += 1
    assert count == 15
    return count


def inspect(build, prior, case, language):
    base = build / 'renders' / f'{case}-{language}'
    soup = BeautifulSoup(base.with_suffix('.html').read_text(), 'html.parser')
    word = Document(base.with_suffix('.docx'))
    raw_paragraphs = [p.text for p in word.paragraphs]
    paragraphs = [canonical_word_dates(soup, p) for p in raw_paragraphs]
    pdf = pdf_text(base.with_suffix('.pdf'))
    questions = [soup.find(id=q) for q in ('q-share-restrictions', 'q-data-preservation')]
    joined, authored = 0, []
    for question in questions:
        assert not question.select('p p, p div, p ul, p table, .dataset-policy > p.data-gap')
        for unit in question.select('.license-summary, .restriction-process, .preservation-summary, .preservation-resources'):
            for run in direct_runs(unit):
                expected = compact(''.join(run))
                standard = 'license-summary' in unit.get('class', []) and unit.find_parent(class_='joined-policy') is not None
                assert any(expected in compact(p) if standard else expected == compact(p) for p in paragraphs), (case, language, 'Owned run is not one Word paragraph', run)
                if len(run) > 1: joined += 1
        for node in question.select('p, li'):
            expected = compact(node.get_text())
            assert expected in compact(pdf) and expected in compact(''.join(paragraphs)), (case, language, 'Missing text', node.get_text())
        for node in question.select('.data-gap, .answer-detail > p'):
            assert compact(node.get_text()) in [compact(p) for p in paragraphs], (case, language, 'Gap/authored paragraph not separate', node.get_text())
        authored.extend(compact(n.get_text()) for n in question.select('.answer-detail > p'))
    available = Counter(compact(p) for p in paragraphs)
    assert all(available[p] >= n for p,n in Counter(authored).items()), 'Repeated authored paragraphs missing'
    dates = [n.get_text() for n in soup.select('#q-share-restrictions .date-value')]
    for date in dates:
        assert any(date.replace('-', '\u2011') in p for p in raw_paragraphs), (case, language, 'Word nonbreaking date lost', date)
    start = compact(questions[0].h3.get_text())[:12]; end = compact(questions[1].h3.get_text())[:12]
    for path in (base.with_suffix('.pdf'), build / 'word-preview' / (base.name + '.pdf')):
        if path.exists() and dates:
            assert_date_lines(subprocess.check_output(['pdftotext', '-bbox-layout', str(path), '-']), dates, start, end)
    if case == 'sharing-custom':
        for name in ('Access-2027-12-31.csv', 'Budget-2027-12-31.csv'):
            assert name in pdf and any(name in p for p in raw_paragraphs), (case, 'Filename changed', name)
        assert soup.select_one('[data-fact-id="restriction-custom-process"][data-status="complete"]')
        assert ('will not be published' if language == 'english' else '不會納入公開的後設資料') in questions[0].get_text()
    if case == 'sharing-missing':
        for fact in ('distribution-restriction-terms', 'restriction-custom-process', 'restriction-metadata-publication', 'retention-period', 'retention-payment'):
            assert soup.select_one(f'[data-fact-id="{fact}"]'), (case, fact)
        assert len(dates) == 1, 'Missing date must not be fabricated'
    if case == 'narrative-long':
        needle = 'Extended access condition remains in the document.' if language == 'english' else '延伸取用條件仍須完整保留於文件中。'
        assert sum(needle in p for p in raw_paragraphs) == 80
        assert compact(pdf).count(compact(needle)) == 80
    comparisons = 0
    if prior and (previous := prior / 'renders' / (base.name + '.html')).exists():
        comparisons = compare_prior(BeautifulSoup(previous.read_text(), 'html.parser'), soup, language)
    row = {'case': case, 'language': language, 'passed': True, 'joined_owned_runs': joined, 'date_values': dates,
           'separate_authored_paragraphs': len(authored), 'controlled_question_comparisons': comparisons, 'pdf_pages': page_bounds(base.with_suffix('.pdf'))}
    preview = build / 'word-preview' / (base.name + '.pdf')
    if preview.exists(): row['word_preview_pages'] = page_bounds(preview)
    return soup, row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--prior', type=Path)
    parser.add_argument('--cases', nargs='+', required=True)
    args = parser.parse_args()
    report = {'selected_checks_passed': False, 'release_acceptance': False, 'rows': [], 'checker_sha256': sha(Path(__file__)),
              'date_helper_sha256': sha(Path(__file__).with_name('check_polish_outputs.py')),
              'text_extractor_sha256': sha(Path(__file__).with_name('check_narrative_outputs.py')),
              'package_sha256': {n: sha(args.build / n) for n in ('english.zip', 'chinese.zip')},
              'artifact_sha256': {str(p.relative_to(args.build)): sha(p) for folder in ('renders', 'word-preview') for p in sorted((args.build / folder).glob('*')) if p.is_file()},
              'limits': ['Synthetic selected cases only', 'Only the recorded Q10/Q11 Chinese phrase changes allowed in prior comparisons', 'ISO-shaped dates only, not date validity or filenames', 'LibreOffice is not Microsoft Word acceptance', 'Stock Markdown table support remains blocked']}
    path = args.build / 'sharing-report.json'
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    try:
        for case in args.cases:
            pair = []
            for language in ('english', 'chinese'):
                soup, row = inspect(args.build, args.prior, case, language)
                pair.append(soup); report['rows'].append(row)
            assert markers(pair[0]) == markers(pair[1]), (case, 'Bilingual marker mismatch')
    except Exception as error:
        report['failure'] = str(error); path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n'); raise
    report['selected_checks_passed'] = True
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'passed': True, 'pairs': len(report['rows']), 'comparisons': sum(r['controlled_question_comparisons'] for r in report['rows'])}))


if __name__ == '__main__': main()
