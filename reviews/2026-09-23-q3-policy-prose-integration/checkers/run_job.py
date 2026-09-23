"""Record explicit child exit status for long local validation processes."""
import argparse,json,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('name');parser.add_argument('command',nargs=argparse.REMAINDER);args=parser.parse_args()
    assert args.name.replace('-','').isalnum() and args.command
    started=time.monotonic()
    with (ROOT/(args.name+'.log')).open('x') as log:
        child=subprocess.Popen(args.command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        while True:
            try:code=child.wait(timeout=30);break
            except subprocess.TimeoutExpired:print(json.dumps(dict(job=args.name,running=True,seconds=round(time.monotonic()-started))),flush=True)
    report=dict(job=args.name,child_exit_code=code,seconds=round(time.monotonic()-started,2),passed=code==0)
    with (ROOT/(args.name+'-exit.json')).open('x') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps(report),flush=True)
    raise SystemExit(code)
if __name__=='__main__':main()
