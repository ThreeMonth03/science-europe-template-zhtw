"""Prepare private native A/B without changing the sealed 0.3.49 evidence."""
import hashlib,json,os,shutil,zipfile
from pathlib import Path
os.umask(0o077)
ROOT=Path(__file__).resolve().parent
PRIOR=Path('/home/trc/.local/share/dsw-preparation-integration.ZTpuU9')
BUILD=Path('/home/trc/Downloads/science-europe-template-zhtw/outputs/word-empty-section-prototype-03')
SEAL='8090eac1b427580ab545bbc99d09fb0279fae876b74275310f60964f6681058a'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):
    with path.open('x') as f:json.dump(value,f,indent=2);f.write('\n')
def main():
    assert ROOT.stat().st_mode&0o777==0o700
    assert sha(PRIOR/'evidence-sha256.json')==SEAL
    prior=json.loads((PRIOR/'evidence-sha256.json').read_text())['files']
    assert len(prior)==1037 and all(sha(PRIOR/r['path'])==r['sha256'] for r in prior)
    assert {str(p.relative_to(PRIOR)) for p in PRIOR.rglob('*') if p.is_file()}=={r['path'] for r in prior}|{'evidence-sha256.json'}
    manifest=json.loads((BUILD/'manifest.json').read_text())
    assert manifest['status']=='prototype' and manifest['translation_units']==775 and manifest['translation_pairs_and_file_bytes_unchanged']
    assert all(not r['dirty'] for r in manifest['checkouts'].values())
    for name in ['offline_worker.py','render_word_previews.py','run.py','comparison_helpers.py']:
        assert not (ROOT/name).exists();shutil.copyfile(PRIOR/name,ROOT/name)
    for arm in ['baseline','candidate']:
        target=ROOT/arm;target.mkdir()
        shutil.copytree(PRIOR/'candidate/contexts',target/'contexts')
        if arm=='baseline':
            shutil.copytree(PRIOR/'candidate/packages',target/'packages')
            shutil.copytree(PRIOR/'candidate/renders',target/'renders')
        else:
            for name in ['offline_worker.py','render_word_previews.py']:shutil.copyfile(ROOT/name,target/name)
            for language,name in [('en','english.zip'),('zh-Hant','chinese.zip')]:
                assert sha(BUILD/name)==manifest['sha256'][name]
                with zipfile.ZipFile(BUILD/name) as z:
                    spec=json.loads(z.read('template/template.json'));package=target/'packages'/language
                    for kind in ['files','assets']:
                        for item in spec[kind]:
                            path=package/item['fileName'];assert path.resolve().is_relative_to(package.resolve())
                            path.parent.mkdir(parents=True,exist_ok=True)
                            with path.open('xb') as f:f.write(item['content'].encode() if kind=='files' else z.read('template/assets/'+item['fileName']))
                    write(package/'template.json',spec)
    contexts={p.stem:sha(p) for p in (ROOT/'candidate/contexts').glob('*.json')}
    assert len(contexts)==7
    write(ROOT/'manifest.json',dict(private=True,prior_seal=SEAL,prior_files=len(prior),
        prototype_manifest_sha256=sha(BUILD/'manifest.json'),contexts=contexts,packages=manifest['sha256'],
        checkouts=manifest['checkouts'],credentials_used=False,remote_writes=0))
    print(json.dumps(dict(prepared=True,contexts=len(contexts),prior_files_unchanged=len(prior))))
if __name__=='__main__':main()

