"""Archive exact 0.3.17 comparisons without promoting known worker failures."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import zipfile
from artifact_utils import sha
from collect_context_review import read,verify_files
from collect_paper_review import PROBES
from check_long_budget_outputs import styles_only_added

ROOT=Path(__file__).resolve().parents[1]
CASES=['preservation-complete','budget-long','budget-many']
KINDS=['long-budget','preservation','sharing','polish','format','reading','quality']


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['baseline','variant','prior-stock','prior-tables','rebuild','english','diagnosis','diagnosis-source','review-document','destination']:
        p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args(); assert not a.destination.exists(), 'Never overwrite a review'
    packages={n:sha(a.baseline/n) for n in ['english.zip','chinese.zip']}
    prior_packages={n:sha(a.prior_stock/n) for n in packages}
    copies=[]
    def keep(source,name): copies.append((source,Path(name)))
    for side,root in [('stock',a.baseline),('tables',a.variant),('prior-stock',a.prior_stock),('prior-tables',a.prior_tables)]:
        prior=side.startswith('prior-'); tables=side.endswith('tables')
        pairs={(c,l) for c in (CASES if tables else CASES[:1]) for l in ['english','chinese']}
        digests=prior_packages if prior else packages
        manifest,pilot,renders=[read(root,n) for n in ['manifest.json','pilot-report.json','render-results.json']]
        assert manifest['status']==('runtime-experiment' if tables else 'candidate')
        assert manifest['source']['version']==('0.3.16' if prior else '0.3.17')
        assert all(not v['dirty'] for v in manifest['checkouts'].values())
        verify_files(root,digests); assert all(manifest['sha256'][n]==h for n,h in digests.items())
        assert pilot['semantic_checks_passed'] and pilot['package_sha256']==digests
        expected={(c,l,f) for c,l in pairs for f in ['html','pdf','docx']}
        assert {(r['case'],r['language'],r['format']) for r in renders}==expected
        assert len(renders)==len(expected) and all(r['passed'] for r in renders)
        issues=set() if tables else {(c,l,k) for c,l in pairs for k in ['markdown-table-unsupported','docx-table-missing']}
        assert {(r['case'],r['language'],r['code']) for r in pilot['blocking_issues']}==issues
        assert len(pilot['blocking_issues'])==len(issues) and pilot['passed']==tables
        verify_files(root/'renders',pilot['sha256'])
        for name in ['manifest.json','pilot-report.json','render-results.json']: keep(root/name,f'{side}/{name}')
        for case,language in sorted(pairs):
            for fmt in ['pdf','docx']:
                for suffix in ['', '.fixture.json']:
                    name=f'{case}-{language}.{fmt}{suffix}'; keep(root/'renders'/name,f'{side}/{name}')
            name=f'{case}-{language}.pdf'; keep(root/'word-preview'/name,f'{side}/word-preview/{name}')
        if prior: continue
        for kind in KINDS:
            filename=kind+'-report.json'; report=read(root,filename)
            assert report['selected_checks_passed'] and report['release_acceptance'] is False
            assert report['package_sha256']==packages
            assert report['checker_sha256']==sha(ROOT/('scripts/check_'+kind.replace('-','_')+'_outputs.py'))
            assert {(r['case'],r['language']) for r in report['rows']}==pairs and len(report['rows'])==len(pairs)
            verify_files(ROOT/'scripts',report.get('helper_sha256',{}))
            for key,folder in [('artifact_sha256',root),('render_sha256',root/'renders')]: verify_files(folder,report.get(key,{}))
            if kind=='long-budget':
                assert report['prior_package_sha256']==prior_packages
                assert sum(r['question_comparisons'] for r in report['rows'])==15*len(pairs)
                verify_files(a.prior_tables if tables else a.prior_stock,report['prior_artifact_sha256'])
                for r in report['rows']:
                    if r['case']=='budget-long': assert r['complete_purpose_paragraphs']==60 and r['purpose_xml_paragraphs_preserved']==64
                    else: assert r['purpose_xml_paragraphs_preserved']==0 and r['prior_word_pages']==r['word_pages']
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
    manifest=read(a.baseline,'manifest.json')
    for name,script,count,positive in [('budget-word-probe','probe_budget_word.py',24,5),('long-budget-word-probe','probe_long_budget_word.py',28,9)]:
        report=read(a.baseline,name+'.json')
        assert report['passed'] and report['release_acceptance'] is False
        assert report['source_commit']==manifest['source']['commit'] and report['checker_sha256']==sha(a.english/'scripts'/script)
        assert report['lua_sha256']==sha(a.baseline/'en/src/word/pilot.lua')==sha(a.baseline/'translated/src/word/pilot.lua')
        assert len(report['rows'])==count and sum(r['eligible'] for r in report['rows'])==positive
        assert all(r['passed'] for r in report['rows']); verify_files(a.english,report.get('helper_sha256',{}))
        keep(a.baseline/(name+'.json'),name+'.json')
    assert manifest['translation_units']==720 and manifest['untranslated_units']==[]
    for name in ['translation-audit.json','structure-audit.json']:
        assert read(a.baseline,name)==[]; keep(a.baseline/name,'stock/'+name)
    audit=read(a.baseline,'km-binding-audit.json')
    assert audit['source_commit']==manifest['source']['commit'] and not audit['source_dirty']
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
        old,new=[{str(f.relative_to(root/locale)):sha(f) for f in sorted((root/locale/'src').rglob('*')) if f.is_file()} for root in [a.prior_stock,a.baseline]]
        assert old.keys()==new.keys()
        changed=sorted(n for n in old if old[n]!=new[n]); assert changed==['src/word/pilot.lua','src/word/reference.docx']
        refs=[root/locale/'src/word/reference.docx' for root in [a.prior_stock,a.baseline]]
        styles_only_added(*refs)
        with zipfile.ZipFile(refs[0]) as z1,zipfile.ZipFile(refs[1]) as z2:
            assert set(z1.namelist())==set(z2.namelist())
            assert [n for n in z1.namelist() if z1.read(n)!=z2.read(n)]==['word/styles.xml']
        delta[locale]={'changed_source_paths':changed,'prior_source_sha256':old,'source_sha256':new,'reference_only_new_table_style':True}
    source_changes=subprocess.check_output(['git','-C',str(a.english),'diff','--name-only',read(a.prior_stock,'manifest.json')['source']['commit'],manifest['source']['commit'],'--','src','scripts/prepare_layout.py'],text=True).splitlines()
    assert source_changes==['scripts/prepare_layout.py','src/word/pilot.lua']
    diagnosis=read(a.diagnosis,'report.json')
    assert diagnosis['source_sha256']==sha(a.diagnosis_source)
    assert diagnosis['checker_sha256']==sha(ROOT/'scripts/rehearse_long_budget.py') and diagnosis['release_acceptance'] is False
    assert set(diagnosis['variants'])=={'full-width','full-width-repeat','paragraph-rows-repeat'}
    with zipfile.ZipFile(a.diagnosis_source) as z: original={n:z.read(n) for n in z.namelist()}
    for name,row in diagnosis['variants'].items():
        assert row['sha256']==sha(a.diagnosis/(name+'.docx'))
        with zipfile.ZipFile(a.diagnosis/(name+'.docx')) as z:
            assert set(z.namelist())==set(original)
            assert [n for n in original if original[n]!=z.read(n)]==['word/document.xml']
        for ext in ['docx','pdf']: keep(a.diagnosis/(name+'.'+ext),'diagnosis/'+name+'.'+ext)
    rejected=subprocess.check_output(['pdftotext','-f','8','-l','8','-layout',str(a.diagnosis/'full-width-repeat.pdf'),'-'],text=True)
    assert '資料管理預算' in rejected and 'BUDGET-PARA-' not in rejected
    keep(a.diagnosis/'report.json','diagnosis/report.json'); keep(a.diagnosis_source,'diagnosis/source.docx')
    keep(a.english/'docs/long-budget-reading.md','english-scope.md'); keep(a.review_document,'README.md')
    payload=(json.dumps({'source_delta':delta,'git_source_changes':source_changes,'collector_sha256':sha(Path(__file__)),
        'release_acceptance':False,'rejected_diagnosis':'full-width-repeat leaves budget heading alone on page 8'},indent=2)+'\n').encode()
    size=len(payload)+sum(s.stat().st_size for s,_ in copies)
    assert size<25_000_000 and len({n for _,n in copies})==len(copies)
    a.destination.mkdir(parents=True,exist_ok=False); hashes={}
    for source,name in copies:
        target=a.destination/name; target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(source,target); hashes[str(name)]=sha(target)
    target=a.destination/'long-budget-source-delta.json'; target.write_bytes(payload); hashes[target.name]=sha(target)
    (a.destination/'checksums.json').write_text(json.dumps(hashes,indent=2)+'\n')
    print(json.dumps({'hashed_files':len(hashes),'bytes':size,'destination':str(a.destination)}))


if __name__=='__main__': main()
