"""Bind every unchanged workflow check to its successful local process receipt."""
import hashlib,json,shlex
import yaml
import run_ci as initial

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def main():
    root=initial.ROOT;second=initial.ZH/'outputs/build-mj6lg547'
    initial_manifest=read(initial.BUILD/'manifest.json');second_manifest=read(second/'manifest.json')
    assert initial_manifest['sha256']==second_manifest['sha256']
    assert initial_manifest['checkouts']==second_manifest['checkouts']
    assert all(not r['dirty'] for r in initial_manifest['checkouts'].values())
    for name in ['english.zip','chinese.zip']:
        assert sha(initial.BUILD/name)==sha(second/name)==initial_manifest['sha256'][name]
    workflow=initial.ZH/'.github/workflows/pilot-checks.yml'
    block=next(s['run'] for s in yaml.safe_load(workflow.read_text())['jobs']['build']['steps'] if s.get('name')=='Build a locked candidate and check lifecycle gates')
    commands=[line.removesuffix(' &') for line in block.splitlines() if line.startswith('../tooling/.venv/bin/python ')]
    assert len(commands)==50
    rows=[]
    for number,line in enumerate(commands):
        directory=root/('ci' if number<29 else 'ci-remaining')
        build=initial.BUILD if number<29 else second
        row=read(directory/f'{number:02d}.json')
        expected=shlex.split(line.replace('../tooling/.venv/bin/python',initial.PY)
            .replace('../english','../science-europe-template').replace('$SE_BUILD_DIR',str(build)))[1:]
        assert row['number']==number and row['args']==expected and row['returncode']==0
        assert sha(directory/f'{number:02d}.log')==row['log_sha256']
        row['log']=str((directory/f'{number:02d}.log').relative_to(root))
        row['clean_candidate_manifest_sha256']=sha(build/'manifest.json')
        rows.append(row)
    remaining=read(root/'ci-remaining.json');assert remaining['passed']
    assert remaining['same_package_and_prepared_bytes_verified']
    assert remaining['workflow_sha256']==sha(workflow)
    state=read(root/'scheduler-final-state.json')
    assert state['primary_required_results_complete_before_stop'] and state['tracked_processes_finished']
    cleanup=read(root/'container-cleanup.json')
    assert cleanup['duplicate_container_cleanup_confirmed'] and cleanup['remaining_matching_active_workers']==0
    report=dict(passed=True,local_only=True,github_ci_run=False,workflow_sha256=sha(workflow),
        equivalent_clean_builds_verified=True,clean_candidate_manifest_sha256=[sha(p/'manifest.json') for p in [initial.BUILD,second]],
        orchestration=dict(primary_indices=[0,28],parallel_indices=[29,49],parallel_workers=4,
            acceptance_commands_and_criteria_unchanged=True,original_scheduler=state['original_scheduler'],
            duplicate_cleanup_initial_wait_expired=state['initial_cleanup_wait_expired'],
            duplicate_cleanup_finally_confirmed=state['tracked_processes_finished'],
            duplicate_container_exit_separately_confirmed=True),rows=rows)
    with (root/'ci-combined.json').open('x') as f:json.dump(report,f,indent=2)
    print(json.dumps(dict(passed=True,python_commands=len(rows),candidate_and_engine_checks=len(rows)-1)))
if __name__=='__main__':main()
