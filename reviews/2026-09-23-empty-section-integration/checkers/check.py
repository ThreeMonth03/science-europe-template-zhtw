"""Exact native parity between accepted prototype and actual 0.3.48 packages."""
import itertools,json,sys,zipfile
from pathlib import Path
from comparison_helpers import core,word_pair,html_pair,geometry,pdf,fonts,raster,sha,compact
ROOT=Path(__file__).resolve().parent
PRIOR=Path('/home/trc/.local/share/dsw-empty-sections.W74UaS')
ZH=Path('/home/trc/Downloads/science-europe-template-zhtw')
BUILD=Path(Path('/tmp/se-section-integration-build-04.log').read_text().strip())
def read(p):return json.loads(p.read_text())
def main():
    manifest=read(ROOT/'manifest.json');assert sha(PRIOR/'evidence-sha256.json')==manifest['prior_seal']
    inventory=read(PRIOR/'evidence-sha256.json')['files']
    assert all(sha(PRIOR/r['path'])==r['sha256'] for r in inventory)
    assert sha(BUILD/'manifest.json')==manifest['build_manifest_sha256']
    sys.path.insert(0,str(ZH/'scripts'))
    from submission_flow_integration import check_package
    current_manifest=read(BUILD/'manifest.json')
    for locale,language,folder in [('en','english','en'),('zh-Hant','chinese','translated')]:
        path=BUILD/(language+'.zip');assert sha(path)==manifest['packages'][path.name]
        check_package(path,BUILD/folder,language,current_manifest['package_timestamp'])
        extracted=ROOT/'candidate/packages'/locale
        with zipfile.ZipFile(path) as z:
            spec=json.loads(z.read('template/template.json'));assert spec==read(extracted/'template.json')
            expected=set()
            for kind in ['files','assets']:
                for item in spec[kind]:
                    value=item['content'].encode() if kind=='files' else z.read('template/assets/'+item['fileName'])
                    expected.add(item['fileName']);assert (extracted/item['fileName']).read_bytes()==value
            assert {str(p.relative_to(extracted)) for p in (extracted/'src').rglob('*') if p.is_file()}==expected
        previous=ROOT/'baseline/packages'/locale
        values=lambda d:{str(p.relative_to(d)):p.read_bytes() for p in (d/'src').rglob('*') if p.is_file()}
        assert values(previous)==values(extracted),'Integrated prepared source differs from prototype'
    expected=list(itertools.product(sorted(manifest['contexts']),['en','zh-Hant'],['review','submission']))
    renders,previews=read(ROOT/'renders.json'),read(ROOT/'previews.json')
    assert len(renders)==len(previews)==28 and all(r['passed'] for r in renders+previews)
    assert {(r['case'],r['language'],r['profile']) for r in renders}==set(expected)
    assert {r['sample'] for r in previews}=={f'{c}-{l}-{p}' for c,l,p in expected}
    rows=[]
    for case,locale,profile in expected:
        folder=f'{case}-{locale}-{profile}';a,b=[ROOT/arm/'renders'/folder for arm in ['baseline','candidate']]
        assert sha(ROOT/'candidate/contexts'/(case+'.json'))==manifest['contexts'][case]==sha(ROOT/'baseline/contexts'/(case+'.json'))
        titles=None
        for name in ['document.html','pdf-entry.html','word-entry.html']:
            observed,n=html_pair((a/name).read_bytes(),(b/name).read_bytes(),profile)
            if titles is None:titles=observed
            else:assert titles==observed
            if case=='EMPTY' and profile=='submission':assert n==15
        word_pair(a/'document.docx',b/'document.docx');metrics={}
        for kind,name in [('pdf','document.pdf'),('word_preview','word-preview/document.pdf')]:
            old,ot=pdf(a/name);new,nt=pdf(b/name)
            assert old==new and ot==nt,'Native text/geometry changed'
            assert fonts(a/name)==fonts(b/name),'Native font inventory changed'
            assert all(title in ''.join(nt) for title in titles)
            pixels=[]
            for page in range(1,len(nt)+1):
                first,last=raster(a/name,page),raster(b/name,page);assert first==last,'Page pixels changed'
                pixels.append(last)
            metrics[kind]=dict(before=len(ot),after=len(nt),geometry_and_fonts_unchanged=True,page_pixel_sha256=pixels)
        rows.append(dict(case=case,locale=locale,profile=profile,passed=True,pages=metrics,
            html_bytes_unchanged=True,docx_components_unchanged_except_core_timestamps=True))
        print(json.dumps(dict(case=case,locale=locale,profile=profile,passed=True)),flush=True)
    totals={kind:sum(r['pages'][kind]['after'] for r in rows) for kind in ['pdf','word_preview']}
    assert totals==dict(pdf=149,word_preview=151)
    result=dict(passed=True,source_integrated=True,release_acceptance=False,native_ms_word=False,native_dsw_server=False,
        credentials_used=False,remote_writes=0,prior_files_unchanged=len(inventory),page_totals=totals,rows=rows)
    with (ROOT/'checks.json').open('x') as f:json.dump(result,f,indent=2)
if __name__=='__main__':main()
