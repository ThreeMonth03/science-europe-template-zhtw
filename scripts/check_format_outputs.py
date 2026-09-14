"""Q2 format/volume artifact and narrowly scoped 0.3.3 comparison checks."""
import argparse
import copy
import json
from pathlib import Path
from bs4 import BeautifulSoup
from docx import Document
from check_narrative_outputs import compact, pdf_text, page_bounds, sha


def compare_unchanged(before, after):
    assert len(before.select('.question')) == len(after.select('.question')) == 15
    for old in before.select('.question'):
        qid = old['id']; new = after.find(id=qid)
        if qid == 'q-what-data':
            old, new = copy.deepcopy(old), copy.deepcopy(new)
            for node in (old, new):
                headings = [h for h in node.select('h4') if h.get_text(strip=True) in ('Data formats and types', '資料格式與類型')]
                assert len(headings) <= 1
                if headings:
                    # Remove only the immediately following format wrapper and its label.
                    wrapper = headings[0].find_next_sibling()
                    assert wrapper.name == 'div'
                    wrapper.decompose(); headings[0].decompose()
        assert compact(old.get_text()) == compact(new.get_text()), (qid, 'change outside Q2 formats')
    return 15


def inspect(build, case, language):
    base = build / 'renders' / f'{case}-{language}'
    soup = BeautifulSoup(base.with_suffix('.html').read_text(), 'html.parser')
    doc = Document(base.with_suffix('.docx')); paragraphs = [p.text for p in doc.paragraphs]
    pdf = pdf_text(base.with_suffix('.pdf')); summaries = soup.select('.format-summary')
    for summary in summaries:
        assert summary.find_parent(class_='format-description')
        assert not summary.select('.data-gap, ul, br, p p, p div')
        expected = compact(summary.get_text())
        assert expected in compact(pdf)
        assert any(expected == compact(p) for p in paragraphs), (case, language, 'Word format summary fragmented')
    q2 = soup.find(id='q-what-data')
    for node in q2.select('.format-description p, .format-description li'):
        text = compact(node.get_text())
        assert text in compact(pdf) and text in compact(''.join(paragraphs)), (case, language, text)
    if case == 'format-rich':
        assert len(summaries) == 1
        detail = q2.select_one('[data-fact-id="nonstandard-reason"][data-status="complete"]')
        assert len(detail.select('p:not(.answer-lead)')) == 2 and len(detail.select('ul > li')) == 2
        for p in detail.select('p:not(.answer-lead)'):
            assert any(compact(p.get_text()) == compact(v) for v in paragraphs)
        for text in ('JSON', 'CSV', 'MyInstrument v1.2', 'station_YYYYMMDD.csv', '0.0001'):
            assert text in q2.get_text() and text in pdf and text in '\n'.join(paragraphs)
        assert not q2.select('.format-description .data-gap')
        assert '0.0 GB in total' not in q2.get_text()
    if case == 'format-partial':
        assert len(summaries) == 4
        assert len(q2.select('[data-fact-id="format-file-count"]')) == 2
        assert len(q2.select('[data-fact-id="format-file-size"]')) == 2
        assert len(q2.select('[data-fact-id="format-conversion"]')) == 4
        assert len(q2.select('[data-fact-id="nonstandard-reason"][data-status="missing"]')) == 4
        assert len(q2.select('[data-fact-id="format-name"]')) == 1
        for token in ('12', '0.25', '0'):
            assert token in q2.get_text()
    row = {'case': case, 'language': language, 'format_summaries': len(summaries), 'pdf_pages': page_bounds(base.with_suffix('.pdf')), 'passed': True}
    preview = build / 'word-preview' / (base.name + '.pdf')
    if preview.exists(): row['word_preview_pages'] = page_bounds(preview)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--prior', type=Path)
    parser.add_argument('--cases', nargs='+', required=True)
    args = parser.parse_args(); rows = []; comparisons = 0
    for case in args.cases:
        for language in ('english', 'chinese'):
            rows.append(inspect(args.build, case, language))
            name = f'{case}-{language}.html'
            if args.prior and (args.prior / 'renders' / name).exists():
                old, new = args.prior / 'renders' / name, args.build / 'renders' / name
                for fmt in ('html', 'pdf', 'docx'):
                    a, b = [json.loads(p.with_suffix('.' + fmt + '.fixture.json').read_text()) for p in (old, new)]
                    for key in ('recipe_sha256', 'events_sha256', 'km_sha256'): assert a[key] == b[key], (case, language, key)
                comparisons += compare_unchanged(*[BeautifulSoup(p.read_text(), 'html.parser') for p in (old, new)])
    report = {'selected_checks_passed': True, 'release_acceptance': False, 'checker_sha256': sha(Path(__file__)), 'rows': rows,
              'controlled_question_comparisons': comparisons,
              'package_sha256': {name: sha(args.build / name) for name in ('english.zip', 'chinese.zip')},
              'artifact_sha256': {str(p.relative_to(args.build)): sha(p) for folder in ('renders', 'word-preview') for p in sorted((args.build / folder).glob('*')) if p.is_file()},
              'limits': ['Only Q2 format wrapper excluded from old/new comparison; remaining Q2 and 14 questions unchanged', 'No computed total from file count/size; original quantities retained without coercion', 'Not full Science Europe coverage or Microsoft Word acceptance']}
    (args.build / 'format-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'passed': True, 'pairs': len(rows), 'comparisons': comparisons}))


if __name__ == '__main__': main()
