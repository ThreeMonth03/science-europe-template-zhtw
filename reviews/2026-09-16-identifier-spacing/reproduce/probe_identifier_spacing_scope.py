"""0.3.28 scope: CSS/Lua separators only; all Jinja and translations identical."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from artifact_utils import sha

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,required=True)
    p.add_argument('--english',type=Path,required=True)
    a=p.parse_args()
    sys.path.insert(0,str(a.english.resolve()/'scripts'))
    from probe_identifier_spacing import baseline,old_lua,CSS_BEGIN,CSS_END
    prior=ROOT/'reviews/2026-09-16-identifier-concise'
    old=json.loads((prior/'candidate-manifest.json').read_text())
    current=json.loads((a.build/'manifest.json').read_text())
    assert current['untranslated_units']==[]
    hashes={str(f.relative_to(ROOT/'translation')):sha(f) for f in (ROOT/'translation/tree').rglob('translation.md')}
    assert hashes==old['translation_tree_sha256']==current['translation_tree_sha256']
    assert len(hashes)==731
    rows=[]
    for row in json.loads((prior/'probes/identifier-concise-scope.json').read_text())['rows']:
        root=a.build/row['language'];before=row['after']
        after={str(f.relative_to(root)):sha(f) for f in (root/'src').rglob('*') if f.is_file()}
        assert before.keys()==after.keys()
        changed=sorted(n for n in before if before[n]!=after[n])
        assert changed==['src/layout.css','src/word/pilot.lua'],changed
        for name,original in [('src/layout.css',baseline((root/'src/layout.css').read_text(),CSS_BEGIN,CSS_END)),
                              ('src/word/pilot.lua',old_lua((root/'src/word/pilot.lua').read_text()))]:
            assert hashlib.sha256(original.encode()).hexdigest()==before[name]
        rows.append({'language':row['language'],'before':before,'after':after,'changed':changed})
    report={'passed':True,'release_acceptance':False,'rows':rows,'unchanged_translation_files':731,
            'checker_sha256':sha(Path(__file__)),'package_sha256':{n:sha(a.build/n) for n in ['english.zip','chinese.zip']},
            'limits':['No wording or answer logic changes','Native render and Microsoft Word acceptance are separate']}
    target=a.build/'identifier-spacing-scope.json';assert not target.exists()
    target.write_text(json.dumps(report,indent=2)+'\n')
    print('Only scoped CSS/Lua changes; all Jinja, fonts, Word reference and 731 translations exact.')


if __name__=='__main__':main()
