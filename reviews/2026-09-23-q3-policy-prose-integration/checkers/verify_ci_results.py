"""Retain the failed workflow and verify the complete corrected unit-suite rerun."""
import hashlib,json,re,shlex
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parent
ZH=Path('/home/trc/Downloads/science-europe-template-zhtw')
PY='/home/trc/Downloads/dsw-document-template-tool/.venv/bin/python'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    report=read(ROOT/'ci.json');assert not report['passed'] and len(report['rows'])==55
    workflow=ZH/'.github/workflows/pilot-checks.yml';assert sha(workflow)==report['workflow_sha256']
    build=Path(Path('/tmp/se-q3-integration-build-03.log').read_text().strip())
    assert sha(build/'manifest.json')==report['clean_candidate_manifest_sha256']
    block=next(s['run'] for s in yaml.safe_load(workflow.read_text())['jobs']['build']['steps'] if s.get('name')=='Build a locked candidate and check lifecycle gates')
    expected=[]
    for line in block.splitlines():
        if not line.startswith('../tooling/.venv/bin/python '):continue
        line=line.removesuffix(' &').replace('../tooling/.venv/bin/python',PY).replace('../english','../science-europe-template').replace('$SE_BUILD_DIR',str(build))
        expected.append(shlex.split(line)[1:])
    assert len(expected)==55
    for i,row in enumerate(report['rows']):
        assert row['number']==i and row['returncode']==(1 if i==0 else 0) and row['args']==expected[i]
        assert sha(ROOT/row['log'])==row['log_sha256']
        assert read(ROOT/'ci'/f'{i:02d}.json')==row
    assert read(ROOT/'ci-exit.json')['child_exit_code']==1
    failed=(ROOT/'ci/00.log').read_text()
    assert re.search(r'Ran 481 tests .*?\n\nFAILED \(failures=1\)',failed,re.S)
    assert 'FAIL: test_exact_sealed_baseline_and_separate_recipe_lock' in failed
    assert read(ROOT/'zh-final-exit.json')['child_exit_code']==0
    assert re.search(r'Ran 481 tests .*?\n\nOK',(ROOT/'zh-final.log').read_text(),re.S)
    result=dict(passed=True,effective_workflow_checks_passed=55,unchanged_non_unit_commands_passed=54,
        original_workflow_passed=False,original_driver_exit_code=1,completed_driver_report_sha256=sha(ROOT/'ci.json'),
        entire_chinese_unit_suite_rerun=True,chinese_unit_tests=481,chinese_rerun_exit_code=0,
        chinese_rerun_log_sha256=sha(ROOT/'zh-final.log'),full_workflow_rerun_after_chinese_test_fix=False,
        final_package_equivalence_required=True,
        explanation='Original workflow failure is retained. The sole failed old-version test was corrected, then the entire 481-test Chinese suite was rerun. All 54 other commands succeeded; a separate exact tests-only diff and package-equivalence proof binds them to the final candidate.')
    with (ROOT/'ci-result-verification.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result))
if __name__=='__main__':main()
