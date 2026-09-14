"""Verify owned Q2/Q10 reading units without flattening free answers or hiding gaps."""
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


def owned_runs(unit):
    flat = []
    def collect(node, owned=False):
        for child in node.find_all(recursive=False):
            classes = child.get('class', [])
            if 'joined-policy' in classes or (owned and 'answer-lead' in classes): collect(child, True)
            elif child.name == 'p' and 'data-gap' not in classes and 'answer-lead' not in classes: flat.append(child.get_text())
            else: flat.append(None)
    collect(unit)
    runs, pending = [], []
    for value in flat + [None]:
        if value is not None: pending.append(value)
        elif pending: runs.append(pending); pending = []
    return [run for run in runs if len(run) > 1]


def assert_quantity_lines(pdf, quantities):
    root = ET.fromstring(subprocess.check_output(['pdftotext', '-bbox-layout', str(pdf), '-']))
    lines = [' '.join(w.text or '' for w in line.findall('{*}word')) for line in root.findall('.//{*}line')]
    for quantity, count in Counter(quantities).items():
        pattern = re.compile(r'(?<![0-9.])' + r'\s*'.join(re.escape(part) for part in quantity.split()) + r'(?![A-Za-z])')
        found = sum(len(pattern.findall(line)) for line in lines)
        assert found >= count, (pdf, 'quantity split across lines', quantity, count, found)


def inspect(build, case, language):
    base = build / 'renders' / f'{case}-{language}'
    soup = BeautifulSoup(base.with_suffix('.html').read_text(), 'html.parser')
    doc = Document(base.with_suffix('.docx')); paragraphs = [p.text for p in doc.paragraphs]
    pdf = pdf_text(base.with_suffix('.pdf')); q10 = soup.find(id='q-share-restrictions')
    joined = 0
    for unit in q10.select('.distribution-reading-unit'):
        assert not unit.select('.joined-policy .answer-detail, .joined-policy .data-gap, :scope > p.data-gap')
        for run in owned_runs(unit):
            assert any(compact(''.join(run)) == compact(p) for p in paragraphs), (case, language, 'Q10 not a single owned Word paragraph', run)
            joined += 1
    for p in q10.select('.data-gap, .answer-detail > p'):
        assert any(compact(p.get_text()) == compact(v) for v in paragraphs), (case, language, 'gap/free paragraph joined', p.get_text())
    for node in q10.select('p, li'):
        expected = compact(node.get_text())
        assert expected in compact(pdf) and expected in compact(''.join(paragraphs)), (case, language, 'Q10 text missing', node.get_text())
    gaps = soup.select('.format-description > p.data-gap')
    for gap in gaps:
        text = gap.get_text()
        lead, terminal, separator = ('尚待補充：', '。', '、') if language == 'chinese' else ('Information still needed:', '.', ', ')
        assert text.count(lead) == text.count(terminal) == 1, (language, text)
        assert text.count(separator) == len(gap.select('[data-status="missing"]')) - 1, (language, text)
    quantities = [q.get_text() for q in soup.select('.format-summary .quantity')]
    for quantity in quantities:
        assert '\xa0' in quantity and any(quantity in p for p in paragraphs), (case, language, 'Word nonbreaking quantity lost', quantity)
    assert_quantity_lines(base.with_suffix('.pdf'), quantities)
    row = {'case': case, 'language': language, 'joined_q10_runs': joined, 'consolidated_format_gaps': len(gaps), 'nonbreaking_quantities': quantities, 'pdf_pages': page_bounds(base.with_suffix('.pdf')), 'passed': True}
    preview = build / 'word-preview' / (base.name + '.pdf')
    if preview.exists():
        assert_quantity_lines(preview, quantities)
        row['word_preview_pages'] = page_bounds(preview)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--cases', nargs='+', required=True)
    args = parser.parse_args()
    report = {'selected_checks_passed': False, 'release_acceptance': False, 'rows': [], 'checker_sha256': sha(Path(__file__)),
              'text_extractor_sha256': sha(Path(__file__).with_name('check_narrative_outputs.py')),
              'package_sha256': {n: sha(args.build / n) for n in ('english.zip', 'chinese.zip')},
              'artifact_sha256': {str(p.relative_to(args.build)): sha(p) for folder in ('renders', 'word-preview') for p in sorted((args.build / folder).glob('*')) if p.is_file()},
              'limits': ['Selected synthetic inputs only', 'Complex repositories and restricted licence blocks deliberately excluded from joining', 'LibreOffice preview is not Microsoft Word acceptance', 'Stock Markdown table support remains blocked']}
    path = args.build / 'polish-report.json'
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    try:
        for case in args.cases:
            for language in ('english', 'chinese'):
                report['rows'].append(inspect(args.build, case, language))
    except Exception as error:
        report['failure'] = str(error)
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        raise
    report['selected_checks_passed'] = True
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'passed': True, 'pairs': len(report['rows'])}))


if __name__ == '__main__': main()
