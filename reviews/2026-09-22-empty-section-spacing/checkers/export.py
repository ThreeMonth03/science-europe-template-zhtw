"""Freeze the private audit and export only content-free public receipts."""
import copy,hashlib,json,os,re,shutil,subprocess
from pathlib import Path
os.umask(0o077)
ROOT=Path(__file__).resolve().parent
ZH=Path('/home/trc/Downloads/science-europe-template-zhtw')
EN=Path('/home/trc/Downloads/science-europe-template')
DEST=ZH/'reviews/2026-09-22-empty-section-spacing'
BUILDS=[ZH/'outputs'/('empty-section-spacing-'+n) for n in ['02','03']]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def write(p,value):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x') as f:f.write(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def cp(a,b):
    assert not b.exists();b.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(a,b)
def main():
    native=read(ROOT/'checks.json');assert native['passed'] and len(native['rows'])==28
    assert not native['regressions'] and not native['release_acceptance']
    engine=read(Path('/tmp/se-empty-sections-engine-02.json'))
    assert engine['passed'] and len(engine['selector_cases'])==63 and len(engine['render_cases'])==28
    logs={
        'english-full-check.log':('/tmp/se-empty-sections-en-full.log',250),
        'chinese-full-check.log':('/tmp/se-empty-sections-zh-full.log',458),
    }
    for target,(source,count) in logs.items():
        assert re.search(r'Ran '+str(count)+r' tests .*?\n\nOK',Path(source).read_text(),re.S)
        cp(Path(source),ROOT/target)
    assert re.search(r'Ran 14 tests .*?\n\nOK',(ROOT/'comparator-tests-02.log').read_text(),re.S)
    for name in ['build-02','build-03','engine-02']:
        cp(Path('/tmp/se-empty-sections-'+name+'.log'),ROOT/(name+'.log'))
    cp(Path('/tmp/se-empty-sections-engine-02.json'),ROOT/'engine.json')
    manifests=[read(p/'manifest.json') for p in BUILDS]
    for m in manifests:
        assert m['status']=='prototype' and not m['source_integrated'] and not m['release_acceptance']
        assert all(not c['dirty'] for c in m['checkouts'].values())
        assert m['checks']==dict(english=396,chinese=396)
        assert m['translation_units']==775 and m['translation_pairs_unchanged']
    for name in ['english.zip','chinese.zip']:
        assert sha(BUILDS[0]/name)==sha(BUILDS[1]/name)==manifests[0]['sha256'][name]==manifests[1]['sha256'][name]
    assert sha(BUILDS[0]/'manifest.json')==read(ROOT/'manifest.json')['build_manifest_sha256']
    for name,repo in [('english',EN),('chinese',ZH)]:
        assert subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()==manifests[0]['checkouts'][name]['commit']
    # Confirm every sealed predecessor file again; importing its code is prohibited.
    prior=Path('/home/trc/.local/share/dsw-flow-integration.jRrEgx')
    assert sha(prior/'evidence-sha256.json')==read(ROOT/'manifest.json')['prior_seal']
    assert all(sha(prior/r['path'])==r['sha256'] for r in read(prior/'evidence-sha256.json')['files'])
    inventory=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p)) for p in sorted(ROOT.rglob('*')) if p.is_file()]
    write(ROOT/'evidence-sha256.json',dict(status='bounded prototype locally verified; not release acceptance',release_acceptance=False,files=inventory))
    summary=copy.deepcopy(native)
    for row in summary['rows']:row['case']={'P19':'REAL-SNAPSHOT-A','P21':'REAL-SNAPSHOT-B'}.get(row['case'],row['case'])
    summary.update(private_evidence_seal_sha256=sha(ROOT/'evidence-sha256.json'),private_evidence_files=len(inventory),
        evidence_contains_private_documents=True,public_summary_is_not_a_replayable_private_fixture=True,
        comparator_tests=14,checker_sha256=sha(ROOT/'check.py'),package_sha256=manifests[0]['sha256'],
        first_comparison_attempt=dict(passed=False,cause='Comparator assumed numbered Word cover; no template failure',
            log_sha256=sha(ROOT/'check-01.log'),checker_sha256=sha(ROOT/'check-attempt-01.py')))
    write(DEST/'native/private-comparison-summary.json',summary)
    cp(ROOT/'visual-review.json',DEST/'native/visual-review.json')
    for i,p in enumerate(BUILDS):cp(p/'manifest.json',DEST/'build'/('manifest.json' if i==0 else 'rebuild-manifest.json'))
    cp(ROOT/'engine.json',DEST/'build/engine.json')
    write(DEST/'build/local-checks.json',dict(passed=True,github_actions_run=False,
        english=dict(unit_tests=250,tdk_verified=True,exit_code=0,only_declared_requirements_installed=True,
            command='make check PYTHON=/tmp/se-flow-en-check.nQ1FzZ/bin/python DSW_TDK=/tmp/se-flow-en-check.nQ1FzZ/bin/dsw-tdk',log_sha256=sha(ROOT/'english-full-check.log')),
        chinese=dict(unit_tests=458,exit_code=0,command='python -m unittest discover -s tests -v',log_sha256=sha(ROOT/'chinese-full-check.log')),
        public_worker_engine=dict(selector_cases=63,render_cases=28,exit_code=0,log_sha256=sha(ROOT/'engine-02.log')),
        private_comparator=dict(tests=14,exit_code=0,log_sha256=sha(ROOT/'comparator-tests-02.log')),
        native_run=dict(exit_code=0,log_sha256=sha(ROOT/'run.log')),
        native_comparison=dict(exit_code=0,log_sha256=sha(ROOT/'check-02.log')),
        older_49_workflow_checks_rerun=False,remote_writes=0,credentials_used=False))
    for name in ['check.py','check-attempt-01.py','comparison_helpers.py','test_comparison_helpers.py','test_boundaries.py','run.py','export.py']:
        cp(ROOT/name,DEST/'checkers'/name)
    public=[dict(path=str(p.relative_to(DEST)),sha256=sha(p)) for p in sorted(DEST.rglob('*')) if p.is_file()]
    write(DEST/'checksums.json',dict(files=public))
    print(json.dumps(dict(passed=True,private_files=len(inventory),private_seal=sha(ROOT/'evidence-sha256.json'),public_files=len(public),public_seal=sha(DEST/'checksums.json'))))
if __name__=='__main__':main()
