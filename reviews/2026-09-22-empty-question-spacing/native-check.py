"""Verify only exact empty-question spacing changed; never expose private text."""
import copy,hashlib,itertools,json,os,subprocess,sys,zipfile
from pathlib import Path
from bs4 import BeautifulSoup
from lxml import etree
os.umask(0o077)
ROOT=Path(__file__).resolve().parent
PRIOR=Path('/home/trc/.local/share/dsw-reuse-summary.umdnFp')
sys.path.insert(0,'/home/trc/Downloads/science-europe-template/experiments/empty-question-spacing')
import probe
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'; NS={'w':W}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def compact(s):return ''.join(s.split())

def heading(xml,qid):
    marks=xml.xpath('//w:bookmarkStart[@w:name=$name]',namespaces=NS,name=qid)
    assert len(marks)==1
    own=marks[0].xpath('ancestor::w:p[1]',namespaces=NS)
    style=own[0].find('w:pPr/w:pStyle',NS) if own else None
    if style is not None and style.get('{'+W+'}val')=='Heading3':return own[0]
    candidates=marks[0].xpath('following::w:p[w:pPr/w:pStyle[@w:val="Heading3"]][1]',namespaces=NS)
    assert len(candidates)==1,'Missing question heading'
    p=candidates[0]
    previous=p.xpath('preceding::w:bookmarkStart[starts-with(@w:name,"q-")][1]/@w:name',namespaces=NS)
    assert previous==[qid],'Question boundary crossed'
    return p

def word_pair(a,b,ids):
    with zipfile.ZipFile(a) as old,zipfile.ZipFile(b) as new:
        assert set(old.namelist())==set(new.namelist())
        for name in old.namelist():
            if name not in ['word/document.xml','docProps/core.xml']:assert old.read(name)==new.read(name),('Other DOCX component changed',name)
        x,y=[etree.fromstring(z.read('word/document.xml')) for z in [old,new]]
        for qid in ids:
            p=heading(y,qid);props=p.find('w:pPr',NS)
            keep=props.find('w:keepNext',NS);space=props.find('w:spacing',NS)
            assert keep is not None and keep.attrib=={'{'+W+'}val':'0'}
            assert space is not None and space.attrib=={'{'+W+'}before':'80','{'+W+'}after':'0'}
            assert heading(x,qid).find('w:pPr/w:keepNext',NS) is None
            assert heading(x,qid).find('w:pPr/w:spacing',NS) is None
            props.remove(keep);props.remove(space)
        assert etree.tostring(x)==etree.tostring(y),'DOCX changed beyond the specified empty headings'
        x,y=[etree.fromstring(z.read('docProps/core.xml')) for z in [old,new]]
        for tree in [x,y]:
            for node in tree:
                if etree.QName(node).localname in ['created','modified']:node.text=''
        assert etree.tostring(x)==etree.tostring(y)

def pdf(path):
    tree=etree.fromstring(subprocess.check_output(['pdftotext','-bbox-layout',str(path),'-']))
    pages=tree.findall('.//{*}page');assert pages,'No PDF pages'
    texts=[]
    for page in pages:
        words=page.findall('.//{*}word');assert words,'Blank PDF page'
        for word in words:
            assert 0<=float(word.get('xMin'))<=float(word.get('xMax'))<=float(page.get('width'))+.5
            assert 0<=float(word.get('yMin'))<=float(word.get('yMax'))<=float(page.get('height'))+.5
        texts.append(compact(''.join(page.itertext())))
    return tree,pages,texts

def main():
    manifest=read(ROOT/'manifest.json')
    assert sha(PRIOR/'evidence-sha256.json')==manifest['prior_seal']
    inventory=read(PRIOR/'evidence-sha256.json')['files']
    assert all(sha(PRIOR/r['path'])==r['sha256'] for r in inventory)
    for file in ['renders.json','previews.json']:
        rows=read(ROOT/file);assert len(rows)==28 and all(r['passed'] for r in rows)
    rows=[]
    for case,locale,profile in itertools.product(sorted(manifest['contexts']),['en','zh-Hant'],['review','submission']):
        folder=f'{case}-{locale}-{profile}';a,b=[ROOT/arm/'renders'/folder for arm in ['baseline','candidate']]
        assert sha(ROOT/'candidate/contexts'/(case+'.json'))==manifest['contexts'][case]==sha(ROOT/'baseline/contexts'/(case+'.json'))
        ids=None;titles=None
        for name in ['document.html','pdf-entry.html','word-entry.html']:
            old,new=[BeautifulSoup((p/name).read_text(),'html.parser') for p in [a,b]]
            assert probe.dom(probe.expected(old.body,profile))==probe.dom(new.body),'HTML text/structure changed'
            actual=[n['id'] for n in new.select('#dmp-content > .dmp-section > .compact-empty-question')]
            if ids is None:ids=actual
            else:assert ids==actual,'Formats disagree on empty answers'
            assert len(new.select('#dmp-content > .dmp-section'))==6 and len(new.select('#dmp-content > .dmp-section > .question'))==15
            titles=[compact(n.get_text()) for n in new.select('#dmp-content > .dmp-section > .question > h3')]
            if profile=='submission':assert not [n for n in new.select('.data-gap') if not n.find_parent(class_='answer-detail')]
        if case=='EMPTY' and profile=='submission':assert len(ids)==15
        if profile=='review':assert not ids
        word_pair(a/'document.docx',b/'document.docx',ids)
        metrics={}
        for kind,name in [('pdf','document.pdf'),('word_preview','word-preview/document.pdf')]:
            before,bp,bt=pdf(a/name);after,ap,at=pdf(b/name)
            all_text=''.join(at)
            for title in titles:assert title in all_text,'A required question heading disappeared'
            if profile=='review':
                assert etree.tostring(before.find('.//{*}body'))==etree.tostring(after.find('.//{*}body')),'Review geometry changed'
                fonts=lambda p:[r.rsplit(None,2)[0] for r in subprocess.check_output(['pdffonts',str(p)],text=True).splitlines()[2:]]
                assert fonts(a/name)==fonts(b/name)
                for number in range(1,len(ap)+1):
                    raster=lambda p:subprocess.check_output(['pdftoppm','-f',str(number),'-l',str(number),'-singlefile','-r','72','-png',str(p)])
                    assert raster(a/name)==raster(b/name),'Review page pixels changed'
            metrics[kind]=dict(before=len(bp),after=len(ap))
        row=dict(case=case,locale=locale,profile=profile,passed=True,empty_headings=len(ids),pages=metrics,
            original_question_text_and_answers_unchanged=True,word_only_designated_paragraph_properties=True,review_geometry_pixels_unchanged=profile=='review')
        rows.append(row);print(json.dumps(row),flush=True)
    result=dict(passed=True,prototype_only=True,release_acceptance=False,rows=rows,prior_files_unchanged=len(inventory),
        native_ms_word=False,native_dsw_server=False,remote_writes=0,credentials_used=False)
    with (ROOT/'checks.json').open('x') as f:f.write(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
