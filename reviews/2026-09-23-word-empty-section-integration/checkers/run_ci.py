"""Execute every Python check in the committed workflow with unchanged arguments.

Only scheduling differs: validate the package first, then independent checks in
four slots including a fresh full Chinese unit run. Every result is collected.
"""
import concurrent.futures,hashlib,json,os,shlex,subprocess,time
from pathlib import Path
import yaml
os.umask(0o077)
ROOT=Path(__file__).resolve().parent
ZH=Path('/home/trc/Downloads/science-europe-template-zhtw')
PY='/home/trc/Downloads/dsw-document-template-tool/.venv/bin/python'
BUILD=Path(Path('/tmp/se-word-integration-build-01.log').read_text().strip())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    manifest=json.loads((BUILD/'manifest.json').read_text())
    assert manifest['status']=='candidate' and all(not r['dirty'] for r in manifest['checkouts'].values())
    workflow=ZH/'.github/workflows/pilot-checks.yml'
    block=next(s['run'] for s in yaml.safe_load(workflow.read_text())['jobs']['build']['steps'] if s.get('name')=='Build a locked candidate and check lifecycle gates')
    commands=[]
    for line in block.splitlines():
        if not line.startswith('../tooling/.venv/bin/python '):continue
        line=line.removesuffix(' &').replace('../tooling/.venv/bin/python',PY).replace('../english','../science-europe-template').replace('$SE_BUILD_DIR',str(BUILD))
        commands.append(shlex.split(line))
    assert len(commands)==54 and commands[1][1]=='scripts/word_empty_section_integration.py'
    logs=ROOT/'ci';logs.mkdir();start=time.time()
    def run(task):
        number,args=task;begin=time.time();log=logs/f'{number:02d}.log'
        with log.open('x') as f:
            try:code=subprocess.run(args,cwd=ZH,stdout=f,stderr=subprocess.STDOUT,timeout=10800).returncode
            except subprocess.TimeoutExpired:code=124
        row=dict(number=number,args=args[1:],returncode=code,seconds=round(time.time()-begin,2),log='ci/'+log.name,log_sha256=sha(log))
        with (logs/f'{number:02d}.json').open('x') as f:json.dump(row,f,indent=2)
        print(json.dumps(dict(number=number,script=args[1],returncode=code,seconds=row['seconds'])),flush=True)
        return row
    rows=[run((1,commands[1]))];assert rows[0]['returncode']==0
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        rows.extend(pool.map(run,[(i,args) for i,args in enumerate(commands) if i!=1]))
    report=dict(passed=all(r['returncode']==0 for r in rows),local_only=True,github_ci_run=False,
        workflow_sha256=sha(workflow),clean_candidate_manifest_sha256=sha(BUILD/'manifest.json'),
        seconds=round(time.time()-start,2),rows=sorted(rows,key=lambda r:r['number']))
    with (ROOT/'ci.json').open('x') as f:json.dump(report,f,indent=2)
    raise SystemExit(0 if report['passed'] else 1)
if __name__=='__main__':main()
