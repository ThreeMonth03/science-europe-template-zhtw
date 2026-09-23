"""Seal finished private evidence and export content-free integration receipts."""
import copy,hashlib,json,os,re,shutil,subprocess
from pathlib import Path
os.umask(0o077)
ROOT=Path(__file__).resolve().parent
ZH=Path('/home/trc/Downloads/science-europe-template-zhtw')
EN=Path('/home/trc/Downloads/science-europe-template')
DEST=ZH/'reviews/2026-09-23-empty-section-integration'
BUILDS=[Path(Path('/tmp/se-section-integration-build-'+n+'.log').read_text().strip()) for n in ['04','05']]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def write(p,value):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x') as f:f.write(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def cp(a,b):
    assert not b.exists();b.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(a,b)
def main():
    native=read(ROOT/'checks.json');ci=read(ROOT/'ci.json')
    assert native['passed'] and len(native['rows'])==28 and ci['passed']
    assert len(ci['rows'])==52 and all(r['returncode']==0 for r in ci['rows'])
    assert re.search(r'Ran 461 tests .*?\n\nOK',(ROOT/'ci/00.log').read_text(),re.S)
    assert re.search(r'Ran 253 tests .*?\n\nOK',Path('/tmp/se-section-integration-en-check-02.log').read_text(),re.S)
    assert re.search(r'Ran 9 tests .*?\n\nOK',(ROOT/'comparator-tests.log').read_text(),re.S)
    assert (DEST/'README.md').is_file()
    manifests=[read(p/'manifest.json') for p in BUILDS]
    for m in manifests:
        assert m['status']=='candidate' and all(not c['dirty'] for c in m['checkouts'].values())
        assert m['source']['version']==m['translation']['version']=='0.3.48'
        assert m['translation_units']==775 and not m['untranslated_units']
    assert manifests[0]['checkouts']==manifests[1]['checkouts']
    for name in ['english.zip','chinese.zip']:
        assert sha(BUILDS[0]/name)==sha(BUILDS[1]/name)==manifests[0]['sha256'][name]==manifests[1]['sha256'][name]
    for name,repo in [('english',EN),('translation',ZH)]:
        assert subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()==manifests[0]['checkouts'][name]['commit']
    # Preserve diagnostic attempts; only fresh final runs supply acceptance.
    for name in ['en-check-01','en-check-02','zh-check-01','legacy-css-02','gate-01',
                 'build-01','build-02','build-03','build-04','build-05','engine-01']:
        cp(Path('/tmp/se-section-integration-'+name+'.log'),ROOT/(name+'.log'))
    drafts=[]
    for number in ['01','02','03']:
        p=Path(Path('/tmp/se-section-integration-build-'+number+'.log').read_text().strip())
        m=read(p/'manifest.json')
        drafts.append(dict(attempt=number,accepted=False,reason='Earlier source/checker lock before final regression fixes',
            manifest_sha256=sha(p/'manifest.json'),checkouts=m['checkouts'],package_sha256={n:m['sha256'][n] for n in ['english.zip','chinese.zip']}))
    write(ROOT/'earlier-builds.json',drafts)
    prior=Path('/home/trc/.local/share/dsw-empty-sections.W74UaS')
    assert sha(prior/'evidence-sha256.json')==read(ROOT/'manifest.json')['prior_seal']
    assert all(sha(prior/r['path'])==r['sha256'] for r in read(prior/'evidence-sha256.json')['files'])
    inventory=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p)) for p in sorted(ROOT.rglob('*')) if p.is_file()]
    write(ROOT/'evidence-sha256.json',dict(status='local source integration verified; not full release acceptance',release_acceptance=False,files=inventory))
    summary=copy.deepcopy(native)
    for row in summary['rows']:row['case']={'P19':'REAL-SNAPSHOT-A','P21':'REAL-SNAPSHOT-B'}.get(row['case'],row['case'])
    summary.update(private_evidence_seal_sha256=sha(ROOT/'evidence-sha256.json'),private_evidence_files=len(inventory),
        public_summary_is_not_a_replayable_private_fixture=True,comparator_tests=9,
        checker_sha256=sha(ROOT/'check.py'),package_sha256={n:manifests[0]['sha256'][n] for n in ['english.zip','chinese.zip']})
    write(DEST/'native/private-parity-summary.json',summary)
    cp(ROOT/'visual-review.json',DEST/'native/visual-review.json')
    for i,build in enumerate(BUILDS):cp(build/'manifest.json',DEST/'build'/('manifest.json' if i==0 else 'rebuild-manifest.json'))
    for name in ['empty-section-integration.json','empty-section-engine.json','submission-flow-integration.json',
                 'submission-flow-engine-en.json','submission-flow-engine-zh.json','full-km-followups-integration.json']:
        cp(BUILDS[0]/name,DEST/'build'/name)
    local=copy.deepcopy(ci)
    for row in local['rows']:
        row['args']=[a.replace(str(BUILDS[0]),'$SE_BUILD_DIR').replace('../science-europe-template','../english') for a in row['args']]
    local['english_clean_make_check']=dict(passed=True,unit_tests=253,tdk_verified=True,exit_code=0,
        only_declared_requirements_installed=True,log_sha256=sha(ROOT/'en-check-02.log'))
    local['chinese_unit_tests']=461
    local['initial_failed_unit_run']=dict(failures=3,log_sha256=sha(ROOT/'en-check-01.log'),
        causes=['Two historical CSS diagnostics append a retired block after current CSS','Version-mutation control accidentally used newly valid 0.3.48'],
        original_failure_retained=True,production_css_changed_after_first_build=False)
    write(DEST/'build/local-checks.json',local)
    write(DEST/'build/earlier-diagnostic-builds.json',drafts)
    for name in ['check.py','comparison_helpers.py','test_comparison_helpers.py','prepare.py','run.py','run_ci.py','export.py']:
        cp(ROOT/name,DEST/'checkers'/name)
    cp(ZH/'scripts/empty_section_spacing_integration.py',DEST/'checkers/empty_section_spacing_integration.py')
    public=[dict(path=str(p.relative_to(DEST)),sha256=sha(p)) for p in sorted(DEST.rglob('*')) if p.is_file()]
    write(DEST/'checksums.json',dict(files=public))
    print(json.dumps(dict(passed=True,private_files=len(inventory),private_seal=sha(ROOT/'evidence-sha256.json'),
        public_files=len(public),public_seal=sha(DEST/'checksums.json'))))
if __name__=='__main__':main()
