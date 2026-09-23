"""Isolated native execution; original snapshots and prototype remain read-only."""
import concurrent.futures,importlib.util,itertools,json,os,subprocess
from pathlib import Path
os.umask(0o077)
ROOT=Path(__file__).resolve().parent
IMAGE='sha256:6d3cbcab3294e760a4d92e27bec72d4fb23a0adb2cc1734d981478688741ab11'
OFFICE='sha256:d71ab8c13b6bd47c7bc81195082005dfb17eaa75e8b1fadd347a64ee66ed98d5'
def run(case,language,profile):
    root=ROOT/'candidate';target=root/'renders'/f'{case}-{language}-{profile}';target.mkdir(parents=True)
    command=['docker','run','--rm','--network','none','--log-driver','none','--cap-drop','ALL',
        '--security-opt','no-new-privileges','--user','1000:1000',
        '-e','PYTHONPATH=/home/user/.local/lib/python3.13/site-packages','-e','XDG_CACHE_HOME=/tmp/private-cache',
        '--entrypoint','python','-v',str(root)+':/audit','-v',str(root/'packages')+':/packages:ro',
        IMAGE,'/audit/offline_worker.py','--case',case,'--language',language,'--profile',profile]
    with (target/'container.log').open('x') as f:
        result=subprocess.run(command,stdout=f,stderr=subprocess.STDOUT,timeout=600)
    return dict(case=case,language=language,profile=profile,passed=result.returncode==0)
def main():
    assert subprocess.check_output(['docker','image','inspect','gotenberg/gotenberg:8','--format','{{.Id}}'],text=True).strip()==OFFICE
    manifest=json.loads((ROOT/'manifest.json').read_text());rows=[]
    tasks=list(itertools.product(manifest['contexts'],['en','zh-Hant'],['review','submission']))
    path=ROOT/'candidate/render_word_previews.py'
    spec=importlib.util.spec_from_file_location('native_office',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    priority=[('MISSING','zh-Hant','submission'),('POSITIVE','zh-Hant','submission'),('NEGATIVE','zh-Hant','submission'),('LONG','zh-Hant','submission')]
    tasks.sort(key=lambda t:priority.index(t) if t in priority else len(priority))
    office_tasks=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as office:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            futures=[pool.submit(run,*task) for task in tasks]
            for future in concurrent.futures.as_completed(futures):
                row=future.result();rows.append(row);print(json.dumps(row),flush=True)
                if row['passed']:
                    folder=ROOT/'candidate/renders'/f"{row['case']}-{row['language']}-{row['profile']}"
                    office_tasks.append(office.submit(module.run,folder))
        previews=[future.result() for future in office_tasks]
    (ROOT/'renders.json').write_text(json.dumps(rows,indent=2)+'\n')
    assert len(rows)==28 and all(r['passed'] for r in rows)
    (ROOT/'previews.json').write_text(json.dumps(previews,indent=2)+'\n')
    assert len(previews)==28 and all(r['passed'] for r in previews)
    (ROOT/'runtime.json').write_text(json.dumps(dict(image=IMAGE,office=OFFICE,native_ms_word=False),indent=2)+'\n')
    print(json.dumps(dict(passed=True,native_groups=28,word_previews=28)),flush=True)
if __name__=='__main__':main()
