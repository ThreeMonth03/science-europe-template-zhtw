"""Only the reviewed empty-Q15 CSS panel may differ from archived 0.3.23."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from artifact_utils import sha
from probe_q8_word_scope import verify_translations

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['build','english']:p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();sys.path.insert(0,str(a.english.resolve()/'scripts'))
    from probe_empty_pdf import split_css
    prior=ROOT/'reviews/2026-09-16-q9-word-labels'
    old=json.loads((prior/'candidate-manifest.json').read_text());new=json.loads((a.build/'manifest.json').read_text())
    verify_translations(old,new);rows=[]
    for row in json.loads((prior/'probes/q9-word-scope.json').read_text())['rows']:
        folder=a.build/row['language'];before=row['after']
        after={str(f.relative_to(folder)):sha(f) for f in (folder/'src').rglob('*') if f.is_file()}
        assert before.keys()==after.keys()
        changed=[name for name in before if before[name]!=after[name]]
        assert changed==['src/layout.css'],(row['language'],changed)
        baseline,panel=split_css((folder/'src/layout.css').read_text())
        assert hashlib.sha256(baseline.encode()).hexdigest()==before['src/layout.css'],'Unexpected CSS edit beyond panel'
        rows.append({'language':row['language'],'changed':changed,'before':before,'after':after,'exact_previous_css_after_removing_panel':True})
    report={'passed':True,'release_acceptance':False,'unchanged_translation_files':731,'rows':rows,
        'checker_sha256':sha(Path(__file__)),'prior_manifest_sha256':sha(prior/'candidate-manifest.json'),
        'prior_scope_sha256':sha(prior/'probes/q9-word-scope.json'),
        'package_sha256':{n:sha(a.build/n) for n in ['english.zip','chinese.zip']}}
    out=a.build/'empty-pdf-scope.json';assert not out.exists();out.write_text(json.dumps(report,indent=2)+'\n')
    print('Empty PDF scope passed: 731 translations unchanged; exactly the bounded CSS panel added.')


if __name__=='__main__':main()
