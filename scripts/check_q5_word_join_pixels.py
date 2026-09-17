"""Exact body-page raster controls: every native PDF and only unjoined Word cases."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from bs4 import BeautifulSoup
from lxml import etree as ET
from artifact_utils import sha


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('build', 'prior'): p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args(); target = a.build / 'q5-word-join-pixels.json'; assert not target.exists()
    proof = json.loads((a.build / 'q5-word-join-report.json').read_text())
    assert proof['selected_checks_passed'] and len(proof['rows']) == 20
    report = dict(passed=False, release_acceptance=False, checker_sha256=sha(Path(__file__)), rows=[],
                  native_report_sha256=sha(a.build / 'q5-word-join-report.json'),
                  limits=['100 dpi body pages only; covers excluded by unique Q1 heading',
                          'Changed Word cases have separate content and visual checks; never treated as unchanged controls'])
    try:
        for row in proof['rows']:
            stem = row['case'] + '-' + row['language']
            soup = BeautifulSoup((a.build / 'renders' / (stem + '.html')).read_text(), 'html.parser')
            heading = ''.join(soup.select_one('.question h3').get_text().split())
            for kind in ['renders'] + ([] if row['selected'] else ['word-preview']):
                paths = [root / kind / (stem + '.pdf') for root in (a.prior, a.build)]
                for path, key, root in zip(paths, ('before_sha256', 'after_sha256'), (a.prior, a.build)):
                    assert sha(path) == row[key][str(path.relative_to(root))]
                starts = []
                for path in paths:
                    bbox = ET.fromstring(subprocess.check_output(['pdftotext', '-bbox-layout', str(path), '-']))
                    pages = [''.join(''.join(page.itertext()).split()) for page in bbox.findall('.//{*}page')]
                    assert sum(page.count(heading) for page in pages) == 1
                    starts.append(next(i + 1 for i, value in enumerate(pages) if heading in value))
                assert starts[0] == starts[1]
                with tempfile.TemporaryDirectory(prefix='se-q5-pixels-') as folder:
                    hashes = []
                    for i, path in enumerate(paths):
                        subprocess.run(['pdftoppm', '-f', str(starts[i]), '-r', '100', '-png', str(path), str(Path(folder) / str(i))],
                                       check=True, capture_output=True)
                        files = sorted(Path(folder).glob(str(i) + '-*.png')); assert files
                        hashes.append([sha(file) for file in files])
                    assert hashes[0] == hashes[1], (stem, kind, 'Unchanged body pixels differ')
                report['rows'].append(dict(case=row['case'], language=row['language'], format=kind,
                    first_body_page=starts[0], identical_body_pages=len(hashes[1]), png_sha256=hashes[1],
                    before_pdf_sha256=sha(paths[0]), after_pdf_sha256=sha(paths[1])))
                print(stem + ' ' + kind, flush=True)
        report['passed'] = True
        report['identical_body_pages'] = sum(row['identical_body_pages'] for row in report['rows'])
    except Exception as error:
        report['failure'] = repr(error); raise
    finally:
        target.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(passed=True, documents=len(report['rows']), identical_body_pages=report['identical_body_pages'])))


if __name__ == '__main__': main()
