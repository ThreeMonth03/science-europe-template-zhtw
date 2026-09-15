"""Q8 Word-only change: all 731 translations and non-Lua prepared inputs stay exact."""
import argparse
import json
from pathlib import Path
from artifact_utils import sha

ROOT=Path(__file__).resolve().parents[1]
PRIOR=ROOT/'reviews/2026-09-15-personal-data-followups'


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build',type=Path,required=True);a=p.parse_args()
    old=json.loads((PRIOR/'candidate-manifest.json').read_text());new=json.loads((a.build/'manifest.json').read_text())
    assert old['translation_tree_sha256']==new['translation_tree_sha256']
    assert len(new['translation_tree_sha256'])==731 and new['untranslated_units']==0
    previous=json.loads((PRIOR/'probes/source-scope.json').read_text())
    rows=[]
    for row in previous['rows']:
        folder=a.build/row['language'];before=row['after']
        after={str(f.relative_to(folder)):sha(f) for f in (folder/'src').rglob('*') if f.is_file()}
        assert before.keys()==after.keys()
        changed=[name for name in before if before[name]!=after[name]]
        assert changed==['src/word/pilot.lua'],(row['language'],changed)
        rows.append({'language':row['language'],'changed':changed,'before':before,'after':after})
    report={'passed':True,'release_acceptance':False,'unchanged_translation_files':731,'rows':rows,
            'checker_sha256':sha(Path(__file__)),'prior_manifest_sha256':sha(PRIOR/'candidate-manifest.json'),
            'prior_scope_sha256':sha(PRIOR/'probes/source-scope.json'),
            'package_sha256':{n:sha(a.build/n) for n in ['english.zip','chinese.zip']},
            'limits':['Version metadata intentionally changes; prepared src comparison includes fonts and reference styles',
                      'Input invariance, not native output or Microsoft Word acceptance']}
    target=a.build/'q8-word-scope.json';assert not target.exists();target.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'passed':True,'unchanged_translations':731,'changed_source':'src/word/pilot.lua'}))


if __name__=='__main__':main()
