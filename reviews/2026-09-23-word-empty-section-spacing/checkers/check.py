"""Native Word-spacing A/B: exact content, bounded XML changes, no PDF changes."""
import hashlib,itertools,json,subprocess,zipfile
from pathlib import Path
from bs4 import BeautifulSoup
from lxml import etree
from comparison_helpers import sha,read,compact,core,pdf,fonts,raster,html_pair

ROOT=Path(__file__).resolve().parent
PRIOR=Path('/home/trc/.local/share/dsw-preparation-integration.ZTpuU9')
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
NS={'w':W};WA='{'+W+'}'

def normalize_xml(before,after,allowed,links=()):
    x,y=[etree.fromstring(v) for v in [before,after]]
    paragraphs=[v.findall('.//w:body/w:p',NS) for v in [x,y]]
    assert len(paragraphs[0])==len(paragraphs[1])
    expected={compact(v) for v in allowed};assert len(expected)==len(allowed)
    def title(p):return compact(''.join(t.text or '' for t in p.findall('.//w:t',NS)))
    expected_links={compact(v) for v in links};assert len(expected_links)==len(links)
    observed=set();linked=set()
    for old,new in zip(*paragraphs):
        old_style=old.find('w:pPr/w:pStyle',NS);new_style=new.find('w:pPr/w:pStyle',NS)
        if new_style is None:continue
        if new_style.get(WA+'val')=='Heading3' and title(new) in expected_links:
            label=title(new);assert label not in linked and title(old)==label
            assert sum(title(p)==label for p in paragraphs[0])==sum(title(p)==label for p in paragraphs[1])==1
            keep=new.find('w:pPr/w:keepNext',NS);old_keep=old.find('w:pPr/w:keepNext',NS)
            assert keep is not None and old_keep is not None and keep.attrib=={WA+'val':'1'} and old_keep.attrib=={WA+'val':'0'}
            keep.set(WA+'val','0');linked.add(label)
        if new_style.get(WA+'val')!='Heading2':continue
        props=new.find('w:pPr',NS);spacing=props.find('w:spacing',NS)
        if spacing is None:continue
        label=title(new)
        assert label in expected and label not in observed,'Unapproved or duplicate heading spacing'
        assert title(old)==label and old_style is not None and old_style.get(WA+'val')=='Heading2'
        assert sum(title(p)==label for p in paragraphs[0])==sum(title(p)==label for p in paragraphs[1])==1
        assert old.find('w:pPr/w:spacing',NS) is None
        assert spacing.attrib=={WA+'before':'60',WA+'after':'40'} and len(spacing)==0
        props.remove(spacing);observed.add(label)
    assert observed==expected,'Expected section spacing not applied'
    assert linked==expected_links,'Expected empty-question keep chain not applied'
    assert etree.tostring(x)==etree.tostring(y),'Unexpected Word text, paragraph, bookmark or formatting change'
    return len(observed)

def word_pair(before,after,allowed,links=()):
    with zipfile.ZipFile(before) as a,zipfile.ZipFile(after) as b:
        assert len(set(a.namelist()))==len(a.namelist()) and len(set(b.namelist()))==len(b.namelist())
        assert set(a.namelist())==set(b.namelist())
        for name in a.namelist():
            x,y=a.read(name),b.read(name)
            if name=='word/document.xml':normalize_xml(x,y,allowed,links)
            else:
                if name=='docProps/core.xml':x,y=core(x),core(y)
                assert x==y,('Unrelated DOCX component changed',name)

def word_pages(path):
    tree=etree.fromstring(subprocess.check_output(['pdftotext','-bbox-layout',str(path),'-']))
    pages=tree.findall('.//{*}page');result=[]
    for index,page in enumerate(pages,1):
        words=page.findall('.//{*}word')
        tail=words[-3:]
        if [w.text for w in tail]==[str(index),'/',str(len(pages))] and all(float(w.get('yMin'))>float(page.get('height'))-60 for w in tail):
            words=words[:-3]
        result.append(compact(''.join(''.join(w.itertext()) for w in words)))
    return result

def word_text(path):return ''.join(word_pages(path))

def expected_sections(html):
    soup=BeautifulSoup(html,'html.parser');sections=soup.select('#dmp-content > .dmp-section')
    assert len(sections)==6
    allowed=[]
    for section in sections:
        questions=section.find_all('div',class_='question',recursive=False)
        assert questions
        if all('compact-empty-question' in q.get('class',[]) for q in questions):
            allowed.append(section.find('h2',recursive=False).get_text())
    return allowed

def expected_links(html):
    soup=BeautifulSoup(html,'html.parser');result=[]
    for section in soup.select('#dmp-content > .dmp-section'):
        questions=section.find_all('div',class_='question',recursive=False)
        if questions and all('compact-empty-question' in q.get('class',[]) for q in questions):
            result.extend(q.find('h3',recursive=False).get_text() for q in questions[:-1])
    return result

def main():
    manifest=read(ROOT/'manifest.json')
    assert sha(PRIOR/'evidence-sha256.json')==manifest['prior_seal']
    inventory=read(PRIOR/'evidence-sha256.json')['files']
    assert len(inventory)==1037 and all(sha(PRIOR/r['path'])==r['sha256'] for r in inventory)
    expected=list(itertools.product(sorted(manifest['contexts']),['en','zh-Hant'],['review','submission']))
    renders=read(ROOT/'renders.json');previews=read(ROOT/'previews.json')
    assert len(renders)==len(previews)==len(expected)==28 and all(r['passed'] for r in renders+previews)
    assert {(r['case'],r['language'],r['profile']) for r in renders}==set(expected)
    assert {r['sample'] for r in previews}=={f'{c}-{l}-{p}' for c,l,p in expected}
    rows=[]
    for case,language,profile in expected:
        name=f'{case}-{language}-{profile}';old,new=[ROOT/arm/'renders'/name for arm in ['baseline','candidate']]
        assert sha(ROOT/'baseline/contexts'/(case+'.json'))==sha(ROOT/'candidate/contexts'/(case+'.json'))==manifest['contexts'][case]
        titles=None;empty=None
        for file in ['document.html','pdf-entry.html','word-entry.html']:
            ts,n=html_pair((old/file).read_bytes(),(new/file).read_bytes(),profile)
            if titles is None:titles,empty=ts,n
            else:assert (titles,empty)==(ts,n)
        allowed=expected_sections((new/'word-entry.html').read_text())
        links=expected_links((new/'word-entry.html').read_text())
        if profile=='review':assert not allowed
        word_pair(old/'document.docx',new/'document.docx',allowed,links)
        metrics={}
        for kind,path in [('pdf','document.pdf'),('word_preview','word-preview/document.pdf')]:
            before,bt=pdf(old/path);after,at=pdf(new/path)
            assert all(t in ''.join(at) for t in titles),'Question heading missing'
            assert fonts(old/path)==fonts(new/path),'Font change'
            assert len(at)<=len(bt),'Page count increased'
            unchanged=kind=='pdf' or not allowed
            if unchanged:assert before==after,'Unchanged output geometry drift'
            else:assert word_text(old/path)==word_text(new/path),'Word preview text changed beyond page-number footer'
            pixels=[]
            for page in range(1,len(at)+1):
                digest=raster(new/path,page)
                if unchanged:assert digest==raster(old/path,page),'Unchanged output pixels drift'
                pixels.append(digest)
            metrics[kind]=dict(before=len(bt),after=len(at),geometry_unchanged=before==after,
                pixel_equality_required=unchanged,page_pixel_sha256=pixels)
        if case in ['MISSING','NEGATIVE'] and language=='zh-Hant' and profile=='submission':
            assert metrics['word_preview']['before']==3 and metrics['word_preview']['after']==2,'Target orphan page remains'
        if case=='EMPTY' and profile=='submission':assert empty==15 and metrics['word_preview']['after']==2
        if case=='MISSING' and language=='en' and profile=='submission':assert metrics['word_preview']['after']==2
        if profile=='submission':assert word_pages(new/'word-preview/document.pdf')[-1]!=titles[-1],'Q15 remains alone on the last page'
        # The complete affected section must stay together, including its last question.
        if allowed:
            _,texts=pdf(new/'word-preview/document.pdf');soup=BeautifulSoup((new/'word-entry.html').read_text(),'html.parser')
            for section in soup.select('#dmp-content > .dmp-section'):
                heading=compact(section.find('h2',recursive=False).get_text())
                if heading not in {compact(v) for v in allowed}:continue
                questions=[compact(q.get_text()) for q in section.select('.question > h3')]
                assert any(heading in text and all(q in text for q in questions) for text in texts),'Empty section split across pages'
        rows.append(dict(case=case,language=language,profile=profile,passed=True,empty_question_headings=empty,
            word_section_headings_changed=len(allowed),word_empty_question_links_changed=len(links),html_bytes_unchanged=True,
            docx_only_allowed_heading_spacing_keep_chains_and_core_timestamps=True,pages=metrics))
        print(json.dumps(dict(case=case,language=language,profile=profile,passed=True,word_pages=metrics['word_preview']['after'])),flush=True)
    totals={kind:{arm:sum(r['pages'][kind][arm] for r in rows) for arm in ['before','after']} for kind in ['pdf','word_preview']}
    assert totals['pdf']=={'before':130,'after':130} and totals['word_preview']['before']==133
    report=dict(passed=True,prototype_only=True,source_integrated=False,release_acceptance=False,native_ms_word=False,
        remote_writes=0,credentials_used=False,prior_files_unchanged=len(inventory),page_totals=totals,rows=rows)
    with (ROOT/'checks.json').open('x') as f:json.dump(report,f,indent=2)
if __name__=='__main__':main()
