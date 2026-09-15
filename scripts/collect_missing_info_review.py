"""Archive selected native regressions without overwriting the failing 0.3.19 audit."""
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
    for name in ['build', 'candidate', 'rebuild', 'prior-audit', 'english', 'document', 'destination']:
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args(); assert not a.destination.exists()
    baseline_hashes = read(a.prior_audit, 'checksums.json'); verify(a.prior_audit, baseline_hashes)
    report = read(a.build, 'missing-info-report.json'); renders = read(a.build, 'missing-info-render-report.json')
    assert report['selected_checks_passed'] and renders['all_renders_succeeded']
    assert report['release_acceptance'] is False and len(report['rows']) == 22 and len(renders['renders']) == 66
    assert all(r['rendered'] for r in renders['renders'])
    assert len({(r['case'],r['language'],r['format']) for r in renders['renders']}) == 66
    expected = {(r['case'], r['language']) for r in report['rows']}; assert len(expected) == 22
    packages = report['package_sha256']; assert packages == renders['package_sha256']
    for build in [a.build, a.candidate, a.rebuild]: verify(build, packages)
    for build in [a.candidate, a.rebuild]:
        manifest = read(build, 'manifest.json')
        assert manifest['status'] == 'candidate' and manifest['source']['version'] == '0.3.20'
        assert all(not state['dirty'] for state in manifest['checkouts'].values())
    assert sha(ROOT/'scripts/check_missing_info_outputs.py') == report['checker_sha256']
    verify(ROOT/'scripts', report['helper_sha256'])
    assert sha(a.english/'scripts/probe_pdf_budget_reading.py') == report['english_helper_sha256']
    copies = []
    def keep(source, destination): copies.append((source, Path(destination)))
    for row in report['rows']:
        verify(a.build, row['artifact_sha256'])
        name = row['case']+'-'+row['language']
        for fmt in ['pdf', 'docx']:
            for suffix in ['', '.fixture.json']:
                file = name+'.'+fmt+suffix; keep(a.build/'renders'/file, 'native/'+file)
        keep(a.build/'word-preview'/(name+'.pdf'), 'word-preview/'+name+'.pdf')
        locale = 'en' if row['language'] == 'english' else 'zh-Hant'
        for suffix in ['.json', '.events.json']:
            file = row['case']+suffix; keep(a.english/'fixtures/pilot'/locale/file, 'fixtures/'+locale+'/'+file)
    for name in ['missing-info-report.json', 'missing-info-render-report.json', 'manifest.json']:
        keep(a.build/name, name)
    for name in ['missing-info-translation-proof.json', 'missing-info-group-probe.json', 'pdf-budget-reading-probe-chinese.json']:
        probe = read(a.candidate, name); assert probe['passed']
        if 'package_sha256' in probe: assert probe['package_sha256'] == packages
        keep(a.candidate/name, 'probes/'+name)
    keep(a.candidate/'manifest.json', 'candidate-manifest.json'); keep(a.rebuild/'manifest.json', 'rebuild-manifest.json')
    for name in ['scripts/check_missing_info_outputs.py', 'scripts/run_missing_info.py', 'scripts/probe_missing_info_translation.py',
                 'scripts/probe_missing_info_group.py', 'scripts/collect_missing_info_review.py', 'pipeline.yml']:
        keep(ROOT/name, 'reproduce/'+name)
    keep(a.english/'scripts/generate_missing_info_fixtures.py', 'reproduce/generate_missing_info_fixtures.py')
    # Preserve the previous failed report and samples with their original hashes.
    for name in baseline_hashes:
        if name.startswith(('native/', 'fixtures/')) or name in ['README.md', 'missing-info-report.json', 'check.py', 'audit.py',
                'extra_case.py', 'fixture-validation.json', 'extra-fixture-validation.json']:
            keep(a.prior_audit/name, 'prior-0.3.19/'+name)
    keep(a.prior_audit/'checksums.json', 'prior-0.3.19-original-checksums.json')
    keep(a.document, 'README.md')
    for file in sorted(a.build.glob('*.png')): keep(file, 'page-samples/'+file.name)
    for source, destination in copies:
        assert source.is_file(), source
    a.destination.mkdir(parents=True)
    for source, destination in copies:
        target = a.destination/destination; target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, target)
    hashes = {str(f.relative_to(a.destination)): sha(f) for f in sorted(a.destination.rglob('*')) if f.is_file()}
    (a.destination/'checksums.json').write_text(json.dumps(hashes, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'archive': str(a.destination), 'verified_files': len(hashes)}))


if __name__ == '__main__': main()
