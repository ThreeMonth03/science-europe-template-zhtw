"""Seal completed private evidence; export only content-free local receipts."""
import copy,hashlib,json,os,re,shutil,subprocess
from pathlib import Path

os.umask(0o077)
ROOT=Path(__file__).resolve().parent
ZH=Path('/home/trc/Downloads/science-europe-template-zhtw')
EN=Path('/home/trc/Downloads/science-europe-template')
TOOL=Path('/home/trc/Downloads/dsw-document-template-tool')
PRIOR=Path('/home/trc/.local/share/dsw-preparation-prose.1ysXWG')
DEST=ZH/'reviews/2026-09-23-preparation-prose-integration'
BUILDS=[Path(Path('/tmp/se-preparation-integration-build-'+n+'.log').read_text().strip()) for n in ['01','02']]
ALIASES={'P19':'REAL-SNAPSHOT-A','P21':'REAL-SNAPSHOT-B'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def write(p,value):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x') as f:f.write(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def cp(a,b):
    assert not b.exists();b.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(a,b)
def main():
    assert not (ROOT/'evidence-sha256.json').exists()
    native=read(ROOT/'checks.json');ci=read(ROOT/'ci.json')
    assert native['passed'] and len(native['rows'])==28
    assert native['page_totals']=={'pdf':130,'word_preview':133}
    assert all(r['passed'] and r['html_bytes_unchanged'] and r['docx_components_unchanged_except_core_timestamps'] for r in native['rows'])
    assert ci['passed'] and len(ci['rows'])==53 and all(r['returncode']==0 for r in ci['rows'])
    assert {r['number'] for r in ci['rows']}==set(range(53))
    for row in ci['rows']:assert sha(ROOT/row['log'])==row['log_sha256']
    assert re.search(r'Ran 467 tests .*?\n\nOK',(ROOT/'ci/00.log').read_text(),re.S)
    english_log=Path('/tmp/se-preparation-integration-en-check-01.log')
    assert re.search(r'Ran 258 tests .*?\n\nOK',english_log.read_text(),re.S)
    assert re.search(r'Ran 9 tests .*?\n\nOK',(ROOT/'comparison-tests-final.log').read_text(),re.S)
    assert 'ModuleNotFoundError' in (ROOT/'comparison-tests.log').read_text()
    visual=read(ROOT/'visual-review.json');observations=read(ROOT/'observation-checks.json')
    assert visual['manually_viewed_pages']==sum(len(r['pages']) for r in visual['observations'])==6
    styles=read(ROOT/'word-style-diagnostic.json')
    assert styles['passed'] and len(styles['rows'])==28 and all(r['docx_unchanged'] for r in styles['rows'])
    assert observations['suspected_english_conjunction_loss_rejected']
    assert all(r['question_15_alone_on_last_page'] for r in observations['known_word_pagination_issue'])
    assert (DEST/'README.md').is_file()
    manifests=[read(p/'manifest.json') for p in BUILDS]
    for m in manifests:
        assert m['status']=='candidate' and all(not c['dirty'] for c in m['checkouts'].values())
        assert m['source']['version']==m['translation']['version']=='0.3.49'
        assert m['translation_units']==775 and not m['untranslated_units']
    assert manifests[0]['checkouts']==manifests[1]['checkouts']
    for name in ['english.zip','chinese.zip']:
        assert sha(BUILDS[0]/name)==sha(BUILDS[1]/name)==manifests[0]['sha256'][name]==manifests[1]['sha256'][name]
    for name,repo in [('english',EN),('translation',ZH),('tooling',TOOL)]:
        assert subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()==manifests[0]['checkouts'][name]['commit']
    cp(english_log,ROOT/'en-check-01.log')
    for name in ['build-01','build-02','en-target','zh-target-01','zh-target-02']:
        cp(Path('/tmp/se-preparation-integration-'+name+'.log'),ROOT/(name+'.log'))
    # Copy the live gate reports and workflow into the private inventory as well.
    gate_names=['reuse-preparation-integration.json','empty-section-integration.json',
        'empty-section-engine.json','submission-flow-integration.json',
        'submission-flow-engine-en.json','submission-flow-engine-zh.json',
        'full-km-followups-integration.json']
    for name in gate_names:cp(BUILDS[0]/name,ROOT/'build-receipts'/name)
    for index,build in enumerate(BUILDS):cp(build/'manifest.json',ROOT/'build-receipts'/('manifest.json' if index==0 else 'rebuild-manifest.json'))
    cp(ZH/'.github/workflows/pilot-checks.yml',ROOT/'pilot-checks.yml')
    assert sha(ROOT/'pilot-checks.yml')==ci['workflow_sha256']
    cp(ZH/'scripts/reuse_preparation_integration.py',ROOT/'reuse_preparation_integration.py')
    cp(EN/'scripts/reuse_preparation_contract.py',ROOT/'reuse_preparation_contract.py')
    assert sha(PRIOR/'evidence-sha256.json')==read(ROOT/'manifest.json')['prior_seal']
    prior_inventory=read(PRIOR/'evidence-sha256.json')['files']
    assert len(prior_inventory)==937 and all(sha(PRIOR/r['path'])==r['sha256'] for r in prior_inventory)
    assert {str(p.relative_to(PRIOR)) for p in PRIOR.rglob('*') if p.is_file()}=={r['path'] for r in prior_inventory}|{'evidence-sha256.json'}
    # All native/CI writers must have exited before this script is invoked.
    inventory=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p)) for p in sorted(ROOT.rglob('*')) if p.is_file()]
    write(ROOT/'evidence-sha256.json',dict(status='local source integration verified; known sparse Word layout issue remains',
        release_acceptance=False,files=inventory))
    private_seal=sha(ROOT/'evidence-sha256.json')
    summary=copy.deepcopy(native)
    for row in summary['rows']:row['case']=ALIASES.get(row['case'],row['case'])
    summary.update(private_evidence_seal_sha256=private_seal,private_evidence_files=len(inventory),
        public_summary_is_not_a_replayable_private_fixture=True,comparator_tests=9,
        checker_sha256=sha(ROOT/'comparison_helpers.py'),package_sha256={n:manifests[0]['sha256'][n] for n in ['english.zip','chinese.zip']},
        known_open_quality_issue='MISSING zh-Hant submission LibreOffice preview: Q15 alone on page 3, unchanged from prototype')
    write(DEST/'native/private-parity-summary.json',summary)
    for name in ['visual-review.json','observation-checks.json','word-style-diagnostic.json','runtime.json']:cp(ROOT/name,DEST/'native'/name)
    for index in range(2):cp(ROOT/'build-receipts'/('manifest.json' if index==0 else 'rebuild-manifest.json'),DEST/('build-manifest.json' if index==0 else 'rebuild-manifest.json'))
    for name in gate_names:cp(ROOT/'build-receipts'/name,DEST/'build'/name)
    public_ci=copy.deepcopy(ci)
    for row in public_ci['rows']:
        row['args']=[a.replace(str(BUILDS[0]),'$SE_BUILD_DIR').replace('../science-europe-template','../english') for a in row['args']]
    write(DEST/'ci.json',public_ci)
    write(DEST/'local-checks.json',dict(passed=True,scope='Local integration regression checks, not full document-quality acceptance',
        english_clean_make_check=dict(passed=True,unit_tests=258,tdk_verified=True,exit_code=0,
            only_declared_requirements_installed=True,log_sha256=sha(ROOT/'en-check-01.log')),
        chinese_unit_tests=467,workflow_python_commands=53,github_ci_run=False,
        comparator_tests=9,comparator_tests_log_sha256=sha(ROOT/'comparison-tests-final.log'),
        initial_comparator_harness_error=dict(kind='Missing local check.py compatibility wrapper',
            fixed_before_native_comparison=True,production_sources_changed=False,log_sha256=sha(ROOT/'comparison-tests.log')),
        native_groups=28,page_totals=native['page_totals'],manually_viewed_pages=6,
        package_rebuild_bitwise_identical=True,credentials_used=False,remote_writes=0,
        release_acceptance=False,known_open_quality_issue=summary['known_open_quality_issue']))
    write(DEST/'private-evidence-receipt.json',dict(private_files=len(inventory),private_seal_sha256=private_seal,
        prior_private_files_unchanged=937,prior_private_seal_sha256=sha(PRIOR/'evidence-sha256.json'),
        private_contexts_documents_images_exported=False))
    for name in ['check.py','comparison_helpers.py','test_comparison_helpers.py','prepare.py','run.py','run_ci.py',
            'review_observations.py','word_style_diagnostic.py','export.py','reuse_preparation_integration.py','reuse_preparation_contract.py']:
        cp(ROOT/name,DEST/'checkers'/name)
    public=[dict(path=str(p.relative_to(DEST)),sha256=sha(p)) for p in sorted(DEST.rglob('*')) if p.is_file()]
    write(DEST/'checksums.json',dict(files=public))
    print(json.dumps(dict(passed=True,private_files=len(inventory),private_seal=private_seal,
        public_files=len(public),public_seal=sha(DEST/'checksums.json'))))
if __name__=='__main__':main()
