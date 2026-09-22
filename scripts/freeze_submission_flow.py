"""Freeze previously accepted, public template bytes; never read project data."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import zipfile
from probe_pdf_budget_translation import pair
from probe_personal_data_translation import archived_pairs

ROOT = Path(__file__).resolve().parents[1]
BASE = 'reviews/2026-09-22-full-km-followups-integration'
PROTO = 'reviews/2026-09-22-empty-question-spacing'
SEALS = {BASE:'f08597cd00530fdb96f8b410fbd4325d80b73c4b1e0783772eef24793bc2bcc4',
         PROTO:'1948496b528eb4ecddad44c17591f79b0f02de0b710e8ba37705fd37e47777e7'}
TRANSLATION_BASE = '6a25bc328a8addc7b7fe644529fe01ebf7538030'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,value):
    p=ROOT/name;p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x') as f:f.write(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    return sha(p)
def sealed(name):
    root=ROOT/name;assert sha(root/'checksums.json')==SEALS[name]
    content=json.loads((root/'checksums.json').read_text())
    rows=content['files'] if 'files' in content else [dict(path=n,sha256=v) for n,v in content.items()]
    assert all(sha(root/r['path'])==r['sha256'] for r in rows)
def run(baseline,prototype):
    sealed(BASE);sealed(PROTO)
    receipts={False:json.loads((ROOT/BASE/'build/manifest.json').read_text()),True:json.loads((ROOT/PROTO/'build-manifest.json').read_text())}
    result=dict(baseline_archive=BASE,prototype_archive=PROTO,seals=SEALS,languages={})
    for language in ['english','chinese']:
        data={}
        for phase,directory in [(False,baseline),(True,prototype)]:
            file=directory/(language+'.zip');assert sha(file)==receipts[phase]['sha256'][file.name]
            with zipfile.ZipFile(file) as z:
                spec=json.loads(z.read('template/template.json'))
                members={n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n!='template/template.json'}
            source={f['fileName']:hashlib.sha256(f['content'].encode()).hexdigest() for f in spec['files']}
            source.update({n.removeprefix('template/assets/'):v for n,v in members.items()})
            label='prototype' if phase else 'baseline';name=f'tests/fixtures/submission-flow/{language}-{label}.json'
            data[label]=dict(fixture=name,fixture_sha256=write(name,spec),sources=source,assets=members,zip_sha256=sha(file))
        before=data['baseline']['sources'];after=data['prototype']['sources']
        assert not set(before)-set(after)
        data['changed']=sorted(n for n in before if before[n]!=after[n]);data['added']=sorted(set(after)-set(before))
        result['languages'][language]=data
    write('docs/submission-flow-prepared-delta.json',result)
    old=Counter(archived_pairs(TRANSLATION_BASE));new=Counter(pair(p.read_text()) for p in (prototype/'translation').rglob('translation.md'))
    assert old.total()==773 and new.total()==775
    reviewed=json.loads((ROOT/'reviews/2026-09-22-reuse-summary-prototype/translation-delta.json').read_text())
    assert old-new==Counter(map(tuple,reviewed['removed'])) and new-old==Counter(map(tuple,reviewed['added']))
    import subprocess
    commit=subprocess.check_output(['git','-C',str(ROOT),'rev-parse',TRANSLATION_BASE],text=True).strip()
    write('docs/submission-flow-translation-delta.json',dict(baseline=commit,baseline_units=773,current_units=775,
        retained_units=(old&new).total(),**reviewed))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--prototype',type=Path,required=True)
    a=p.parse_args();run(a.baseline,a.prototype)
