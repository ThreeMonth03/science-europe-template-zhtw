"""Run the workflow's unchanged Python check commands against one clean build.

Only independent CLI commands run concurrently. Every exit code is collected;
this is local execution, not a claim about a GitHub-hosted runner.
"""
import concurrent.futures,hashlib,json,os,shlex,subprocess,time
from pathlib import Path
import yaml
os.umask(0o077)
ROOT=Path(__file__).resolve().parent
ZH=Path('/home/trc/Downloads/science-europe-template-zhtw')
PY='/home/trc/Downloads/dsw-document-template-tool/.venv/bin/python'
BUILD=ZH/'outputs/build-v0i7akit'
def main():
    workflow=ZH/'.github/workflows/pilot-checks.yml'
    data=yaml.safe_load(workflow.read_text())
    steps=data['jobs']['build']['steps']
    block=next(s['run'] for s in steps if s.get('name')=='Build a locked candidate and check lifecycle gates')
    commands=[]
    for line in block.splitlines():
        if not line.startswith('../tooling/.venv/bin/python '):continue
        line=line.removesuffix(' &').replace('../tooling/.venv/bin/python',PY).replace('../english','../science-europe-template').replace('$SE_BUILD_DIR',str(BUILD))
        commands.append(shlex.split(line))
    assert len(commands)>=50 and commands[0][1:]==['-m','unittest','discover','-s','tests','-v']
    logs=ROOT/'ci';logs.mkdir();started=time.time()
    def run(task):
        number,args=task;begin=time.time();log=logs/f'{number:02d}.log'
        with log.open('x') as f:
            result=subprocess.run(args,cwd=ZH,stdout=f,stderr=subprocess.STDOUT,timeout=10800)
        row=dict(number=number,args=args[1:],returncode=result.returncode,seconds=round(time.time()-begin,2),log=log.name,
            log_sha256=hashlib.sha256(log.read_bytes()).hexdigest())
        with (logs/f'{number:02d}.json').open('x') as f:json.dump(row,f,indent=2)
        print(json.dumps(dict(number=number,script=args[1],returncode=result.returncode,seconds=row['seconds'])),flush=True)
        return row
    # Unit discovery first; package verification then precedes historical views.
    rows=[run((0,commands[0])),run((1,commands[1]))]
    assert all(r['returncode']==0 for r in rows)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        rows.extend(pool.map(run,enumerate(commands[2:],2)))
    report=dict(local_only=True,github_ci_run=False,passed=all(r['returncode']==0 for r in rows),
        seconds=round(time.time()-started,2),workflow_sha256=hashlib.sha256(workflow.read_bytes()).hexdigest(),
        clean_candidate_manifest_sha256=hashlib.sha256((BUILD/'manifest.json').read_bytes()).hexdigest(),rows=rows)
    with (ROOT/'ci.json').open('x') as f:json.dump(report,f,indent=2)
    raise SystemExit(0 if report['passed'] else 1)
if __name__=='__main__':main()
