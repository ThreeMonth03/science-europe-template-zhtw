"""Re-run exact sealed prototype contexts against the integrated 0.3.49 packages."""
import hashlib,json,os,shutil,zipfile
from pathlib import Path
os.umask(0o077)
ROOT=Path(__file__).resolve().parent
PRIOR=Path('/home/trc/.local/share/dsw-preparation-prose.1ysXWG')
BUILD=Path(Path('/tmp/se-preparation-integration-build-01.log').read_text().strip())
SEAL='246ade8a6b1e949a4eddb7d5e00dda8fadadc246a106b8352ef52bc27cbe29dd'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x') as f:json.dump(v,f,indent=2);f.write('\n')
def main():
    assert ROOT.stat().st_mode&0o777==0o700
    assert sha(PRIOR/'evidence-sha256.json')==SEAL
    inventory=json.loads((PRIOR/'evidence-sha256.json').read_text())['files']
    assert all(sha(PRIOR/r['path'])==r['sha256'] for r in inventory)
    manifest=json.loads((BUILD/'manifest.json').read_text())
    assert manifest['status']=='candidate' and not manifest['untranslated_units']
    assert manifest['source']['version']==manifest['translation']['version']=='0.3.49'
    assert all(not r['dirty'] for r in manifest['checkouts'].values())
    for arm in ['baseline','candidate']:
        dest=ROOT/arm;dest.mkdir()
        shutil.copytree(PRIOR/'candidate/contexts',dest/'contexts')
        if arm=='baseline':
            shutil.copytree(PRIOR/'candidate/packages',dest/'packages')
            shutil.copytree(PRIOR/'candidate/renders',dest/'renders')
        else:
            for name in ['offline_worker.py','render_word_previews.py']:
                shutil.copyfile(ROOT/name,dest/name)
            for language,name in [('en','english.zip'),('zh-Hant','chinese.zip')]:
                assert sha(BUILD/name)==manifest['sha256'][name]
                with zipfile.ZipFile(BUILD/name) as z:
                    spec=json.loads(z.read('template/template.json'));package=dest/'packages'/language
                    for kind in ['files','assets']:
                        for item in spec[kind]:
                            p=package/item['fileName'];assert p.resolve().is_relative_to(package.resolve())
                            p.parent.mkdir(parents=True,exist_ok=True)
                            with p.open('xb') as f:f.write(item['content'].encode() if kind=='files' else z.read('template/assets/'+item['fileName']))
                    write(package/'template.json',spec)
    contexts={p.stem:sha(p) for p in (ROOT/'candidate/contexts').glob('*.json')}
    assert len(contexts)==7
    write(ROOT/'manifest.json',dict(private=True,prior_seal=SEAL,prior_files=len(inventory),
        build_manifest_sha256=sha(BUILD/'manifest.json'),contexts=contexts,
        packages={n:manifest['sha256'][n] for n in ['english.zip','chinese.zip']},
        checkouts=manifest['checkouts'],credentials_used=False,remote_writes=0))
    print(json.dumps(dict(prepared=True,contexts=len(contexts),prior_files_verified=len(inventory))))
if __name__=='__main__':main()
