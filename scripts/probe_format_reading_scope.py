"""0.3.31 Q2-only source/translation delta and retained Q11 behavior checks."""
import argparse
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
from artifact_utils import sha
from probe_pdf_budget_translation import pair
from probe_personal_data_translation import verify_current_translation_chain
ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,required=True);p.add_argument('--english',type=Path,required=True)
    a=p.parse_args();sys.path[:0]=[str(a.english.resolve()/n) for n in ['scripts','tests']]
    from format_reading_contract import check_roots
    from archive_basis_contract import check_roots as archive_checks
    from probe_archive_gap_panels import rows,FIRST,LAST,PAIRS
    from bs4 import BeautifulSoup
    files=sorted((ROOT/'translation/tree').rglob('translation.md'))
    personal,following=verify_current_translation_chain([pair(f.read_text()) for f in files])
    current=json.loads((a.build/'manifest.json').read_text());assert current['untranslated_units']==[]
    hashes={str(f.relative_to(ROOT/'translation')):sha(f) for f in files}
    assert hashes==current['translation_tree_sha256']
    baseline=following['format_reading']['baseline']
    data=subprocess.check_output(['git','-C',str(ROOT),'archive',baseline,'translation/tree'])
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        old={f.name:archive.extractfile(f).read() for f in archive if f.isfile()}
    new={str(f.relative_to(ROOT)):f.read_bytes() for f in files}
    changed={n for n in old.keys()|new.keys() if old.get(n)!=new.get(n)}
    assert changed and all(n.startswith('translation/tree/src/questions/02-what-data.html.j2/') for n in changed)
    prior=ROOT/'reviews/2026-09-17-archive-gap-panels/probes/archive-gap-scope.json'
    proof=json.loads(prior.read_text());checks=[]
    for old_row in proof['rows']:
        folder=old_row['language'];root=a.build/folder;before=old_row['after']
        after={str(f.relative_to(root)):sha(f) for f in (root/'src').rglob('*') if f.is_file()}
        assert before.keys()==after.keys()
        differences=sorted(n for n in before if before[n]!=after[n])
        assert differences==['src/questions/02-what-data.html.j2'],differences
        language='english' if folder=='en' else 'chinese'
        frozen=a.english/'tests/fixtures/format-0.3.30.en.html.j2' if folder=='en' else ROOT/'tests/fixtures/format-0.3.30.zh-Hant.html.j2'
        assert sha(frozen)==('9ae958eae76cd2b2523b9e961d4cb58497ed7449c3fc32b0b1e8f42017e56224' if folder=='en' else '5a9c7f0d4c0cdbf5cc7ab5a493cbc3619521888c2b9055870c57767c41f34555')
        count=check_roots(root,frozen,language)
        archive=a.english/'tests/fixtures/archive-0.3.28.en.html.j2' if folder=='en' else ROOT/'tests/fixtures/archive-0.3.28.zh-Hant.html.j2'
        preserved=archive_checks(root,archive,language);gaps=0
        for _,html,expected in rows(root):
            soup=BeautifulSoup(html,'html.parser');found=[]
            for pair_ids,left,right in zip(PAIRS,FIRST,LAST):
                assert len(soup.select(left))==len(soup.select(right))
                if soup.select(left):found.append(list(pair_ids))
            assert found==expected;gaps+=1
        checks.append({'language':folder,'before':before,'after':after,'changed':differences,
            'q2_exact_dom_checks':count,'q11_branch_checks':preserved,'q11_gap_combinations':gaps,'frozen_sha256':sha(frozen)})
    report={'passed':True,'release_acceptance':False,'rows':checks,'reviewed_deltas':following,
        'translation_units':len(files),'translation_tree_sha256':hashes,'checker_sha256':sha(Path(__file__)),
        'contract_sha256':sha(a.english/'scripts/format_reading_contract.py'),
        'package_sha256':{n:sha(a.build/n) for n in ['english.zip','chinese.zip']}}
    target=a.build/'format-reading-scope.json';assert not target.exists();target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'passed':True,'q2_checks':sum(r['q2_exact_dom_checks'] for r in checks),'unchanged_source_files_except':differences,'units':len(files)}))


if __name__=='__main__':main()
