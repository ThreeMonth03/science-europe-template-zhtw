"""Detect the observed Q8 short label/permission split; preserve failures as evidence."""
import argparse
import json
from pathlib import Path
import re
import subprocess
from bs4 import BeautifulSoup
from artifact_utils import sha


def compact(value): return re.sub(r'\s+', '', value)


def locations(pages, heading, following, pairs):
    pages = list(map(compact, pages)); text = ''.join(pages)
    start = text.index(compact(heading)); end = text.index(compact(following), start+len(compact(heading)))
    def page(position):
        offset = 0
        for i, value in enumerate(pages, 1):
            if offset <= position < offset+len(value): return i
            offset += len(value)
        raise AssertionError('Text position outside pages')
    cursor = start; rows = []
    for label, permission in pairs:
        label, permission = compact(label), compact(permission)
        at = text.find(label, cursor, end); assert at >= 0, 'Label missing within Q8'
        then = text.find(permission, at+len(label), end); assert then >= 0, 'Permission missing after label within Q8'
        row = {'label': label, 'label_page': page(at), 'permission_page': page(then),
               'label_end_page': page(at+len(label)-1), 'permission_end_page': page(then+len(permission)-1)}
        row['together'] = len({row[k] for k in ['label_page', 'label_end_page', 'permission_page', 'permission_end_page']}) == 1
        rows.append(row); cursor = then+len(permission)
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', type=Path, required=True); p.add_argument('--cases', nargs='+', required=True)
    p.add_argument('--output', type=Path, required=True); a = p.parse_args(); assert not a.output.exists()
    report = {'passed': False, 'release_acceptance': False, 'rows': [], 'checker_sha256': sha(Path(__file__)),
              'package_sha256': {n: sha(a.build/n) for n in ['english.zip', 'chinese.zip']},
              'scope': 'Q8 reference list entries with a simple dataset label and a short permission sentence; actual native PDF / LibreOffice page text'}
    try:
        for case in a.cases:
            for language in ['english', 'chinese']:
                stem = case+'-'+language; source = a.build/'renders'/(stem+'.html')
                soup = BeautifulSoup(source.read_text(), 'html.parser'); q8 = soup.select_one('#q-copyright-ipr')
                pairs = []
                for item in q8.select('.answer > ul > li'):
                    label = item.find('div', recursive=False)
                    if label is None: continue
                    # Only the known short plain permission sibling: complex
                    # authored restrictions are outside this bounded probe.
                    following = list(label.next_siblings)
                    if any(getattr(n, 'name', None) for n in following): continue
                    permission = ''.join(str(n) for n in following).strip()
                    if not permission or len(permission) > 200: continue
                    pairs.append((label.get_text(), permission))
                for fmt, path in [('native-pdf', a.build/'renders'/(stem+'.pdf')), ('word-preview', a.build/'word-preview'/(stem+'.pdf'))]:
                    pages = [v for v in subprocess.check_output(['pdftotext', '-raw', str(path), '-'], text=True).split('\f') if v.strip()]
                    values = locations(pages, q8.h3.get_text(), soup.select_one('#q-ethical-issues h3').get_text(), pairs)
                    report['rows'].append({'case': case, 'language': language, 'format': fmt, 'entries': values,
                                           'html_sha256': sha(source), 'pdf_sha256': sha(path)})
        report['failures'] = [{'case': r['case'], 'language': r['language'], 'format': r['format'], **entry}
                              for r in report['rows'] for entry in r['entries'] if not entry['together']]
        report['passed'] = not report['failures']
    finally:
        a.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'passed': report['passed'], 'failures': report.get('failures', [])}, ensure_ascii=False))
    raise SystemExit(0 if report['passed'] else 2)


if __name__ == '__main__': main()
