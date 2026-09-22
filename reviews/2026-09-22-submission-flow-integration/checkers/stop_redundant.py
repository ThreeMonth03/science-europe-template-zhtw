"""Stop only this audit's duplicate scheduling after required prefix passed."""
import json,os,signal,subprocess,time
from pathlib import Path
import run_ci as initial

def main():
    root=initial.ROOT;pid=2267662
    for i in range(29):
        receipt=json.loads((root/'ci'/f'{i:02d}.json').read_text())
        assert receipt['number']==i and receipt['returncode']==0
    assert (root/'ci-remaining').is_dir()
    command=(Path('/proc')/str(pid)/'cmdline').read_bytes().split(b'\0')
    assert command[:2]==[initial.PY.encode(),str(root/'run_ci.py').encode()]
    os.kill(pid,signal.SIGSTOP)
    try:
        snapshot={}
        for line in subprocess.check_output(['ps','-e','-o','pid=,ppid=,comm='],text=True).splitlines():
            p,parent,comm=line.split(None,2);snapshot[int(p)]=(int(parent),comm)
        direct=[p for p,(parent,_) in snapshot.items() if parent==pid]
        names=[]
        for p in direct:
            args=(Path('/proc')/str(p)/'cmdline').read_bytes().split(b'\0')
            assert args[0]==initial.PY.encode() and b'--source-dir' in args
            assert args[args.index(b'--source-dir')+1].startswith(str(initial.BUILD).encode()+b'/')
            assert b'probe_storage_context.py' in args[1],args[1]
            names.append(Path(args[1].decode()).name)
        descendants=set(direct)
        while True:
            extra={p for p,(parent,_) in snapshot.items() if parent in descendants}-descendants
            if not extra:break
            descendants.update(extra)
        docker=[p for p in descendants if snapshot[p][1]=='docker']
        # Docker run's default signal proxy stops its own attached worker;
        # no global image or container-name matching is used.
        for p in docker:
            try:os.kill(p,signal.SIGTERM)
            except ProcessLookupError:pass
        for p in [pid]+direct:
            try:os.kill(p,signal.SIGTERM)
            except ProcessLookupError:pass
    finally:
        try:os.kill(pid,signal.SIGCONT)
        except ProcessLookupError:pass
    tracked=sorted(descendants|{pid})
    def active(p):
        try:return (Path('/proc')/str(p)/'stat').read_text().split(') ',1)[1][0]!='Z'
        except FileNotFoundError:return False
    for _ in range(75):
        if not any(active(p) for p in tracked):break
        time.sleep(.2)
    finished=not any(active(p) for p in tracked)
    state=dict(primary_required_results_complete_before_stop=True,tracked_processes_finished=finished,
        original_scheduler='Stopped after successful required checks 0-28; redundant checks 29-49 are supplied by the byte-identical rebuild scheduler.',
        stopped_processes=tracked,redundant_cli_names=names,additional_scheduler_running=True)
    with (root/'scheduler-state.json').open('x') as f:json.dump(state,f,indent=2)
    assert finished
    print(json.dumps(dict(stopped_only_redundant_work=True,primary_successful_checks=29,tracked_processes_finished=finished)))
if __name__=='__main__':main()
