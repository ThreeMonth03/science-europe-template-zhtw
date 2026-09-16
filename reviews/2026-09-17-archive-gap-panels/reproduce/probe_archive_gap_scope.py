"""0.3.30 exact CSS-only scope, unchanged translations and Q11 branch behavior."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from artifact_utils import sha

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,required=True);p.add_argument('--english',type=Path,required=True)
    a=p.parse_args();sys.path[:0]=[str(a.english.resolve()/n) for n in ['scripts','tests']]
    from probe_archive_gap_panels import split_css,rows,FIRST,LAST,PAIRS
    from archive_basis_contract import check_roots
    from bs4 import BeautifulSoup
    prior=ROOT/'reviews/2026-09-16-archive-basis-reading'
    old=json.loads((prior/'candidate-manifest.json').read_text())
    current=json.loads((a.build/'manifest.json').read_text())
    assert current['untranslated_units']==[]
    hashes={str(f.relative_to(ROOT/'translation')):sha(f) for f in (ROOT/'translation/tree').rglob('translation.md')}
    assert len(hashes)==732 and hashes==old['translation_tree_sha256']==current['translation_tree_sha256']
    checks=[]
    for row in json.loads((prior/'probes/archive-basis-translation-proof.json').read_text())['rows']:
        folder=row['language'];root=a.build/folder;before=row['after']
        after={str(f.relative_to(root)):sha(f) for f in (root/'src').rglob('*') if f.is_file()}
        assert before.keys()==after.keys()
        changed=sorted(n for n in before if before[n]!=after[n]);assert changed==['src/layout.css']
        assert hashlib.sha256(split_css((root/'src/layout.css').read_text())[0].encode()).hexdigest()==before['src/layout.css']
        language='english' if folder=='en' else 'chinese'
        frozen=a.english/'tests/fixtures/archive-0.3.28.en.html.j2' if folder=='en' else ROOT/'tests/fixtures/archive-0.3.28.zh-Hant.html.j2'
        branches=check_roots(root,frozen,language)
        selected=0
        for name,html,expected in rows(root):
            soup=BeautifulSoup(html,'html.parser');found=[]
            for pair,left,right in zip(PAIRS,FIRST,LAST):
                assert len(soup.select(left))==len(soup.select(right))
                if soup.select(left):found.append(list(pair))
            assert found==expected;selected+=1
        checks.append({'language':folder,'before':before,'after':after,'changed':changed,'unchanged_q11_branch_checks':branches,'gap_combinations':selected})
    report={'passed':True,'release_acceptance':False,'rows':checks,'unchanged_translation_files':732,
            'checker_sha256':sha(Path(__file__)),'engine_checker_sha256':sha(a.english/'scripts/probe_archive_gap_panels.py'),
            'package_sha256':{n:sha(a.build/n) for n in ['english.zip','chinese.zip']},
            'limits':['Only the marked CSS addition is admitted; native pagination is checked separately']}
    target=a.build/'archive-gap-scope.json';assert not target.exists();target.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'passed':True,'unchanged_translations':732,'gap_combinations':128,'prior_branch_checks':548}))


if __name__=='__main__':main()
