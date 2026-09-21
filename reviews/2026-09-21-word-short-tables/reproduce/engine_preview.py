"""Standalone Word-engine stress preview, explicitly not native API acceptance."""
import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from lxml import etree
from docx import Document
from docx.oxml.ns import qn
from table_recipe import ROOT, sha
from table_probe import cases

sys.path.insert(0, str(ROOT / 'scripts'))
from check_word_short_budget_outputs import word_pages
from notice_native import generated_o_markers
from notice_probe import compact


def inspect(root):
    names = {name for name, _, _ in cases()}; rows = []
    for phase in ['before', 'after']:
        document = Document(root / (phase + '.docx')); pdf = root / (phase + '.pdf')
        bbox = subprocess.check_output(['pdftotext', '-bbox-layout', str(pdf), '-'])
        raw = subprocess.check_output(['pdftotext', '-raw', str(pdf), '-'], text=True)
        pages = word_pages(raw, bbox)
        expected = compact(''.join(n.text or '' for n in document.element.body.iter(qn('w:t'))))
        counts = Counter(c for c in ''.join(pages) if c not in {'•', '◦', '\uf0b7', '\uf0a1'})
        counts.subtract({'o': generated_o_markers(document, bbox)})
        # Every Item/Value token in this synthetic matrix is a table header.
        # Remove only geometrically grouped generated header instances, and
        # remove the corresponding actual tblHeader rows from the Word oracle.
        source_headers = Counter(); source_header_text = Counter()
        for row in document.element.body.iter(qn('w:tr')):
            header = row.find(qn('w:trPr') + '/' + qn('w:tblHeader'))
            if header is None: continue
            assert header.get(qn('w:val')) == 'on'
            words = [n.text for n in row.iter(qn('w:t'))]
            assert words[0] == 'Item' and all(w == 'Value' for w in words[1:])
            source_headers[len(words)-1] += 1; source_header_text.update(''.join(words))
        xml = etree.fromstring(bbox)
        rendered_headers = Counter(); rendered_header_text = Counter()
        for page in xml.findall('.//{*}page'):
            levels = {}
            for word in page.findall('.//{*}word'):
                if word.text in ['Item', 'Value']: levels.setdefault(round(float(word.get('yMin')), 2), []).append(word)
            for words in levels.values():
                words.sort(key=lambda w: float(w.get('xMin'))); assert words[0].text == 'Item'
                values = None
                for word in words:
                    rendered_header_text.update(word.text)
                    if word.text == 'Item':
                        if values is not None: rendered_headers[values] += 1
                        values = 0
                    else: values += 1
                rendered_headers[values] += 1
        assert not (source_headers - rendered_headers) and set(rendered_headers) <= set(source_headers)
        counts.subtract(rendered_header_text)
        expected_counts = Counter(expected); expected_counts.subtract(source_header_text)
        assert counts == expected_counts, (phase, counts-expected_counts, expected_counts-counts)
        text_pages = subprocess.check_output(['pdftotext', '-layout', str(pdf), '-'], text=True).split('\f')
        coverage = {name: [] for name in names}; current = None
        for index, text in enumerate(text_pages, 1):
            for line in text.splitlines():
                if line.strip().startswith('CASE: '):
                    current = line.strip()[6:]; assert current in names
                if current and line.split() == ['N/A', 'N/A'] and index not in coverage[current]: coverage[current].append(index)
        for name in ['many-rows', 'mixed-separated']:
            assert len(coverage[name]) >= 2, (phase, name, 'Long table did not span pages')
        rows.append(dict(phase=phase, pages=len(pages), long_controls={n: coverage[n] for n in ['many-rows', 'mixed-separated']},
                         docx_sha256=sha((root / (phase + '.docx')).read_bytes()), pdf_sha256=sha(pdf.read_bytes()),
                         exact_nonheader_characters=True, verified_extra_headers=dict(rendered_headers-source_headers)))
    return rows


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--engine', type=Path, required=True)
    p.add_argument('--check-only', action='store_true'); p.add_argument('--output', type=Path); a = p.parse_args()
    target = a.output or a.engine / 'preview.json'; assert not target.exists()
    if not a.check_only:
        for phase in ['before', 'after']:
            assert not (a.engine / (phase + '.pdf')).exists()
            with tempfile.TemporaryDirectory(prefix='short-table-engine-lo-') as folder:
                subprocess.run(['libreoffice', '-env:UserInstallation=' + Path(folder).as_uri(), '--headless', '--convert-to', 'pdf',
                    '--outdir', str(a.engine), str(a.engine / (phase + '.docx'))], capture_output=True, check=True, timeout=120)
    report = dict(passed=False, native_checked=False, release_acceptance=False, checker_sha256=sha(Path(__file__).read_bytes()))
    try: report['rows'] = inspect(a.engine); report['passed'] = True
    except Exception as error: report['failure'] = repr(error); raise
    finally: target.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))
