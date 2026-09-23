"""Seal the final prototype separately from its rejected first native attempt."""
import copy,hashlib,json,re,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
ZH=Path('/home/trc/Downloads/science-europe-template-zhtw')
EN=Path('/home/trc/Downloads/science-europe-template')
PRIOR=Path('/home/trc/.local/share/dsw-preparation-integration.ZTpuU9')
FAILED=Path('/home/trc/.local/share/dsw-word-empty-sections.lbeV2Q')
DEST=ZH/'reviews/2026-09-23-word-empty-section-spacing'
BUILDS=[ZH/'outputs'/('word-empty-section-prototype-'+n) for n in ['03','04']]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def write(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
def cp(a,b):
    assert not b.exists();b.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(a,b)
def verify(root,seal,expected):
    assert sha(root/'evidence-sha256.json')==seal
    rows=read(root/'evidence-sha256.json')['files'];assert len(rows)==expected
    assert all(sha(root/r['path'])==r['sha256'] for r in rows)
    assert {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}=={r['path'] for r in rows}|{'evidence-sha256.json'}
def main():
    assert not (ROOT/'evidence-sha256.json').exists()
    checks=read(ROOT/'checks.json');visual=read(ROOT/'visual-review.json')
    assert checks['passed'] and len(checks['rows'])==28 and not checks['source_integrated']
    assert checks['page_totals']['pdf']=={'before':130,'after':130}
    assert checks['page_totals']['word_preview']['before']==133
    assert visual['manually_viewed_pages']==sum(len(r['pages']) for r in visual['rows'])==9
    for name,total in [('english',262),('chinese',469)]:
        source=Path('/tmp/se-word-empty-sections-'+('en' if name=='english' else 'zh')+'-check-02.log')
        assert re.search(r'Ran '+str(total)+r' tests .*?\n\nOK',source.read_text(),re.S)
        cp(source,ROOT/(name+'-unit-check.log'))
    assert re.search(r'Ran 9 tests .*?\n\nOK',(ROOT/'comparison-tests.log').read_text(),re.S)
    for name in ['english-engine','english-package-engine','chinese-package-engine']:
        report=read(ROOT/(name+'.json'));assert report['passed'] and len(report['rows'])==121 and all(r['passed'] for r in report['rows'])
    manifests=[read(p/'manifest.json') for p in BUILDS]
    for m in manifests:
        assert m['status']=='prototype' and not m['source_integrated'] and all(not v['dirty'] for v in m['checkouts'].values())
        assert m['translation_units']==775 and m['translation_pairs_and_file_bytes_unchanged']
    assert manifests[0]==manifests[1]
    for name in ['english.zip','chinese.zip']:
        assert sha(BUILDS[0]/name)==sha(BUILDS[1]/name)==manifests[0]['sha256'][name]
    for name,repo in [('english',EN),('chinese',ZH)]:
        assert subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()==manifests[0]['checkouts'][name]['commit']
    verify(PRIOR,read(ROOT/'manifest.json')['prior_seal'],1037)
    verify(FAILED,'a8e286544c40005674b41f4d392c4373ac1ee5a3b15198803254ab9feff110c2',923)
    for i,build in enumerate(BUILDS):cp(build/'manifest.json',ROOT/('build-manifest.json' if i==0 else 'rebuild-manifest.json'))
    cp(FAILED/'failure-summary.json',ROOT/'failed-attempt-summary.json')
    for label,repo in [('english',EN),('chinese',ZH)]:
        for p in (repo/'experiments/word-empty-section-spacing').iterdir():
            if p.is_file():cp(p,ROOT/'recipes'/label/p.name)
    cp(EN/'.github/workflows/quality.yml',ROOT/'english-quality-workflow.yml')
    inventory=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p)) for p in sorted(ROOT.rglob('*')) if p.is_file()]
    write(ROOT/'evidence-sha256.json',dict(status='bounded prototype target and native regressions passed; not integrated or released',files=inventory))
    private_seal=sha(ROOT/'evidence-sha256.json')
    summary=copy.deepcopy(checks)
    for row in summary['rows']:row['case']={'P19':'REAL-SNAPSHOT-A','P21':'REAL-SNAPSHOT-B'}.get(row['case'],row['case'])
    summary.update(private_evidence_seal_sha256=private_seal,private_evidence_files=len(inventory),
        public_summary_is_not_a_replayable_private_fixture=True,package_sha256=manifests[0]['sha256'])
    write(DEST/'native/checks.json',summary)
    for name in ['visual-review.json','runtime.json']:cp(ROOT/name,DEST/'native'/name)
    for name in ['build-manifest.json','rebuild-manifest.json']:cp(ROOT/name,DEST/name)
    for name in ['english-engine.json','english-package-engine.json','chinese-package-engine.json']:cp(ROOT/name,DEST/'engine'/name)
    cp(ROOT/'spacing-sweep.json',DEST/'diagnostics/spacing-sweep.json')
    cp(ROOT/'failed-attempt-summary.json',DEST/'diagnostics/failed-attempt-summary.json')
    write(DEST/'local-checks.json',dict(passed=True,prototype_only=True,source_integrated=False,release_acceptance=False,
        english_tests=262,english_tdk_verify=True,english_unit_log_sha256=sha(ROOT/'english-unit-check.log'),
        chinese_tests=469,chinese_unit_log_sha256=sha(ROOT/'chinese-unit-check.log'),
        comparator_tests=9,comparator_log_sha256=sha(ROOT/'comparison-tests.log'),
        new_english_ci_scope_cases=121,package_scope_cases=dict(english=121,chinese=121),
        github_actions_run=False,all_53_historical_workflow_commands_rerun=False,
        two_clean_builds_bitwise_equal=True,native_groups=28,page_totals=checks['page_totals'],
        manual_pages=9,credentials_used=False,remote_writes=0))
    write(DEST/'private-evidence-receipt.json',dict(private_files=len(inventory),private_seal_sha256=private_seal,
        prior_files_unchanged=1037,prior_seal_sha256=sha(PRIOR/'evidence-sha256.json'),
        failed_attempt_files_unchanged=923,failed_attempt_seal_sha256=sha(FAILED/'evidence-sha256.json'),
        private_contexts_documents_images_exported=False))
    for name in ['check.py','test_check.py','comparison_helpers.py','prepare.py','run.py','spacing_sweep.py','export.py']:
        cp(ROOT/name,DEST/'checkers'/name)
    public=[dict(path=str(p.relative_to(DEST)),sha256=sha(p)) for p in sorted(DEST.rglob('*')) if p.is_file()]
    write(DEST/'checksums.json',dict(files=public))
    print(json.dumps(dict(passed=True,private_files=len(inventory),private_seal=private_seal,public_files=len(public),public_seal=sha(DEST/'checksums.json'))))
if __name__=='__main__':main()
