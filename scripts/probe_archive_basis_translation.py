"""0.3.29: exact bilingual Q11 list-to-sentence scope and translation delta."""
import argparse
import json
import sys
from pathlib import Path
from artifact_utils import sha
from probe_pdf_budget_translation import pair
from probe_personal_data_translation import verify_translation_chain

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,required=True)
    p.add_argument('--english',type=Path,required=True)
    a=p.parse_args();sys.path[:0]=[str(a.english.resolve()/n) for n in ['scripts','tests']]
    from archive_basis_contract import check_roots
    old_root=ROOT/'reviews/2026-09-16-identifier-spacing'
    manifest=json.loads((a.build/'manifest.json').read_text())
    assert manifest['untranslated_units']==[]
    files=sorted((ROOT/'translation/tree').rglob('translation.md'))
    _,delta=verify_translation_chain([pair(f.read_text()) for f in files])
    hashes={str(f.relative_to(ROOT/'translation')):sha(f) for f in files}
    assert hashes==manifest['translation_tree_sha256']
    old_hashes=json.loads((old_root/'candidate-manifest.json').read_text())['translation_tree_sha256']
    outside=lambda values:{k:v for k,v in values.items() if not k.startswith('tree/src/post-project-archive.html.j2/')}
    assert outside(hashes)==outside(old_hashes),'Unrelated translation file or metadata changed'
    rows=[]
    for old in json.loads((old_root/'probes/identifier-spacing-scope.json').read_text())['rows']:
        folder=old['language'];root=a.build/folder
        language='english' if folder=='en' else 'chinese'
        frozen=(a.english/'tests/fixtures/archive-0.3.28.en.html.j2' if folder=='en' else ROOT/'tests/fixtures/archive-0.3.28.zh-Hant.html.j2')
        assert sha(frozen)==old['after']['src/post-project-archive.html.j2']
        before=old['after'];after={str(f.relative_to(root)):sha(f) for f in (root/'src').rglob('*') if f.is_file()}
        assert before.keys()==after.keys()
        changed=sorted(n for n in before if before[n]!=after[n])
        assert changed==['src/post-project-archive.html.j2'],changed
        count=check_roots(root,frozen,language)
        rows.append({'language':folder,'before':before,'after':after,'changed':changed,'branch_checks':count})
    report={'passed':True,'release_acceptance':False,'rows':rows,'translation_delta':delta,
            'checker_sha256':sha(Path(__file__)),'contract_sha256':sha(a.english/'scripts/archive_basis_contract.py'),
            'delta_sha256':sha(ROOT/'docs/archive-basis-translation-delta.json'),
            'translation_tree_sha256':hashes,
            'package_sha256':{n:sha(a.build/n) for n in ['english.zip','chinese.zip']},
            'limits':['Adapter-based branch and source-scope checks; native layout is separate',
                      'Unsupported/stale answers are adapter-only, not valid native KM fixtures']}
    target=a.build/'archive-basis-translation-proof.json';assert not target.exists()
    target.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'passed':True,'branch_checks':sum(r['branch_checks'] for r in rows),'retained_translation_pairs':delta['retained_units'],'units':len(files)}))


if __name__=='__main__':main()
