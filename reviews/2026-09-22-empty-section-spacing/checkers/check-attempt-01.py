"""Reject any text, Word, review geometry or pagination regression."""
import importlib.util,itertools,json,zipfile
from pathlib import Path
from bs4 import BeautifulSoup
from lxml import etree
from comparison_helpers import core,word_pair,html_pair,geometry,pdf,fonts,raster,sha,compact

ROOT=Path(__file__).resolve().parent
PRIOR=Path('/home/trc/.local/share/dsw-flow-integration.jRrEgx')
EN=Path('/home/trc/Downloads/science-europe-template')
BUILD=Path('/home/trc/Downloads/science-europe-template-zhtw/outputs/empty-section-spacing-02')
def load(name):
    spec=importlib.util.spec_from_file_location('native_sections_'+name,EN/'experiments/empty-section-spacing'/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def read(p):return json.loads(p.read_text())
def without_counters(pages):
    result=[]
    for number,text in enumerate(pages,1):
        suffix=f'{number}/{len(pages)}';assert text.endswith(suffix),'Expected generated footer missing'
        result.append(text[:-len(suffix)])
    return result
def location(pages,needle,start=0,end=None):
    text=''.join(pages);end=len(text) if end is None else end
    offset=text.find(needle,start,end)
    assert needle and offset>=0 and text.find(needle,offset+1,end)<0,'Missing or ambiguous expected heading'
    def at(n):
        count=0
        for page,value in enumerate(pages,1):
            count+=len(value)
            if n<count:return page
        raise AssertionError('Text offset outside document')
    return offset,at(offset),at(offset+len(needle)-1)
def boundaries(page,texts):
    rows=[]
    for section in page.select('#dmp-content > .dmp-section'):
        title=compact(section.find('h2',recursive=False).get_text())
        question=compact(section.select_one(':scope > .question > h3').get_text())
        _,_,end=location(texts,title);_,begin,_=location(texts,question)
        rows.append(dict(section=section['id'],heading_kept_with_question=end==begin))
    return rows
def q8_pair(page,texts):
    q8=page.select_one('#q-copyright-ipr');q9=page.select_one('#q-ethical-issues')
    item=q8.select_one('.answer > ul > li');label=item.find('div',recursive=False);intro=label.next_sibling
    assert isinstance(intro,str) and compact(intro)
    start,_,_=location(texts,compact(q8.h3.get_text()));end,_,_=location(texts,compact(q9.h3.get_text()),start)
    position,_,name_end=location(texts,compact(label.get_text()),start,end)
    _,intro_start,_=location(texts,compact(intro),position+len(compact(label.get_text())),end)
    return name_end==intro_start
def main():
    manifest=read(ROOT/'manifest.json');assert sha(PRIOR/'evidence-sha256.json')==manifest['prior_seal']
    inventory=read(PRIOR/'evidence-sha256.json')['files']
    assert all(sha(PRIOR/r['path'])==r['sha256'] for r in inventory)
    expected=list(itertools.product(sorted(manifest['contexts']),['en','zh-Hant'],['review','submission']))
    for name in ['renders.json','previews.json']:
        values=read(ROOT/name);assert len(values)==28 and all(r['passed'] for r in values)
    recipe=load('recipe');probe=load('probe');rows=[];regressions=[]
    assert sha(BUILD/'manifest.json')==manifest['build_manifest_sha256']
    for locale,name in [('en','english.zip'),('zh-Hant','chinese.zip')]:
        assert sha(BUILD/name)==manifest['packages'][name]
        package=ROOT/'candidate/packages'/locale
        with zipfile.ZipFile(BUILD/name) as z:
            metadata=json.loads(z.read('template/template.json'));assert read(package/'template.json')==metadata
            for kind in ['files','assets']:
                for item in metadata[kind]:
                    data=item['content'].encode() if kind=='files' else z.read('template/assets/'+item['fileName'])
                    assert (package/item['fileName']).read_bytes()==data
        values=lambda root:{str(p.relative_to(root)):p.read_bytes() for p in (root/'src').rglob('*') if p.is_file()}
        recipe.project_prepared(values(ROOT/'baseline/packages'/locale),values(package))
    for case,locale,profile in expected:
        folder=f'{case}-{locale}-{profile}';a,b=[ROOT/arm/'renders'/folder for arm in ['baseline','candidate']]
        assert sha(ROOT/'candidate/contexts'/(case+'.json'))==manifest['contexts'][case]==sha(ROOT/'baseline/contexts'/(case+'.json'))
        sections=None;page=None
        for name in ['document.html','pdf-entry.html','word-entry.html']:
            old,new=(a/name).read_bytes(),(b/name).read_bytes()
            assert new.count(recipe.CSS)==1 and not old.count(recipe.CSS)
            html_pair(old,new.replace(recipe.CSS,b'',1),profile)
            parsed=BeautifulSoup(new,'html.parser');found=probe.expected(parsed)
            if sections is None:sections=found
            else:assert sections==found
            if name=='pdf-entry.html':page=parsed
        word_pair(a/'document.docx',b/'document.docx')
        metrics={}
        for kind,name in [('pdf','document.pdf'),('word_preview','word-preview/document.pdf')]:
            old,ot=pdf(a/name);new,nt=pdf(b/name)
            before,after=without_counters(ot),without_counters(nt)
            assert ''.join(before)==''.join(after),'Original PDF text changed'
            assert fonts(a/name)==fonts(b/name),'PDF font inventory changed'
            for title in page.select('#dmp-content > .dmp-section > .question > h3'):
                _,first,last=location(after,compact(title.get_text()));assert first==last,'Question heading split across pages'
            if len(after)>len(before):regressions.append(dict(case=case,locale=locale,profile=profile,format=kind,reason='page-count-increase'))
            old_bounds,new_bounds=boundaries(page,before),boundaries(page,after)
            for x,y in zip(old_bounds,new_bounds):
                if x['heading_kept_with_question'] and not y['heading_kept_with_question']:
                    regressions.append(dict(case=case,locale=locale,profile=profile,format=kind,reason='section-heading-orphan',section=y['section']))
            q8=None
            if case in ['SYN-COMPLETE','SYN-OTHER']:
                old_q8,new_q8=q8_pair(page,before),q8_pair(page,after);q8=dict(before=old_q8,after=new_q8)
                if old_q8 and not new_q8:regressions.append(dict(case=case,locale=locale,profile=profile,format=kind,reason='q8-label-orphan'))
            unchanged=kind=='word_preview' or profile=='review' or not sections
            if unchanged:
                assert old==new,'An untouched format or review changed geometry'
                for number in range(1,len(after)+1):assert raster(a/name,number)==raster(b/name,number),'Untouched page pixels changed'
            metrics[kind]=dict(before=len(before),after=len(after),unchanged_geometry_and_pixels=unchanged,
                section_boundaries_before=old_bounds,section_boundaries_after=new_bounds,q8_boundary=q8)
        rows.append(dict(case=case,locale=locale,profile=profile,passed=True,eligible_sections=sections,pages=metrics,
            html_unchanged_except_exact_css=True,all_text_retained=True,docx_unchanged_except_core_timestamps=True))
        print(json.dumps(dict(case=case,locale=locale,profile=profile,pdf_before=metrics['pdf']['before'],pdf_after=metrics['pdf']['after'])),flush=True)
    empty=next(r for r in rows if (r['case'],r['locale'],r['profile'])==('EMPTY','en','submission'))
    assert (empty['pages']['pdf']['before'],empty['pages']['pdf']['after'])==(3,2)
    totals={kind:{phase:sum(r['pages'][kind][phase] for r in rows) for phase in ['before','after']} for kind in ['pdf','word_preview']}
    result=dict(passed=not regressions,prototype_only=True,source_integrated=False,release_acceptance=False,
        native_ms_word=False,native_dsw_server=False,remote_writes=0,credentials_used=False,
        prior_files_unchanged=len(inventory),page_totals=totals,regressions=regressions,rows=rows)
    with (ROOT/'checks.json').open('x') as f:json.dump(result,f,indent=2)
    assert not regressions,'See recorded pagination regressions; do not promote'
if __name__=='__main__':main()
