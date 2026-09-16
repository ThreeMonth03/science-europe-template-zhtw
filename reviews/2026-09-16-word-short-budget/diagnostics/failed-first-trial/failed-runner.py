"""Width-only trials on copied native DOCX, not new DSW exports."""
import argparse
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import zipfile
from lxml import etree as E
from artifact_utils import sha
from check_short_budget_outputs import prompt_lines

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
def q(n): return '{'+W+'}'+n


def widths(table, fractions):
    grid = table.find(q('tblGrid')); nodes = list(grid)
    assert len(nodes) == 3
    total = sum(int(n.get(q('w'))) for n in nodes)
    values = [round(total*f) for f in fractions[:2]]
    values.append(total-sum(values))
    for n, value in zip(nodes, values): n.set(q('w'), str(value))
    for row in table.findall(q('tr')):
        cells = row.findall(q('tc')); assert len(cells) == 3
        for cell, value in zip(cells, values):
            width = cell.find(q('tcPr')).find(q('tcW'))
            assert width is not None and width.get(q('type')) == 'dxa'
            width.set(q('w'), str(value))
    return values


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prior',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    report={'release_acceptance':False,'native_export':False,'rows':[],'checker_sha256':sha(Path(__file__))}
    for case in ['partial','budget-mixed-gaps']:
        for lang in ['english','chinese']:
            source=a.prior/'renders'/(case+'-'+lang+'.docx')
            with zipfile.ZipFile(source) as z: entries={n:z.read(n) for n in z.namelist()}
            for name, fractions in [('baseline',(.57,.17,.26)),('width-49',(.49,.25,.26)),('width-46',(.46,.28,.26))]:
                doc=E.fromstring(entries['word/document.xml']);tables=doc.findall('.//'+q('tbl'))
                target=tables[-1]
                header=''.join(target.find(q('tr')).itertext())
                assert ('Resource and purpose' in header if lang=='english' else '資源項目與用途' in header)
                original=copy.deepcopy(target)
                if name!='baseline': values=widths(target,fractions)
                else: values=[int(n.get(q('w'))) for n in target.find(q('tblGrid'))]
                # Restore only changed width attributes to prove all other XML identical.
                restored=copy.deepcopy(target)
                for old,new in zip(original.iter(),restored.iter()):
                    assert old.tag==new.tag
                    if old.tag in [q('gridCol'),q('tcW')]: new.attrib.clear();new.attrib.update(old.attrib)
                assert E.tostring(restored,method='c14n')==E.tostring(original,method='c14n')
                stem=case+'-'+lang+'-'+name;out=a.output/(stem+'.docx')
                with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
                    for key,data in entries.items():z.writestr(key,E.tostring(doc) if key=='word/document.xml' else data)
                with tempfile.TemporaryDirectory(prefix='se-word-width-lo-') as temp:
                    subprocess.run(['libreoffice','-env:UserInstallation='+Path(temp).as_uri(),'--headless','--convert-to','pdf','--outdir',str(a.output),str(out)],check=True,capture_output=True)
                pdf=out.with_suffix('.pdf');assert pdf.is_file()
                info=subprocess.check_output(['pdfinfo',str(pdf)],text=True)
                row={'case':case,'language':lang,'variant':name,'width_twips':values,
                    'pages':int(next(line.split(':')[1] for line in info.splitlines() if line.startswith('Pages:'))),
                    'source_sha256':sha(source),'docx_sha256':sha(out),'pdf_sha256':sha(pdf),'only_widths_changed':True}
                if case=='partial':row['missing_currency_lines']=prompt_lines(pdf,'Information not provided: currency.' if lang=='english' else '幣別尚未提供。')
                report['rows'].append(row);print(json.dumps(row,ensure_ascii=False),flush=True)
    (a.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':main()
