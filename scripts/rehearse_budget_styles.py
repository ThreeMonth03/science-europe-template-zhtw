"""Disposable DOCX-only diagnosis; never overwrite native DSW documents."""
import argparse
from pathlib import Path
import json
import zipfile
from lxml import etree
from artifact_utils import sha

NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
W='{'+NS['w']+'}'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True); p.add_argument('--out',type=Path,required=True)
    a=p.parse_args(); a.out.mkdir(parents=True,exist_ok=False)
    with zipfile.ZipFile(a.source) as z: parts={n:z.read(n) for n in z.namelist()}
    report={'source_sha256':sha(a.source),'release_acceptance':False,'variants':{}}
    for profile in ['compact','release-keeps','compact-release','keep-overview']:
        root=etree.fromstring(parts['word/document.xml']); table=root.findall('.//w:body/w:tbl',NS)[-1]
        if profile=='keep-overview':
            active=False
            for para in root.findall('.//w:body/w:p',NS):
                text=''.join(para.itertext())
                if text.startswith('15. '): active=True
                if active:
                    prop=para.find('w:pPr',NS)
                    if prop is None: prop=etree.Element(W+'pPr'); para.insert(0,prop)
                    etree.SubElement(prop,W+'keepNext',attrib={W+'val':'1'})
        for row in table.findall('w:tr',NS)[1:]:
            for para in row.findall('.//w:p',NS):
                prop=para.find('w:pPr',NS)
                if prop is None: prop=etree.Element(W+'pPr'); para.insert(0,prop)
                if 'compact' in profile:
                    spacing=etree.SubElement(prop,W+'spacing',attrib={W+'before':'0',W+'after':'40'})
                if 'release' in profile:
                    etree.SubElement(prop,W+'keepNext',attrib={W+'val':'0'})
        target=a.out/(profile+'.docx')
        with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
            for name,data in parts.items(): z.writestr(name,etree.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True) if name=='word/document.xml' else data)
        report['variants'][profile]={'sha256':sha(target),'only_document_xml_modified':True}
    (a.out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(a.out)


if __name__=='__main__': main()
