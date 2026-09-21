"""Fresh diagnostic DOCX copies, never production/native output replacements."""
import argparse
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile
from lxml import etree
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'scripts')]
from artifact_utils import sha
from rehearse_profile_pagination import geometry
from check_header_controls import raster_digest


def change(source, target, mode):
    with zipfile.ZipFile(source) as original:
        tree = etree.fromstring(original.read('word/document.xml'))
        tables = [t for t in tree.iter(qn('w:tbl')) if [
            [''.join(c.itertext()) for c in r.findall(qn('w:tc'))] for r in t.findall(qn('w:tr'))
        ] == [['Item', 'Value'], ['Original.csv', '0'], ['N/A', 'Retained.']]]
        assert len(tables) == 1
        styles = etree.fromstring(original.read('word/styles.xml'))
        if mode == 'style-both':
            assert not styles.xpath("./w:style[@w:styleId='PilotShortAnswerTable']", namespaces={'w': qn('w:style')[1:].split('}')[0]})
            style = etree.SubElement(styles, qn('w:style'), {qn('w:type'): 'table', qn('w:styleId'): 'PilotShortAnswerTable'})
            etree.SubElement(style, qn('w:name'), {qn('w:val'): 'PilotShortAnswerTable'})
            etree.SubElement(style, qn('w:basedOn'), {qn('w:val'): 'Table'})
            etree.SubElement(etree.SubElement(style, qn('w:trPr')), qn('w:cantSplit'))
            table_style = tables[0].find(qn('w:tblPr') + '/' + qn('w:tblStyle'))
            assert table_style is not None and table_style.get(qn('w:val')) == 'Table'
            table_style.set(qn('w:val'), 'PilotShortAnswerTable')
        rows = tables[0].findall(qn('w:tr'))
        for index, row in enumerate(rows):
            if mode in ['cant-split', 'both']:
                pr = row.find(qn('w:trPr'))
                if pr is None: pr = etree.Element(qn('w:trPr')); row.insert(0, pr)
                assert pr.find(qn('w:cantSplit')) is None
                etree.SubElement(pr, qn('w:cantSplit'))
            if mode in ['keep-nonfinal', 'both', 'style-both'] and index < len(rows) - 1:
                for p in row.iter(qn('w:p')):
                    style = p.find(qn('w:pPr') + '/' + qn('w:pStyle'))
                    assert style is not None and style.get(qn('w:val')) == 'Compact'
                    style.set(qn('w:val'), 'PilotTableLead')
        with zipfile.ZipFile(target, 'x') as new:
            for entry in original.infolist():
                raw = original.read(entry.filename)
                if entry.filename == 'word/document.xml' and mode != 'baseline':
                    raw = etree.tostring(tree, xml_declaration=True, encoding='UTF-8', standalone=True)
                if entry.filename == 'word/styles.xml' and mode == 'style-both':
                    raw = etree.tostring(styles, xml_declaration=True, encoding='UTF-8', standalone=True)
                new.writestr(copy.copy(entry), raw)


def run(archive, output, modes=None):
    assert not output.exists(); output.mkdir(parents=True)
    report = dict(diagnostic_only=True, native_checked=False, release_acceptance=False,
                  script_sha256=sha(Path(__file__)),
                  libreoffice=subprocess.check_output(['libreoffice', '--version'], text=True).strip(), rows=[])
    for language in ['chinese', 'english']:
        for profile in ['review', 'submission']:
            name = 'ethics-long-' + profile + '-' + language
            source = archive / 'after/renders' / (name + '.docx')
            native = archive / 'after/word-preview' / (name + '.pdf')
            for mode in modes or ['baseline', 'keep-nonfinal', 'cant-split', 'both', 'style-both']:
                target = output / (name + '-' + mode + '.docx'); change(source, target, mode)
                with tempfile.TemporaryDirectory(prefix='table-flow-lo-') as folder:
                    subprocess.run(['libreoffice', '-env:UserInstallation=' + Path(folder).as_uri(), '--headless',
                                    '--convert-to', 'pdf', '--outdir', str(output), str(target)], check=True, capture_output=True, timeout=90)
                pdf = target.with_suffix('.pdf')
                pages = subprocess.check_output(['pdftotext', '-layout', str(pdf), '-'], text=True).split('\f')
                if not pages[-1].strip(): pages.pop()
                positions = {key: [i for i, text in enumerate(pages, 1) if key in text]
                             for key in ['Item', 'Value', 'Retained.', 'LIST-B:', 'FINAL-AUTHORED-PARAGRAPH:']}
                if mode == 'baseline':
                    assert geometry(pdf) == geometry(native) and raster_digest(pdf) == raster_digest(native)
                row = dict(language=language, profile=profile, mode=mode, positions=positions, pages=len(pages),
                           source_sha256=sha(source), docx_sha256=sha(target), pdf_sha256=sha(pdf))
                report['rows'].append(row); (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
                print(json.dumps(row), flush=True)
    report['completed'] = True; (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    p.add_argument('--modes', nargs='+', choices=['baseline', 'keep-nonfinal', 'cant-split', 'both', 'style-both'])
    a = p.parse_args(); run(a.archive, a.output, a.modes)
