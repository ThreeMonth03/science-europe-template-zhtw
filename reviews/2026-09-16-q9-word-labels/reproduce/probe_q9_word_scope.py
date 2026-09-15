"""Compare 0.3.23 prepared source and translations with archived 0.3.22."""
import argparse
import json
from pathlib import Path
from artifact_utils import sha
from probe_q8_word_scope import verify_translations

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build',type=Path,required=True);a=p.parse_args()
    prior=ROOT/'reviews/2026-09-15-q8-word-labels';old=json.loads((prior/'candidate-manifest.json').read_text());new=json.loads((a.build/'manifest.json').read_text())
    verify_translations(old,new);rows=[]
    for row in json.loads((prior/'probes/q8-word-scope.json').read_text())['rows']:
        folder=a.build/row['language'];before=row['after'];after={str(f.relative_to(folder)):sha(f) for f in (folder/'src').rglob('*') if f.is_file()}
        assert before.keys()==after.keys();changed=[n for n in before if before[n]!=after[n]];assert changed==['src/word/pilot.lua']
        rows.append({'language':row['language'],'changed':changed,'before':before,'after':after})
    report={'passed':True,'release_acceptance':False,'unchanged_translation_files':731,'rows':rows,'checker_sha256':sha(Path(__file__)),
            'prior_manifest_sha256':sha(prior/'candidate-manifest.json'),'package_sha256':{n:sha(a.build/n) for n in ['english.zip','chinese.zip']}}
    out=a.build/'q9-word-scope.json';assert not out.exists();out.write_text(json.dumps(report,indent=2)+'\n');print('Q9 scope passed: 731 translations exact; only Word Lua changed.')


if __name__=='__main__':main()
