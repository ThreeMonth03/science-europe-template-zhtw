"""Run independent remaining engine checks on the byte-identical second build.

Original checks 27/28 keep running. Every command and acceptance criterion is
unchanged; only scheduling and the equivalent clean output directory differ.
"""
import concurrent.futures,hashlib,json,os,shlex,subprocess,time
import yaml
import run_ci as initial

def main():
    os.umask(0o077);root=initial.ROOT;build=initial.ZH/'outputs/build-mj6lg547'
    manifests=[json.loads((p/'manifest.json').read_text()) for p in [initial.BUILD,build]]
    assert manifests[0]['sha256']==manifests[1]['sha256']
    assert manifests[0]['checkouts']==manifests[1]['checkouts']
    for name in ['english.zip','chinese.zip']:
        assert (build/name).read_bytes()==(initial.BUILD/name).read_bytes()
    import sys
    sys.path.insert(0,str(initial.ZH/'scripts'))
    from submission_flow_integration import check_package
    for language,folder in [('english','en'),('chinese','translated')]:
        check_package(build/(language+'.zip'),build/folder,language,manifests[1]['package_timestamp'])
    workflow=initial.ZH/'.github/workflows/pilot-checks.yml'
    block=next(s['run'] for s in yaml.safe_load(workflow.read_text())['jobs']['build']['steps'] if s.get('name')=='Build a locked candidate and check lifecycle gates')
    commands=[]
    for line in block.splitlines():
        if not line.startswith('../tooling/.venv/bin/python '):continue
        line=line.removesuffix(' &').replace('../tooling/.venv/bin/python',initial.PY).replace('../english','../science-europe-template').replace('$SE_BUILD_DIR',str(build))
        commands.append(shlex.split(line))
    assert len(commands)==50
    logs=root/'ci-remaining';logs.mkdir();start=time.time()
    def run(task):
        number,args=task;begin=time.time();log=logs/f'{number:02d}.log'
        with log.open('x') as f:result=subprocess.run(args,cwd=initial.ZH,stdout=f,stderr=subprocess.STDOUT,timeout=10800)
        row=dict(number=number,args=args[1:],returncode=result.returncode,seconds=round(time.time()-begin,2),
            log='ci-remaining/'+log.name,log_sha256=hashlib.sha256(log.read_bytes()).hexdigest(),
            clean_candidate_manifest_sha256=hashlib.sha256((build/'manifest.json').read_bytes()).hexdigest())
        with (logs/f'{number:02d}.json').open('x') as f:json.dump(row,f,indent=2)
        print(json.dumps(dict(number=number,returncode=result.returncode,seconds=row['seconds'])),flush=True)
        return row
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        rows=list(pool.map(run,enumerate(commands[29:],29)))
    report=dict(passed=all(r['returncode']==0 for r in rows),local_only=True,github_ci_run=False,
        same_package_and_prepared_bytes_verified=True,seconds=round(time.time()-start,2),rows=rows,
        workflow_sha256=hashlib.sha256(workflow.read_bytes()).hexdigest())
    with (root/'ci-remaining.json').open('x') as f:json.dump(report,f,indent=2)
    raise SystemExit(0 if report['passed'] else 1)
if __name__=='__main__':main()
