"""Inspect actual DOCX styles without rewriting documents or displaying answers."""
import hashlib,json,zipfile
from pathlib import Path
from lxml import etree
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parent
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
W='{'+NS['w']+'}'
def values(node):
    return {etree.QName(k).localname:v for k,v in node.attrib.items()} if node is not None else None
def compact(value):return ''.join(value.split())
def main():
    rows=[]
    for folder in sorted((ROOT/'candidate/renders').iterdir()):
        path=folder/'document.docx'
        original=hashlib.sha256(path.read_bytes()).hexdigest()
        soup=BeautifulSoup((folder/'word-entry.html').read_text(),'html.parser')
        expected_empty=len(soup.select('#dmp-content > .dmp-section > .question.compact-empty-question'))
        section_titles={compact(n.get_text()) for n in soup.select('#dmp-content > .dmp-section > h2')}
        question_titles={compact(n.get_text()) for n in soup.select('#dmp-content > .dmp-section > .question > h3')}
        assert len(section_titles)==6 and len(question_titles)==15
        with zipfile.ZipFile(path) as archive:
            body=etree.fromstring(archive.read('word/document.xml'))
            styles=etree.fromstring(archive.read('word/styles.xml'))
        h2=[];h3=[]
        for para in body.findall('.//w:body/w:p',NS):
            style=para.find('w:pPr/w:pStyle',NS)
            if style is None:continue
            name=style.get(W+'val')
            title=compact(''.join(n.text or '' for n in para.findall('.//w:t',NS)))
            if name=='Heading2' and title in section_titles:h2.append(para)
            if name=='Heading3' and title in question_titles:h3.append(para)
        assert len(h2)==6 and len(h3)==15
        assert all(p.find('w:pPr/w:spacing',NS) is None for p in h2)
        compact_headings=[p for p in h3 if values(p.find('w:pPr/w:spacing',NS))=={'before':'80','after':'0'}]
        assert len(compact_headings)==expected_empty
        assert all(values(p.find('w:pPr/w:keepNext',NS))=={'val':'0'} for p in compact_headings)
        heading2=styles.xpath('w:style[@w:styleId="Heading2"]',namespaces=NS)[0]
        spacing=values(heading2.find('w:pPr/w:spacing',NS))
        assert spacing=={'before':'240','after':'120'}
        assert values(heading2.find('w:pPr/w:pageBreakBefore',NS))=={'val':'0'}
        assert hashlib.sha256(path.read_bytes()).hexdigest()==original
        sample=folder.name
        for source,target in [('P19-','REAL-SNAPSHOT-A-'),('P21-','REAL-SNAPSHOT-B-')]:
            if sample.startswith(source):sample=target+sample[len(source):]
        rows.append(dict(sample=sample,section_headings=6,question_headings=15,
            compact_empty_question_headings=expected_empty,heading2_spacing_twips=spacing,
            heading2_direct_spacing_overrides=0,docx_unchanged=True))
    assert len(rows)==28
    report=dict(scope='Read-only actual DOCX spacing diagnostic',passed=True,rows=rows,
        diagnostic_scope_correction='Initial all-body Heading2 count also included frontmatter headings; final diagnostic matches the six actual DMP section titles from HTML.',
        hypothesis='Word empty-section headings still use general Heading2 spacing; test bounded per-section spacing rather than shrinking all text.',
        causality_proven_by_fix_ab=False)
    with (ROOT/'word-style-diagnostic.json').open('x') as f:json.dump(report,f,indent=2)
    print(json.dumps(dict(passed=True,groups=len(rows),production_changed=False)))
if __name__=='__main__':main()
