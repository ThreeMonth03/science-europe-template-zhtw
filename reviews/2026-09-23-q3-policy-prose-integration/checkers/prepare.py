"""Fresh 0.3.51 native replay, retaining the sealed prototype as the baseline."""
import hashlib,json,os,shutil,sys,zipfile
from pathlib import Path
os.umask(0o077)
ROOT=Path(__file__).resolve().parent
PRIOR=Path('/home/trc/.local/share/dsw-q3-prose-final.oDtqal')
ZH=Path('/home/trc/Downloads/science-europe-template-zhtw')
BUILD=Path(Path('/tmp/se-q3-integration-build-01.log').read_text().strip())
SEAL='02d6d54731e58d09e127ea9a31e49e9faa2304c99527531e86c3ca000d779325'
sys.path.insert(0,str(ZH/'scripts'))
from q3_policy_prose_integration import check_package
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
def main():
    assert ROOT.stat().st_mode&0o777==0o700
    assert sha(PRIOR/'evidence-sha256.json')==SEAL
    inventory=json.loads((PRIOR/'evidence-sha256.json').read_text())['files']
    assert len(inventory)==1345 and all(sha(PRIOR/r['path'])==r['sha256'] for r in inventory)
    assert {str(p.relative_to(PRIOR)) for p in PRIOR.rglob('*') if p.is_file()}=={r['path'] for r in inventory}|{'evidence-sha256.json'}
    manifest=json.loads((BUILD/'manifest.json').read_text())
    assert manifest['status']=='candidate' and all(not c['dirty'] for c in manifest['checkouts'].values())
    assert manifest['source']['version']==manifest['translation']['version']=='0.3.51'
    shutil.copytree(PRIOR/'candidate',ROOT/'baseline')
    dest=ROOT/'candidate';dest.mkdir()
    shutil.copytree(PRIOR/'candidate/contexts',dest/'contexts')
    for name in ['offline_worker.py','render_word_previews.py']:shutil.copyfile(PRIOR/'candidate'/name,dest/name)
    packages={}
    for language,locale,folder in [('english','en','en'),('chinese','zh-Hant','translated')]:
        path=BUILD/(language+'.zip');assert sha(path)==manifest['sha256'][path.name]
        check_package(path,BUILD/folder,language,manifest['package_timestamp'])
        packages[path.name]=sha(path)
        with zipfile.ZipFile(path) as z:
            spec=json.loads(z.read('template/template.json'));package=dest/'packages'/locale
            for kind in ['files','assets']:
                for item in spec[kind]:
                    p=package/item['fileName'];assert p.resolve().is_relative_to(package.resolve())
                    p.parent.mkdir(parents=True,exist_ok=True)
                    with p.open('xb') as f:f.write(item['content'].encode() if kind=='files' else z.read('template/assets/'+item['fileName']))
            write(package/'template.json',spec)
        # Identity/version differs; every actual rendering input must match the accepted prototype.
        old=ROOT/'baseline/packages'/locale
        a={str(p.relative_to(old)):sha(p) for p in (old/'src').rglob('*') if p.is_file()}
        b={str(p.relative_to(package)):sha(p) for p in (package/'src').rglob('*') if p.is_file()}
        assert a==b
    contexts={p.stem:sha(p) for p in (dest/'contexts').glob('*.json')}
    assert len(contexts)==10 and contexts==json.loads((PRIOR/'manifest.json').read_text())['contexts']
    write(ROOT/'manifest.json',dict(private=True,prior_seal=SEAL,prior_files=len(inventory),
        build_manifest_sha256=sha(BUILD/'manifest.json'),contexts=contexts,packages=packages,
        checkouts=manifest['checkouts'],credentials_used=False,remote_writes=0))
    print(json.dumps(dict(prepared=True,contexts=10,prototype_files_verified=1345,rendering_inputs_byte_identical=True)))
if __name__=='__main__':main()
