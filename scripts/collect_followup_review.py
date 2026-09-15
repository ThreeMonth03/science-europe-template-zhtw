"""Archive tested Q13 follow-up completeness without promoting stock failures."""
import argparse
import json
from pathlib import Path
import shutil
from artifact_utils import sha
from collect_context_review import read, verify_files
from collect_paper_review import PROBES

ROOT=Path(__file__).resolve().parents[1]
PAIRS={(c,l) for c in ['preservation-complete','identifier-followups'] for l in ['english','chinese']}
KINDS=['identifier_followup','preservation','sharing','polish','format','reading','quality']


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['baseline','variant','prior-stock','prior-tables','rebuild','english','binding-audit','contract-audit','review-document','destination']:
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args(); assert not a.destination.exists(), 'Never overwrite a review'
    packages={n:sha(a.baseline/n) for n in ['english.zip','chinese.zip']}; old_packages={n:sha(a.prior_stock/n) for n in packages}
    copies=[]
    def keep(source,name): copies.append((source,Path(name)))
    for side,root in [('stock',a.baseline),('tables',a.variant),('prior-stock',a.prior_stock),('prior-tables',a.prior_tables)]:
        prior=side.startswith('prior-'); tables=side.endswith('tables'); digests=old_packages if prior else packages
        manifest,pilot,renders=[read(root,n) for n in ['manifest.json','pilot-report.json','render-results.json']]
        assert manifest['status']==('runtime-experiment' if tables else 'candidate')
        assert all(not v['dirty'] for v in manifest['checkouts'].values())
        assert manifest['source']['version']==('0.3.14' if prior else '0.3.15')
        verify_files(root,digests); assert all(manifest['sha256'][n]==h for n,h in digests.items())
        if prior:
            replay=manifest['artifact_replay']; original=Path(replay['source_build'])
            assert replay['source_manifest_sha256']==sha(original/'manifest.json')
            assert replay['preparer_sha256']==sha(ROOT/'scripts/prepare_followup_baseline.py')
            verify_files(original,old_packages)
        assert pilot['semantic_checks_passed'] and pilot['package_sha256']==digests
        expected=set() if tables else {(c,l,code) for c,l in PAIRS for code in ['markdown-table-unsupported','docx-table-missing']}
        assert {(r['case'],r['language'],r['code']) for r in pilot['blocking_issues']}==expected
        assert len(pilot['blocking_issues'])==len(expected) and pilot['passed']==(not expected)
        assert len(renders)==12 and all(r['passed'] for r in renders)
        assert {(r['case'],r['language'],r['format']) for r in renders}=={(c,l,f) for c,l in PAIRS for f in ['html','pdf','docx']}
        verify_files(root/'renders',pilot['sha256'])
        for name in ['manifest.json','pilot-report.json','render-results.json']: keep(root/name,f'{side}/{name}')
        for case,language in sorted(PAIRS):
            for fmt in ['pdf','docx']:
                for suffix in ['', '.fixture.json']:
                    name=f'{case}-{language}.{fmt}{suffix}'; keep(root/'renders'/name,f'{side}/{name}')
            name=f'{case}-{language}.pdf'; keep(root/'word-preview'/name,f'{side}/word-preview/{name}')
        if prior: continue
        for kind in KINDS:
            filename=kind.replace('_','-')+'-report.json'; report=read(root,filename)
            assert report['selected_checks_passed'] and report['release_acceptance'] is False and report['package_sha256']==packages
            assert report['checker_sha256']==sha(ROOT/f'scripts/check_{kind}_outputs.py')
            assert len(report['rows'])==4 and {(r['case'],r['language']) for r in report['rows']}==PAIRS
            verify_files(ROOT/'scripts',report.get('helper_sha256',{}))
            for key,folder in [('artifact_sha256',root),('render_sha256',root/'renders')]: verify_files(folder,report.get(key,{}))
            if kind=='identifier_followup':
                assert report['prior_package_sha256']==old_packages
                assert sum(r['controlled_question_comparisons'] for r in report['rows'])==60
                for r in report['rows']:
                    complete=r['case']=='preservation-complete'
                    assert r['warning_paragraphs_added']==(0 if complete else 3)
                    assert r['child_states']==({'complete':4} if complete else {'missing':4,'explicit-no':2,'complete':2})
                verify_files(a.prior_tables if tables else a.prior_stock,report['prior_artifact_sha256'])
            keep(root/filename,f'{side}/{filename}')
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
    for name in ['translation-audit.json','structure-audit.json']:
        assert read(a.baseline,name)==[]; keep(a.baseline/name,'stock/'+name)
    runtime=read(a.variant,'runtime-comparison.json')
    assert runtime['selected_comparison_passed'] and runtime['release_acceptance'] is False and runtime['package_sha256']==packages
    assert runtime['checker_sha256']==sha(ROOT/'scripts/compare_runtime_outputs.py')
    assert {(r['case'],r['language']) for r in runtime['checks']}==PAIRS
    for side,root in [('stock',a.baseline),('tables',a.variant)]: verify_files(root,runtime['artifact_sha256'][side])
    keep(a.variant/'runtime-comparison.json','runtime-comparison.json')
    audit=json.loads(a.binding_audit.read_text()); source=read(a.baseline,'manifest.json')['source']['commit']
    assert not audit['source_dirty'] and audit['source_commit']==source
    assert len(audit['templates'])==34 and all(not t['unbound_variables'] and not t['absent_entities'] for t in audit['templates'])
    keep(a.binding_audit,'binding-audit.json'); keep(a.english/'docs/identifier-followups.md','english-scope.md')
    contract=json.loads(a.contract_audit.read_text()); assert contract['source_commit']==source
    assert contract['checker_sha256']==sha(a.english/'scripts/audit_identifier_contract.py')
    assert set(contract['locales'])=={'en','zh-Hant'}
    for locale,row in contract['locales'].items():
        assert not row['fixture_errors'] and len(row['fields'])==3
        assert row['fixture_sha256']==sha(a.english/'fixtures/pilot'/locale/'identifier-followups.events.json')
    keep(a.contract_audit,'contract-audit.json')
    rebuild=read(a.rebuild,'manifest.json')
    assert rebuild['status']=='candidate' and all(not v['dirty'] for v in rebuild['checkouts'].values())
    verify_files(a.rebuild,packages); keep(a.rebuild/'manifest.json','rebuild-manifest.json')
    delta={}
    for locale in ['en','translated']:
        old,new=[{str(f.relative_to(root/locale)):sha(f) for f in sorted((root/locale/'src').rglob('*')) if f.is_file()} for root in [a.prior_stock,a.baseline]]
        changed=sorted(n for n in old if old[n]!=new.get(n))
        assert old.keys()==new.keys() and changed==['src/questions/13-persistent-identifier.html.j2']
        delta[locale]={'changed_source_paths':changed,'prior_source_sha256':old,'source_sha256':new,'css_lua_reference_and_other_sources_byte_identical':True}
    payload=(json.dumps(delta,indent=2)+'\n').encode(); keep(a.review_document,'README.md')
    size=len(payload)+sum(source.stat().st_size for source,_ in copies)
    assert size<25_000_000 and len({n for _,n in copies})==len(copies)
    a.destination.mkdir(parents=True,exist_ok=False); hashes={}
    for source,name in copies:
        target=a.destination/name; target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,target); hashes[str(name)]=sha(target)
    target=a.destination/'followup-source-delta.json'; target.write_bytes(payload); hashes[target.name]=sha(target)
    (a.destination/'checksums.json').write_text(json.dumps(hashes,indent=2)+'\n')
    print(json.dumps({'hashed_files':len(hashes),'bytes':size,'destination':str(a.destination)}))


if __name__=='__main__': main()
