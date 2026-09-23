"""Seal successful local integration evidence; publish only content-free receipts."""
import copy, hashlib, json, os, re, shutil, subprocess
from pathlib import Path
os.umask(0o077)
ROOT=Path(__file__).resolve().parent
ZH=Path('/home/trc/Downloads/science-europe-template-zhtw')
EN=Path('/home/trc/Downloads/science-europe-template')
TOOL=Path('/home/trc/Downloads/dsw-document-template-tool')
PRIOR=Path('/home/trc/.local/share/dsw-word-empty-sections.gFM6aN')
DEST=ZH/'reviews/2026-09-23-word-empty-section-integration'
BUILDS=[Path(Path('/tmp/se-word-integration-build-'+n+'.log').read_text().strip()) for n in ['01','02']]
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
    native,ci,visual=map(read,[ROOT/'checks.json',ROOT/'ci.json',ROOT/'visual-review.json'])
    assert native['passed'] and len(native['rows'])==28
    assert native['page_totals']=={'pdf':130,'word_preview':131}
    assert all(r['passed'] and r['html_bytes_unchanged'] and r['docx_components_unchanged_except_core_timestamps'] for r in native['rows'])
    assert ci['passed'] and len(ci['rows'])==54 and all(r['returncode']==0 for r in ci['rows'])
    assert {r['number'] for r in ci['rows']}==set(range(54))
    for row in ci['rows']:assert sha(ROOT/row['log'])==row['log_sha256']
    assert re.search(r'Ran 472 tests .*?\n\nOK',(ROOT/'ci/00.log').read_text(),re.S)
    english_log=Path('/tmp/se-word-integration-en-check-03.log')
    assert re.search(r'Ran 265 tests .*?\n\nOK',english_log.read_text(),re.S)
    assert 'SUCCESS: The template is valid!' in english_log.read_text()
    assert re.search(r'Ran 9 tests .*?\n\nOK',(ROOT/'comparison-tests.log').read_text(),re.S)
    assert visual['manually_viewed_pages']==sum(len(r['pages']) for r in visual['observations'])==8
    assert read(ROOT/'observation-checks.json')['suspected_answer_separation_rejected']
    assert (DEST/'README.md').is_file()
    manifests=[read(p/'manifest.json') for p in BUILDS]
    for m in manifests:
        assert m['status']=='candidate' and all(not c['dirty'] for c in m['checkouts'].values())
        assert m['source']['version']==m['translation']['version']=='0.3.50'
        assert m['translation_units']==775 and not m['untranslated_units']
    assert manifests[0]['checkouts']==manifests[1]['checkouts']
    assert manifests[0]['translation_tree_sha256']==manifests[1]['translation_tree_sha256']
    for name in ['english.zip','chinese.zip']:
        assert sha(BUILDS[0]/name)==sha(BUILDS[1]/name)==manifests[0]['sha256'][name]==manifests[1]['sha256'][name]
    for name,repo in [('english',EN),('translation',ZH),('tooling',TOOL)]:
        assert subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()==manifests[0]['checkouts'][name]['commit']
    cp(english_log,ROOT/'english-make-check.log')
    for name in ['en-check','en-check-02','en-engine','zh-target','zh-target-02','zh-check-01','build-01','build-02']:
        cp(Path('/tmp/se-word-integration-'+name+'.log'),ROOT/(name+'.log'))
    gates=['word-empty-section-integration.json','word-empty-section-engine-english.json','word-empty-section-engine-chinese.json',
        'reuse-preparation-integration.json','empty-section-integration.json','empty-section-engine.json',
        'submission-flow-integration.json','submission-flow-engine-en.json','submission-flow-engine-zh.json',
        'full-km-followups-integration.json']
    for name in gates:cp(BUILDS[0]/name,ROOT/'build-receipts'/name)
    for index,build in enumerate(BUILDS):cp(build/'manifest.json',ROOT/'build-receipts'/('manifest.json' if index==0 else 'rebuild-manifest.json'))
    cp(EN/'outputs/word-empty-section-integration-engine-01.json',ROOT/'english-source-engine.json')
    cp(ZH/'.github/workflows/pilot-checks.yml',ROOT/'pilot-checks.yml')
    assert sha(ROOT/'pilot-checks.yml')==ci['workflow_sha256']
    for name,repo in [('word_empty_section_contract.py',EN),('word_empty_section_integration.py',ZH)]:cp(repo/'scripts'/name,ROOT/name)
    assert sha(PRIOR/'evidence-sha256.json')==read(ROOT/'manifest.json')['prior_seal']
    previous=read(PRIOR/'evidence-sha256.json')['files']
    assert len(previous)==970 and all(sha(PRIOR/r['path'])==r['sha256'] for r in previous)
    assert {str(p.relative_to(PRIOR)) for p in PRIOR.rglob('*') if p.is_file()}=={r['path'] for r in previous}|{'evidence-sha256.json'}
    inventory=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p)) for p in sorted(ROOT.rglob('*')) if p.is_file()]
    write(ROOT/'evidence-sha256.json',dict(status='Local source integration matches accepted Word prototype',release_acceptance=False,files=inventory))
    seal=sha(ROOT/'evidence-sha256.json')
    summary=copy.deepcopy(native)
    for row in summary['rows']:row['case']=ALIASES.get(row['case'],row['case'])
    summary.update(private_evidence_seal_sha256=seal,private_evidence_files=len(inventory),
        public_summary_is_not_a_replayable_private_fixture=True,comparator_tests=9,
        package_sha256=manifests[0]['sha256'],checker_sha256=sha(ROOT/'comparison_helpers.py'))
    write(DEST/'native/private-parity-summary.json',summary)
    for name in ['visual-review.json','runtime.json','observation-checks.json']:cp(ROOT/name,DEST/'native'/name)
    for index in range(2):cp(ROOT/'build-receipts'/('manifest.json' if index==0 else 'rebuild-manifest.json'),DEST/('build-manifest.json' if index==0 else 'rebuild-manifest.json'))
    for name in gates:cp(ROOT/'build-receipts'/name,DEST/'build'/name)
    cp(ROOT/'english-source-engine.json',DEST/'build/english-source-engine.json')
    public_ci=copy.deepcopy(ci)
    for row in public_ci['rows']:
        row['args']=[a.replace(str(BUILDS[0]),'$SE_BUILD_DIR').replace('../science-europe-template','../english') for a in row['args']]
    write(DEST/'ci.json',public_ci)
    write(DEST/'local-checks.json',dict(passed=True,scope='Local integration parity, not full document-quality acceptance',
        english_make_check=dict(passed=True,unit_tests=265,tdk_verified=True,only_declared_requirements_installed=True,log_sha256=sha(ROOT/'english-make-check.log')),
        chinese_unit_tests=472,workflow_python_commands=54,github_ci_run=False,comparator_tests=9,
        comparator_tests_log_sha256=sha(ROOT/'comparison-tests.log'),native_groups=28,page_totals=native['page_totals'],
        manually_viewed_pages=8,package_rebuild_bitwise_identical=True,translation_file_bytes_unchanged=775,
        initial_harness_failures=[dict(kind='Q1 historical unit test compared current Word assets before projection',log_sha256=sha(ROOT/'en-check.log')),
            dict(kind='New test used wrong archived manifest relative path',log_sha256=sha(ROOT/'zh-target.log'))],
        interrupted_english_rerun=dict(exit_code=143,reason_unconfirmed=True,log_sha256=sha(ROOT/'en-check-02.log'),superseded_by_full_successful_rerun=True),
        credentials_used=False,remote_writes=0,release_acceptance=False,native_ms_word=False))
    write(DEST/'private-evidence-receipt.json',dict(private_files=len(inventory),private_seal_sha256=seal,
        prior_private_files_unchanged=970,prior_private_seal_sha256=sha(PRIOR/'evidence-sha256.json'),private_contexts_documents_images_exported=False))
    for name in ['check.py','comparison_helpers.py','test_comparison_helpers.py','prepare.py','run.py','run_ci.py',
                 'export.py','review_observations.py','word_empty_section_contract.py','word_empty_section_integration.py']:
        cp(ROOT/name,DEST/'checkers'/name)
    public=[dict(path=str(p.relative_to(DEST)),sha256=sha(p)) for p in sorted(DEST.rglob('*')) if p.is_file()]
    write(DEST/'checksums.json',dict(files=public))
    print(json.dumps(dict(passed=True,private_files=len(inventory),private_seal=seal,public_files=len(public),public_seal=sha(DEST/'checksums.json'))))
if __name__=='__main__':main()
