"""Seal exact local integration evidence; publish no private documents or answers."""
import copy,hashlib,json,os,re,shutil,subprocess
from pathlib import Path
os.umask(0o077)
ROOT=Path(__file__).resolve().parent
EN=Path('/home/trc/Downloads/science-europe-template')
ZH=Path('/home/trc/Downloads/science-europe-template-zhtw')
TOOL=Path('/home/trc/Downloads/dsw-document-template-tool')
PRIOR=Path('/home/trc/.local/share/dsw-q3-prose-final.oDtqal')
DEST=ZH/'reviews/2026-09-23-q3-policy-prose-integration'
ALIASES={'P19':'REAL-SNAPSHOT-A','P21':'REAL-SNAPSHOT-B'}
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def cp(a,b):
    assert not b.exists();b.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(a,b)
def write(p,value):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')
def main():
    assert not (ROOT/'evidence-sha256.json').exists()
    assert (DEST/'README.md').is_file()
    native,ci,final,visual=map(read,[ROOT/'checks.json',ROOT/'ci.json',ROOT/'final-lock-equivalence.json',ROOT/'visual-review.json'])
    for name in ['native','english','zh-final','ci-verify','compare','final-lock','final-gate']:
        assert read(ROOT/(name+'-exit.json'))['child_exit_code']==0,name
    assert native['passed'] and len(native['rows'])==40
    assert native['page_totals']=={'pdf':168,'word_preview':167}
    assert all(r['passed'] and r['html_bytes_unchanged'] and r['docx_components_unchanged_except_core_timestamps'] for r in native['rows'])
    assert not ci['passed'] and len(ci['rows'])==55 and {r['number'] for r in ci['rows']}==set(range(55))
    for row in ci['rows']:assert row['returncode']==(1 if row['number']==0 else 0) and sha(ROOT/row['log'])==row['log_sha256']
    assert final['passed'] and final['packages_bitwise_identical_across_six_builds']
    assert re.search(r'Ran 481 tests .*?\n\nOK',(ROOT/'zh-final.log').read_text(),re.S)
    assert re.search(r'Ran 281 tests .*?\n\nOK',(ROOT/'english.log').read_text(),re.S)
    assert 'SUCCESS: The template is valid!' in (ROOT/'english.log').read_text()
    assert re.search(r'Ran 9 tests .*?\n\nOK',(ROOT/'comparison-tests.log').read_text(),re.S)
    assert visual['manually_viewed_pages']==len(visual['observations'])==9
    assert read(ROOT/'visual-replay.json')['all_inspected_images_match_successful_replay']
    builds=[Path(Path('/tmp/se-q3-integration-build-'+n+'.log').read_text().strip()) for n in ['01','02','03','04','05','06']]
    manifests=[read(b/'manifest.json') for b in builds]
    assert sha(builds[0]/'manifest.json')==read(ROOT/'manifest.json')['build_manifest_sha256']
    assert sha(builds[2]/'manifest.json')==final['workflow_manifest_sha256']==ci['clean_candidate_manifest_sha256']
    assert sha(builds[4]/'manifest.json')==final['final_manifest_sha256']
    assert sha(builds[5]/'manifest.json')==final['final_rebuild_manifest_sha256']
    for i,build in enumerate(builds,1):
        cp(build/'manifest.json',ROOT/'build-receipts'/f'manifest-{i:02d}.json')
        for name in ['english.zip','chinese.zip']:
            assert sha(build/name)==final['package_sha256'][name]==manifests[i-1]['sha256'][name]
    for name,repo in [('english',EN),('translation',ZH),('tooling',TOOL)]:
        assert subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()==final['final_checkouts'][name]['commit']
    for name in ['english.zip','chinese.zip']:cp(builds[4]/name,ROOT/'final-packages'/name)
    for label,build in [('initial-attempt',builds[0]),('full-workflow',builds[2]),('final-lock',builds[4])]:
        for path in build.glob('*.json'):cp(path,ROOT/'build-receipts'/label/path.name)
    for name in ['en-check-01','en-check-02','en-target-01','zh-target-01','zh-target-02','en-source-probe-01','en-word-probe-01','build-01','build-02','build-03','build-04','build-05','build-06']:
        cp(Path('/tmp/se-q3-integration-'+name+'.log'),ROOT/'earlier-logs'/(name+'.log'))
    for name in ['q3-policy-prose-integration-01.json','word-empty-section-integration-051.json']:
        cp(EN/'outputs'/name,ROOT/'english-source-probes'/name)
    cp(ZH/'.github/workflows/pilot-checks.yml',ROOT/'pilot-checks.yml')
    assert sha(ROOT/'pilot-checks.yml')==ci['workflow_sha256']
    for name,repo in [('q3_policy_prose_contract.py',EN),('q3_policy_prose_integration.py',ZH)]:cp(repo/'scripts'/name,ROOT/name)
    assert sha(PRIOR/'evidence-sha256.json')==read(ROOT/'manifest.json')['prior_seal']
    previous=read(PRIOR/'evidence-sha256.json')['files']
    assert len(previous)==1345 and all(sha(PRIOR/r['path'])==r['sha256'] for r in previous)
    assert {str(p.relative_to(PRIOR)) for p in PRIOR.rglob('*') if p.is_file()}=={r['path'] for r in previous}|{'evidence-sha256.json'}
    inventory=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p)) for p in sorted(ROOT.rglob('*')) if p.is_file()]
    write(ROOT/'evidence-sha256.json',dict(status='Paired 0.3.51 integration reproduces the accepted Q3 prototype',release_acceptance=False,files=inventory))
    seal=sha(ROOT/'evidence-sha256.json')
    summary=copy.deepcopy(native)
    for row in summary['rows']:row['case']=ALIASES.get(row['case'],row['case'])
    summary.update(private_evidence_seal_sha256=seal,private_evidence_files=len(inventory),
        public_summary_is_not_a_replayable_private_fixture=True,comparator_tests=9,
        package_sha256=final['package_sha256'],checker_sha256=sha(ROOT/'comparison_helpers.py'))
    write(DEST/'native/private-parity-summary.json',summary)
    for name in ['visual-review.json','runtime.json','visual-replay.json','heading-observation.json']:cp(ROOT/name,DEST/'native'/name)
    cp(ROOT/'ci-result-verification.json',DEST/'ci-result-verification.json')
    for index,name in [(0,'native-input-build-manifest.json'),(1,'native-input-rebuild-manifest.json'),(2,'workflow-build-manifest.json'),(3,'workflow-rebuild-manifest.json'),(4,'build-manifest.json'),(5,'rebuild-manifest.json')]:
        cp(ROOT/'build-receipts'/f'manifest-{index+1:02d}.json',DEST/name)
    for name in ['q3-policy-prose-integration.json','word-empty-section-integration.json','reuse-preparation-integration.json',
                 'empty-section-integration.json','submission-flow-integration.json','full-km-followups-integration.json','submission-reading-integration.json']:
        cp(builds[2]/name,DEST/'build'/name)
    cp(builds[4]/'q3-policy-prose-integration.json',DEST/'build/final-lock-q3-policy-prose-integration.json')
    for name in ['q3-policy-prose-integration-01.json','word-empty-section-integration-051.json']:
        cp(ROOT/'english-source-probes'/name,DEST/'build'/('english-source-'+name))
    for name,data in [('ci.json',ci),('final-lock-equivalence.json',final)]:
        public=copy.deepcopy(data)
        for row in public.get('rows',[]):
            row['args']=[a.replace(str(builds[0]),'$NATIVE_INPUT_BUILD_DIR').replace(str(builds[2]),'$WORKFLOW_BUILD_DIR').replace(str(builds[4]),'$FINAL_BUILD_DIR').replace('../science-europe-template','../english') for a in row['args']]
        write(DEST/name,public)
    write(DEST/'local-checks.json',dict(passed=True,scope='Local integration equivalence, not full document-quality acceptance',
        english_make_check=dict(unit_tests=281,tdk_verified=True,child_exit_code=0,only_declared_requirements_installed=True,log_sha256=sha(ROOT/'english.log')),
        chinese_unit_tests=481,chinese_rerun_exit_code=0,chinese_rerun_log_sha256=sha(ROOT/'zh-final.log'),
        effective_workflow_checks_passed=55,unchanged_non_unit_commands_passed=54,
        original_full_workflow_passed=False,full_workflow_rerun_after_chinese_test_fix=False,
        final_identity_and_content_gate_rerun=True,
        final_lock_equivalence_required=True,github_ci_run=False,comparator_tests=9,comparator_tests_log_sha256=sha(ROOT/'comparison-tests.log'),
        native_groups=40,page_totals=native['page_totals'],manually_viewed_pages=9,package_bitwise_identical_across_six_builds=True,
        translation_file_bytes_unchanged=775,initial_failed_english_test='Old Word prototype test compared raw 0.3.51 sources to 0.3.50 before exact projection',
        initial_failure_log_sha256=sha(ROOT/'earlier-logs/en-check-01.log'),
        failed_chinese_test='Old Word prototype test required current version 0.3.50',failed_chinese_suite_log_sha256=sha(ROOT/'ci/00.log'),
        interrupted_attempts=read(ROOT/'interrupted-runs.json'),no_interrupted_attempt_counted_as_pass=True,
        credentials_used=False,remote_writes=0,release_acceptance=False,native_ms_word=False))
    write(DEST/'private-evidence-receipt.json',dict(private_files=len(inventory),private_seal_sha256=seal,
        prior_private_files_unchanged=1345,prior_private_seal_sha256=sha(PRIOR/'evidence-sha256.json'),private_contexts_documents_images_exported=False))
    for name in ['check.py','comparison_helpers.py','test_comparison_helpers.py','prepare.py','run.py','run_ci.py','run_job.py',
                 'export.py','recheck_final_lock.py','verify_ci_results.py','q3_policy_prose_contract.py','q3_policy_prose_integration.py']:
        cp(ROOT/name,DEST/'checkers'/name)
    public=[dict(path=str(p.relative_to(DEST)),sha256=sha(p)) for p in sorted(DEST.rglob('*')) if p.is_file()]
    write(DEST/'checksums.json',dict(files=public))
    print(json.dumps(dict(passed=True,private_files=len(inventory),private_seal=seal,public_files=len(public),public_seal=sha(DEST/'checksums.json'))))
if __name__=='__main__':main()
