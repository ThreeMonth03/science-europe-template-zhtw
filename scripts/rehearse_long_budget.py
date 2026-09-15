"""Disposable full-width long-budget diagnosis, never native DSW evidence."""
import argparse
import copy
import json
from pathlib import Path
import zipfile
from lxml import etree
from artifact_utils import sha

W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True); p.add_argument('--out',type=Path,required=True)
    a=p.parse_args(); assert not a.out.exists()
    with zipfile.ZipFile(a.source) as z: parts={n:z.read(n) for n in z.namelist()}
    report={'source_sha256':sha(a.source),'checker_sha256':sha(Path(__file__)),
            'release_acceptance':False,'variants':{}}
    a.out.mkdir(parents=True)
    for profile in ['full-width','full-width-repeat','paragraph-rows-repeat']:
        repeat=profile!='full-width'
        root=etree.fromstring(parts['word/document.xml']); table=root.findall('.//'+W+'body/'+W+'tbl')[-1]
        rows=table.findall(W+'tr'); assert len(rows)==3
        cells=rows[1].findall(W+'tc'); assert len(cells)==3
        contents=[n for n in cells[0] if n.tag!=W+'tcPr']; assert len(contents)>60
        metadata=copy.deepcopy(rows[1]); title=metadata.find(W+'tc')
        for n in list(title):
            if n.tag!=W+'tcPr': title.remove(n)
        title.append(copy.deepcopy(contents[0]))
        if repeat:
            props=metadata.find(W+'trPr')
            if props is None: props=etree.SubElement(metadata,W+'trPr')
            etree.SubElement(props,W+'tblHeader')
        description=etree.Element(W+'tr'); cell=etree.SubElement(description,W+'tc')
        props=etree.SubElement(cell,W+'tcPr')
        width=sum(int(c.get(W+'w')) for c in table.findall(W+'tblGrid/'+W+'gridCol'))
        etree.SubElement(props,W+'tcW',attrib={W+'w':str(width),W+'type':'dxa'})
        etree.SubElement(props,W+'gridSpan',attrib={W+'val':'3'})
        for n in contents[1:]: cell.append(copy.deepcopy(n))
        tail=copy.deepcopy(table)
        for n in tail.findall(W+'tr')[1:]: tail.remove(n)
        tail.append(copy.deepcopy(rows[2]))
        for n in rows[1:]: table.remove(n)
        table.append(metadata)
        if profile=='paragraph-rows-repeat':
            for n in contents[1:]:
                row=etree.Element(W+'tr'); entry=etree.SubElement(row,W+'tc')
                entry.append(copy.deepcopy(props)); entry.append(copy.deepcopy(n)); table.append(row)
        else: table.append(description)
        table.addnext(tail)
        target=a.out/(profile+'.docx')
        with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
            for name,data in parts.items():
                z.writestr(name,etree.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True) if name=='word/document.xml' else data)
        report['variants'][profile]={'sha256':sha(target),'only_document_xml_modified':True}
    (a.out/'report.json').write_text(json.dumps(report,indent=2)+'\n'); print(a.out)


if __name__=='__main__': main()
