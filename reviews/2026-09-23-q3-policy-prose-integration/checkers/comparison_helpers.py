"""Strict integrated-package equivalence to the accepted native prototype.

All private document content stays local. Only DOCX creation/modification
timestamps and PDF metadata may differ; every visible page is compared.
"""
import hashlib,itertools,json,os,subprocess,zipfile
from pathlib import Path
from bs4 import BeautifulSoup
from lxml import etree
os.umask(0o077)
ROOT=Path(__file__).resolve().parent
PRIOR=Path('/home/trc/.local/share/dsw-q3-prose-final.oDtqal')
DC='http://purl.org/dc/terms/'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def compact(s):return ''.join(s.split())
def core(data):
    tree=etree.fromstring(data)
    for name in ['created','modified']:
        nodes=tree.findall('{'+DC+'}'+name);assert len(nodes)==1
        nodes[0].text=''
    return etree.tostring(tree)
def word_pair(a,b):
    with zipfile.ZipFile(a) as old,zipfile.ZipFile(b) as new:
        assert len(set(old.namelist()))==len(old.namelist())
        assert len(set(new.namelist()))==len(new.namelist())
        assert set(old.namelist())==set(new.namelist()),'DOCX member inventory changed'
        for name in old.namelist():
            x,y=old.read(name),new.read(name)
            if name=='docProps/core.xml':x,y=core(x),core(y)
            assert x==y,('DOCX component changed',name)
def html_pair(a,b,profile):
    assert a==b,'HTML bytes changed'
    soup=BeautifulSoup(b,'html.parser')
    assert len(soup.select('#dmp-content > .dmp-section'))==6
    questions=soup.select('#dmp-content > .dmp-section > .question');assert len(questions)==15
    titles=[compact(n.get_text()) for n in soup.select('#dmp-content > .dmp-section > .question > h3')]
    assert len(titles)==15 and all(titles)
    empty=soup.select('#dmp-content > .dmp-section > .compact-empty-question')
    if profile=='review':assert not empty
    if profile=='submission':
        assert not [n for n in soup.select('.data-gap') if not n.find_parent(class_='answer-detail')]
    return titles,len(empty)
def geometry(data):
    tree=etree.fromstring(data);body=tree.find('.//{*}body');assert body is not None
    pages=body.findall('.//{*}page');assert pages,'No PDF pages'
    texts=[]
    for page in pages:
        width,height=float(page.get('width')),float(page.get('height'))
        assert width>0 and height>0
        words=page.findall('.//{*}word');assert words,'Blank PDF page'
        for word in words:
            assert 0<=float(word.get('xMin'))<=float(word.get('xMax'))<=width+.5,'Off-page PDF text'
            assert 0<=float(word.get('yMin'))<=float(word.get('yMax'))<=height+.5,'Off-page PDF text'
        texts.append(compact(''.join(page.itertext())))
    return etree.tostring(body),texts
def pdf(path):return geometry(subprocess.check_output(['pdftotext','-bbox-layout',str(path),'-']))
def fonts(path):
    rows=subprocess.check_output(['pdffonts',str(path)],text=True).splitlines()[2:]
    assert rows
    return [r.rsplit(None,2)[0] for r in rows]
def raster(path,page):
    return hashlib.sha256(subprocess.check_output(['pdftoppm','-f',str(page),'-l',str(page),'-singlefile','-r','72','-png',str(path)])).hexdigest()
def main():
    manifest=read(ROOT/'manifest.json')
    assert sha(PRIOR/'evidence-sha256.json')==manifest['prior_seal']
    inventory=read(PRIOR/'evidence-sha256.json')['files']
    assert all(sha(PRIOR/r['path'])==r['sha256'] for r in inventory)
    expected=list(itertools.product(sorted(manifest['contexts']),['en','zh-Hant'],['review','submission']))
    render_rows=read(ROOT/'renders.json');preview_rows=read(ROOT/'previews.json')
    assert len(render_rows)==len(preview_rows)==40
    assert {(r['case'],r['language'],r['profile']) for r in render_rows}==set(expected)
    assert {r['sample'] for r in preview_rows}=={f'{c}-{l}-{p}' for c,l,p in expected}
    assert all(r['passed'] for r in render_rows+preview_rows)
    rows=[]
    for case,locale,profile in expected:
        folder=f'{case}-{locale}-{profile}';a,b=[ROOT/arm/'renders'/folder for arm in ['baseline','candidate']]
        assert sha(ROOT/'candidate/contexts'/(case+'.json'))==manifest['contexts'][case]==sha(ROOT/'baseline/contexts'/(case+'.json'))
        titles=None;empty=None
        for name in ['document.html','pdf-entry.html','word-entry.html']:
            observed,n=html_pair((a/name).read_bytes(),(b/name).read_bytes(),profile)
            if titles is None:titles,empty=observed,n
            else:assert (titles,empty)==(observed,n)
        if case=='EMPTY' and profile=='submission':assert empty==15
        word_pair(a/'document.docx',b/'document.docx')
        metrics={}
        for kind,name in [('pdf','document.pdf'),('word_preview','word-preview/document.pdf')]:
            before,bt=pdf(a/name);after,at=pdf(b/name)
            assert before==after,'PDF text geometry changed'
            assert fonts(a/name)==fonts(b/name),'PDF fonts changed'
            assert all(title in ''.join(at) for title in titles),'Question title missing'
            hashes=[]
            for page in range(1,len(at)+1):
                x,y=raster(a/name,page),raster(b/name,page)
                assert x==y,'Rendered page pixels changed'
                hashes.append(y)
            metrics[kind]=dict(before=len(bt),after=len(at),geometry_and_fonts_unchanged=True,page_pixel_sha256=hashes)
        row=dict(case=case,locale=locale,profile=profile,passed=True,empty_headings=empty,pages=metrics,
            html_bytes_unchanged=True,docx_components_unchanged_except_core_timestamps=True)
        rows.append(row);print(json.dumps(dict(case=case,locale=locale,profile=profile,passed=True)),flush=True)
    totals={kind:sum(r['pages'][kind]['after'] for r in rows) for kind in ['pdf','word_preview']}
    assert totals=={'pdf':168,'word_preview':167}
    report=dict(passed=True,scope='Native integration equivalence to accepted prototype',release_acceptance=False,
        native_ms_word=False,native_dsw_server=False,remote_writes=0,credentials_used=False,
        prior_files_unchanged=len(inventory),page_totals=totals,rows=rows)
    with (ROOT/'checks.json').open('x') as f:f.write(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
