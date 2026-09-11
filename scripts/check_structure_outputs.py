"""Selected 0.2.2 output regressions, not complete answer or visual acceptance."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from bs4 import BeautifulSoup
from docx import Document


def check(build):
    checks = []
    for case in ('representative', 'retention-partial', 'structured', 'structured-partial'):
        for language in ('english', 'chinese'):
            base = build / 'renders' / f'{case}-{language}'
            if not base.with_suffix('.html').exists():
                continue
            html = BeautifulSoup(base.with_suffix('.html').read_text(), 'html.parser')
            for question in ('q-copyright-ipr', 'q-ethical-issues', 'q-data-preservation', 'q-persistent-identifier'):
                section = html.find(id=question)
                assert section is not None
                assert not section.select('p p, p ul, p ol, p div, p table'), (case, language, question, 'nested block')
                assert all(child.name == 'li' for ul in section.select('ul, ol') for child in ul.find_all(recursive=False)), (case, language, question, 'invalid list child')
            assert len(html.select('.ethical-project')) == 1, 'Project duplicated or omitted'
            q11 = html.find(id='q-data-preservation')
            warnings = {node.get('data-fact-id') for node in q11.select('[data-status="needs-review"]')}
            if case.startswith('structured'):
                assert not warnings, (case, language, warnings)
                duration = '10 years' if language == 'english' else '10 年'
            else:
                assert warnings == {'retention-period', 'retention-payment'}, (case, language, warnings)
                duration = None
            pdf_text = subprocess.check_output(['pdftotext', str(base.with_suffix('.pdf')), '-'], text=True)
            doc = Document(base.with_suffix('.docx'))
            word_text = '\n'.join(p.text for p in doc.paragraphs)
            needles = ['station_YYYYMMDD.csv', 'CHANGELOG.md'] if not case.endswith('partial') else []
            if duration:
                needles.append(duration)
            for fmt, text in [('html', html.get_text(' ', strip=True)), ('pdf', pdf_text), ('docx', word_text)]:
                for needle in needles:
                    assert ''.join(needle.split()) in ''.join(text.split()), (case, language, fmt, needle)
            checks.append({'case': case, 'language': language, 'selected_checks_passed': True,
                           'review_warnings': sorted(warnings)})
    assert checks, 'No requested structure fixtures were rendered'
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    args = parser.parse_args()
    report = {'checks': check(args.build), 'selected_regressions_passed': True,
              'release_acceptance': False,
              'scope': 'Selected block structure, project count, review markers, duration and case-sensitive filenames; not all SE requirements or visual approval',
              'checker_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (args.build / 'structure-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
