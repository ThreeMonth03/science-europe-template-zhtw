"""Archive initial 22-case-language exports and the explicitly separate final Q7 repair."""
import argparse
import json
from pathlib import Path
import shutil
from artifact_utils import sha

ROOT = Path(__file__).resolve().parents[1]


def read(root, name): return json.loads((root/name).read_text())


def verify(root, hashes):
    for name, digest in hashes.items(): assert sha(root/name) == digest, ('Evidence drift', root, name)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['initial', 'final', 'candidate', 'rebuild', 'prior-audit', 'english', 'document', 'destination']:
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args(); assert not a.destination.exists()
    prior_hashes = read(a.prior_audit, 'checksums.json'); verify(a.prior_audit, prior_hashes)
    initial = read(a.initial, 'missing-info-complete-initial-report.json')
    final = read(a.final, 'missing-info-verified-report.json')
    assert len(initial['rows']) == 22 and not initial['selected_checks_passed']
    failures = [(r['case'], r['language'], r['errors'], r['reading_issues']) for r in initial['rows'] if r['errors'] or r['reading_issues']]
    assert failures == [('personal-data-partial', 'chinese', [{'code': 'invalid-block-in-paragraph'}], [])]
    assert len(final['rows']) == 6 and final['selected_checks_passed']
    assert {(r['case'],r['language']) for r in final['rows']} == {(c,l) for c in ['personal-data-partial','preservation-complete','budget-long'] for l in ['english','chinese']}
    proof = read(a.candidate, 'q7-boundary-isolation-proof.json'); assert proof['passed'] and len(proof['rows']) == 22
    assert all(r['q7_output_byte_identical'] for r in proof['rows'] if r['case'] != 'personal-data-partial')
    for row in proof['package_diffs']:
        assert row['before_sha256'] == initial['package_sha256'][row['language']+'.zip']
        assert row['after_sha256'] == final['package_sha256'][row['language']+'.zip']
    verify(a.candidate, final['package_sha256']); verify(a.rebuild, final['package_sha256'])
    copies = []
    def keep(source, target): copies.append((source, Path(target)))
    for label, build, report, expected in [('initial',a.initial,initial,66),('final',a.final,final,18)]:
        verify(build, report['package_sha256'])
        renders = read(build, 'missing-info-render-report.json')
        assert renders['all_renders_succeeded'] and len(renders['renders']) == expected
        assert len({(r['case'],r['language'],r['format']) for r in renders['renders']}) == expected
        assert all(r['rendered'] for r in renders['renders'])
        for row in report['rows']:
            verify(build, row['artifact_sha256'])
            name = row['case']+'-'+row['language']
            for fmt in ['pdf','docx']:
                for suffix in ['', '.fixture.json']:
                    filename = name+'.'+fmt+suffix; keep(build/'renders'/filename, label+'/native/'+filename)
            keep(build/'word-preview'/(name+'.pdf'), label+'/word-preview/'+name+'.pdf')
            locale = 'en' if row['language'] == 'english' else 'zh-Hant'
            for suffix in ['.json','.events.json']:
                filename = row['case']+suffix; keep(a.english/'fixtures/pilot'/locale/filename, 'fixtures/'+locale+'/'+filename)
        for filename in ['manifest.json','missing-info-render-report.json']:
            keep(build/filename, label+'/'+filename)
        filename = 'missing-info-complete-initial-report.json' if label == 'initial' else 'missing-info-verified-report.json'
        keep(build/filename, label+'/missing-info-report.json')
        for file in sorted(build.glob('*.png')): keep(file,label+'/page-samples/'+file.name)
    for name in ['q7-boundary-isolation-proof.json','missing-info-translation-proof.json','missing-info-group-probe.json','pdf-budget-reading-probe-chinese.json']:
        assert read(a.candidate,name)['passed']; keep(a.candidate/name,'probes/'+name)
    for label, build in [('candidate',a.candidate),('rebuild',a.rebuild)]:
        manifest=read(build,'manifest.json'); assert manifest['status']=='candidate' and all(not c['dirty'] for c in manifest['checkouts'].values())
        keep(build/'manifest.json',label+'-manifest.json')
    for filename in list(prior_hashes) + ['checksums.json']:
        keep(a.prior_audit/filename,'prior-0.3.19/'+filename)
    for label, root in [('initial',a.initial),('final',a.final)]:
        keep(root/'owned-test-template-cleanup.json',label+'/owned-test-template-cleanup.json')
    for filename in ['check_missing_info_outputs.py','run_missing_info.py','probe_missing_info_translation.py','probe_missing_info_group.py',
                     'probe_q7_boundary_isolation.py','collect_missing_info_final_review.py']:
        keep(ROOT/'scripts'/filename,'reproduce/'+filename)
    keep(ROOT/'pipeline.yml','reproduce/pipeline.yml'); keep(a.document,'README.md')
    for source,_ in copies: assert source.is_file(), source
    a.destination.mkdir(parents=True)
    for source,name in copies:
        target=a.destination/name; target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(source,target)
    hashes={str(f.relative_to(a.destination)):sha(f) for f in sorted(a.destination.rglob('*')) if f.is_file()}
    (a.destination/'checksums.json').write_text(json.dumps(hashes,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'archive':str(a.destination),'verified_files':len(hashes)}))


if __name__=='__main__': main()
