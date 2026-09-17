"""Local diagnostic derivatives only: test paragraph keeps without changing templates."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
import zipfile
from docx import Document
from docx.text.paragraph import Paragraph
from docx.oxml.ns import qn
from lxml import etree
from bs4 import BeautifulSoup
from artifact_utils import sha
from check_storage_context_outputs import word_parts,locations


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();assert not a.output.exists();a.output.mkdir(parents=True)
    source=a.build/'renders/metadata-partial-chinese.docx'
    soup=BeautifulSoup((a.build/'renders/metadata-partial-chinese.html').read_text(),'html.parser')
    rows=[]
    for mode,indices,key in [('direct-next',[1,2,3],'keepNext'),('policy-lines',[1],'keepLines'),('lead-lines',[1,2],'keepLines'),('all-lines',[1,2,3,4],'keepLines')]:
        d=Document(source);paragraphs=[n for n in word_parts(d)[1] if n.tag==qn('w:p')]
        for index in indices:
            properties=paragraphs[index].find(qn('w:pPr'))
            assert properties.find(qn('w:'+key)) is None
            etree.SubElement(properties,qn('w:'+key))
        target=a.output/(mode+'.docx')
        with zipfile.ZipFile(source) as old,zipfile.ZipFile(target,'w') as new:
            for item in old.infolist():
                data=etree.tostring(d.element,encoding='UTF-8',xml_declaration=True,standalone=True) if item.filename=='word/document.xml' else old.read(item)
                new.writestr(item,data)
        with tempfile.TemporaryDirectory(prefix='q5-keep-lo-') as profile:
            subprocess.run(['libreoffice','-env:UserInstallation='+Path(profile).as_uri(),'--headless','--convert-to','pdf','--outdir',str(a.output),str(target)],check=True,capture_output=True)
        row=dict(mode=mode,q5_locations=locations(target.with_suffix('.pdf'),soup),docx_sha256=sha(target),preview_sha256=sha(target.with_suffix('.pdf')))
        rows.append(row);print(json.dumps(row),flush=True)
    (a.output/'report.json').write_text(json.dumps(dict(diagnostic_not_native=True,source_sha256=sha(source),rows=rows),indent=2)+'\n')


if __name__=='__main__':main()
