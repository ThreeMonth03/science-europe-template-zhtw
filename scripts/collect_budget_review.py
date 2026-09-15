"""Archive bounded Q15 evidence; preserve stock failures and rejected diagnoses."""
import argparse
import json
from pathlib import Path
import shutil
import zipfile
from artifact_utils import sha
from collect_context_review import read, verify_files
from collect_paper_review import PROBES

ROOT = Path(__file__).resolve().parents[1]
CASES = ['preservation-complete', 'budget-long', 'budget-many']
KINDS = ['preservation', 'sharing', 'polish', 'format', 'reading', 'quality']


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['baseline', 'variant', 'prior-stock', 'prior-tables', 'prior-build',
                 'rebuild', 'english', 'rehearsal', 'diagnosis-source', 'review-document', 'destination']:
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args()
    assert not a.destination.exists(), 'Never overwrite a review'
    packages = {n:sha(a.baseline/n) for n in ['english.zip','chinese.zip']}
    old_packages = {n:sha(a.prior_build/n) for n in packages}
    copies = []
    def keep(source, name): copies.append((source, Path(name)))
    for side,root in [('stock',a.baseline),('tables',a.variant),
                      ('prior-stock',a.prior_stock),('prior-tables',a.prior_tables)]:
        prior = side.startswith('prior-'); tables = side.endswith('tables')
        pairs = {(c,l) for c in (CASES if tables else CASES[:1]) for l in ['english','chinese']}
        digests = old_packages if prior else packages
        manifest,pilot,renders = [read(root,n) for n in ['manifest.json','pilot-report.json','render-results.json']]
        assert manifest['status']==('runtime-experiment' if tables else 'candidate')
        assert all(not v['dirty'] for v in manifest['checkouts'].values())
        assert manifest['source']['version']==('0.3.15' if prior else '0.3.16')
        verify_files(root,digests)
        assert all(manifest['sha256'][n]==h for n,h in digests.items())
        assert pilot['semantic_checks_passed'] and pilot['package_sha256']==digests
        # Prior stock is immutable 0.3.15 evidence with one additional case.
        rendered={(r['case'],r['language'],r['format']) for r in renders}
        expected={(c,l,f) for c,l in pairs for f in ['html','pdf','docx']}
        assert all(r['passed'] for r in renders) and expected<=rendered
        if side!='prior-stock': assert rendered==expected and len(renders)==len(expected)
        issues=[r for r in pilot['blocking_issues'] if (r['case'],r['language']) in pairs]
        expected_issues=set() if tables else {(c,l,k) for c,l in pairs for k in ['markdown-table-unsupported','docx-table-missing']}
        assert {(r['case'],r['language'],r['code']) for r in issues}==expected_issues
        assert len(issues)==len(expected_issues) and pilot['passed']==tables
        if side!='prior-stock': assert len(pilot['blocking_issues'])==len(issues)
        verify_files(root/'renders',pilot['sha256'])
        for name in ['manifest.json','pilot-report.json','render-results.json']: keep(root/name,f'{side}/{name}')
        for case,language in sorted(pairs):
            for fmt in ['pdf','docx']:
                for suffix in ['', '.fixture.json']:
                    name=f'{case}-{language}.{fmt}{suffix}'; keep(root/'renders'/name,f'{side}/{name}')
            name=f'{case}-{language}.pdf'; keep(root/'word-preview'/name,f'{side}/word-preview/{name}')
        if prior: continue
        for kind in ['budget']+KINDS:
            filename='budget-pagination-report.json' if kind=='budget' else kind+'-report.json'
            report=read(root,filename)
            assert report['selected_checks_passed'] and report['release_acceptance'] is False
            assert report['package_sha256']==packages
            assert report['checker_sha256']==sha(ROOT/f'scripts/check_{kind}_outputs.py')
            assert {(r['case'],r['language']) for r in report['rows']}==pairs and len(report['rows'])==len(pairs)
            verify_files(ROOT/'scripts',report.get('helper_sha256',{}))
            for key,folder in [('artifact_sha256',root),('render_sha256',root/'renders')]: verify_files(folder,report.get(key,{}))
            if kind=='budget':
                assert report['prior_package_sha256']==old_packages
                assert sum(r['question_comparisons'] for r in report['rows'])==15*len(pairs)
                verify_files(a.prior_tables if tables else a.prior_stock,report['prior_artifact_sha256'])
                for r in report['rows']:
                    small=r['case']=='preservation-complete'
                    assert r['eligible']==small and bool(r['changed_overview_styles'])==small
                    assert bool(r['q15_pagination']['all_q15_on_one_page'])==small
            keep(root/filename,f'{side}/{filename}')
    replay=read(a.prior_tables,'manifest.json')['artifact_replay']
    original=Path(replay['source_build'])
    assert replay['source_manifest_sha256']==sha(original/'manifest.json')
    assert replay['preparer_sha256']==sha(ROOT/'scripts/prepare_budget_baseline.py')
    verify_files(original,old_packages)
    for name,script in PROBES+[('identifier-translation-probe','identifier_translation')]:
        report=read(a.baseline,name+'.json')
        assert report['passed'] and report['release_acceptance'] is False and report['package_sha256']==packages
        assert report['checker_sha256']==sha(ROOT/f'scripts/probe_{script}.py')
        verify_files(a.english if script=='repository_reading' else ROOT/'scripts',report.get('helper_sha256',{}))
        verify_files(a.english,report.get('source_helper_sha256',{}))
        fixtures={'format_translation':'test_format_volume.py','sharing_translation':'test_sharing_preservation.py','preservation_translation':'test_preservation_coverage.py','answer_states':'test_answer_states.py'}
        if 'fixture_helper_sha256' in report: assert report['fixture_helper_sha256']==sha(a.english/'tests'/fixtures[script])
        if 'adapter_sha256' in report: assert report['adapter_sha256']==sha(a.english/'tests/test_science_europe_contract.py')
        if 'fixture_source_sha256' in report: assert report['fixture_source_sha256']==sha(a.english/'scripts/generate_identifier_fixtures.py')
        for key in ['reviewed_phrases_sha256','phrase_sha256']:
            if key in report: assert report[key]==sha(ROOT/'docs/readability-phrases.json')
        keep(a.baseline/(name+'.json'),'stock/'+name+'.json')
    probe=read(a.baseline,'budget-word-probe.json')
    assert probe['passed'] and probe['release_acceptance'] is False
    assert probe['source_commit']==read(a.baseline,'manifest.json')['source']['commit']
    assert probe['checker_sha256']==sha(a.english/'scripts/probe_budget_word.py')
    for root in [a.english,a.baseline/'en',a.baseline/'translated']:
        assert probe['lua_sha256']==sha(root/'src/word/pilot.lua')
    assert len(probe['rows'])==24 and sum(r['eligible'] for r in probe['rows'])==5
    assert all(r['passed'] and bool(r['changed_overview_paragraphs'])==r['eligible'] for r in probe['rows'])
    keep(a.baseline/'budget-word-probe.json','budget-word-probe.json')
    manifest=read(a.baseline,'manifest.json')
    assert manifest['translation_units']==720 and manifest['untranslated_units']==[]
    for name in ['translation-audit.json','structure-audit.json']:
        assert read(a.baseline,name)==[]; keep(a.baseline/name,'stock/'+name)
    audit=read(a.baseline,'km-binding-audit.json')
    assert not audit['source_dirty'] and audit['source_commit']==manifest['source']['commit']
    assert len(audit['templates'])==34 and all(not t['unbound_variables'] and not t['absent_entities'] for t in audit['templates'])
    keep(a.baseline/'km-binding-audit.json','binding-audit.json')
    runtime=read(a.variant,'runtime-comparison.json')
    assert runtime['selected_comparison_passed'] and runtime['release_acceptance'] is False
    assert runtime['package_sha256']==packages and runtime['checker_sha256']==sha(ROOT/'scripts/compare_runtime_outputs.py')
    assert {(r['case'],r['language']) for r in runtime['checks']}=={(CASES[0],l) for l in ['english','chinese']}
    for side,root in [('stock',a.baseline),('tables',a.variant)]: verify_files(root,runtime['artifact_sha256'][side])
    keep(a.variant/'runtime-comparison.json','runtime-comparison.json')
    rebuild=read(a.rebuild,'manifest.json')
    assert rebuild['status']=='candidate' and all(not v['dirty'] for v in rebuild['checkouts'].values())
    assert rebuild['source']==manifest['source']; verify_files(a.rebuild,packages)
    keep(a.rebuild/'manifest.json','rebuild-manifest.json')
    delta={}
    for locale in ['en','translated']:
        old,new=[{str(f.relative_to(root/locale)):sha(f) for f in sorted((root/locale/'src').rglob('*')) if f.is_file()} for root in [a.prior_build,a.baseline]]
        assert old.keys()==new.keys()
        changed=sorted(n for n in old if old[n]!=new[n]); assert changed==['src/word/pilot.lua']
        delta[locale]={'changed_source_paths':changed,'prior_source_sha256':old,'source_sha256':new,
                       'jinja_css_reference_and_other_sources_byte_identical':True}
    # Retain disposable A/B files, explicitly separate from native output.
    rehearsal=read(a.rehearsal,'report.json')
    # The diagnosis used the prior patched control, not stock Markdown parsing.
    source=a.prior_tables/'renders/preservation-complete-chinese.docx'
    original_control=a.diagnosis_source
    assert rehearsal['source_sha256']==sha(original_control)
    assert rehearsal['release_acceptance'] is False
    from check_budget_outputs import compare_word
    from docx import Document
    compare_word(Document(original_control),Document(source),False)
    with zipfile.ZipFile(original_control) as z: parts={n:z.read(n) for n in z.namelist()}
    for profile,row in rehearsal['variants'].items():
        target=a.rehearsal/(profile+'.docx'); assert row['sha256']==sha(target)
        with zipfile.ZipFile(target) as z:
            assert set(z.namelist())==set(parts)
            assert [n for n in parts if parts[n]!=z.read(n)]==['word/document.xml']
        for ext in ['docx','pdf']: keep(a.rehearsal/(profile+'.'+ext),'diagnosis/'+profile+'.'+ext)
    keep(a.rehearsal/'report.json','diagnosis/report.json')
    keep(original_control,'diagnosis/source.docx')
    keep(a.english/'docs/budget-pagination.md','english-scope.md')
    keep(a.review_document,'README.md')
    payload=(json.dumps({'source_delta':delta,'collector_sha256':sha(Path(__file__)),
        'rehearsal_script_sha256':sha(ROOT/'scripts/rehearse_budget_styles.py'),
        'release_acceptance':False},indent=2)+'\n').encode()
    size=len(payload)+sum(source.stat().st_size for source,_ in copies)
    assert size<25_000_000 and len({n for _,n in copies})==len(copies)
    a.destination.mkdir(parents=True,exist_ok=False); hashes={}
    for source,name in copies:
        target=a.destination/name; target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,target); hashes[str(name)]=sha(target)
    target=a.destination/'budget-source-delta.json'; target.write_bytes(payload); hashes[target.name]=sha(target)
    (a.destination/'checksums.json').write_text(json.dumps(hashes,indent=2)+'\n')
    print(json.dumps({'hashed_files':len(hashes),'bytes':size,'destination':str(a.destination)}))


if __name__=='__main__': main()
