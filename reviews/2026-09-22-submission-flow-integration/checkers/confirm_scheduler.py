"""Confirm delayed duplicate-worker cleanup without replacing the timeout receipt."""
import hashlib,json
from pathlib import Path
import run_ci as initial

def main():
    source=initial.ROOT/'scheduler-state.json';state=json.loads(source.read_text())
    for pid in state['stopped_processes']:
        path=Path('/proc')/str(pid)/'stat'
        assert not path.exists() or path.read_text().split(') ',1)[1][0]=='Z'
    state.update(tracked_processes_finished=True,initial_cleanup_wait_seconds=15,
        initial_cleanup_wait_expired=True,original_orchestrator_exit_code=143,
        prior_timeout_receipt_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
    with (initial.ROOT/'scheduler-final-state.json').open('x') as f:json.dump(state,f,indent=2)
    print(json.dumps(dict(tracked_processes_finished=True,prior_timeout_retained=True,processes=len(state['stopped_processes']))))
if __name__=='__main__':main()
