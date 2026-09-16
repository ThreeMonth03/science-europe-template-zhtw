"""Replay frozen synthetic HTML in a no-network, no-credential worker container."""
import argparse
import json
from pathlib import Path
import subprocess
import shutil
import time
import uuid
from artifact_utils import sha

ROOT = Path(__file__).resolve().parents[1]
IMAGE = 'datastewardshipwizard/document-worker@sha256:5e5c5e1e436feb49fc4cbcd62c2e0ab2785db2141b0fe40d2926906bcfeaebfc'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    p.add_argument('--cases', nargs='+', default=['budget-many-chinese.html'])
    p.add_argument('--cycles', type=int, default=12)
    p.add_argument('--gc', choices=['natural', 'after-each'], default='natural')
    p.add_argument('--probe', choices=['render', 'font-lifetime'], default='render')
    p.add_argument('--save-all', action='store_true')
    p.add_argument('--timeout', type=int, default=600)
    p.add_argument('--image', default=IMAGE); a = p.parse_args()
    assert 1 <= a.cycles <= 30
    assert 1 <= a.timeout <= 1800
    suffix = '.ttf' if a.probe == 'font-lifetime' else '.html'
    assert all(Path(name).name == name and name.endswith(suffix) for name in a.cases)
    sources = {name: sha(a.source/name) for name in a.cases}
    a.output.mkdir(parents=True, exist_ok=False); a.output.chmod(0o777)
    runner = ROOT/'experiments/worker-pdf-stability/replay.py'
    sequence = a.cases*a.cycles; container = 'se-worker-replay-'+uuid.uuid4().hex[:12]
    command = ['docker', 'run', '--name', container, '--network', 'none', '--read-only', '--tmpfs', '/tmp:rw,size=1g',
        '-e', 'XDG_CACHE_HOME=/tmp/cache',
        '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--ulimit', 'core=0', '-i',
        '-v', str(a.source.resolve())+':/sources:ro', '-v', str(runner)+':/replay.py:ro',
        '-v', str(a.output.resolve())+':/out', '--entrypoint', 'python', a.image, '-u', '/replay.py']
    payload = {'sequence': sequence, 'gc_policy': a.gc, 'probe': a.probe, 'save_all': a.save_all}
    for path in (runner, Path(__file__)):
        shutil.copy2(path, a.output/path.name)
    (a.output/'settings.json').write_text(json.dumps(payload, indent=2)+'\n')
    started = time.monotonic()
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    timed_out = False
    try:
        stdout, stderr = process.communicate(json.dumps(payload).encode(), timeout=a.timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        subprocess.run(['docker', 'kill', container], check=True, capture_output=True, timeout=30)
        stdout, stderr = process.communicate(timeout=30)
    result = subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
    (a.output/'stdout.jsonl').write_bytes(result.stdout); (a.output/'stderr.txt').write_bytes(result.stderr)
    state = json.loads(subprocess.check_output(['docker', 'inspect', '--format', '{{json .State}}', container]))
    image_id = subprocess.check_output(['docker', 'inspect', '--format', '{{.Image}}', container], text=True).strip()
    events = [json.loads(line) for line in result.stdout.decode().splitlines() if line.startswith('{')]
    completed = [e for e in events if e['event'] == ('lifetime-complete' if a.probe == 'font-lifetime' else 'render-complete')]
    passed = not timed_out and result.returncode == 0 and len(completed) == len(sequence) and events[-1]['event'] == 'complete'
    report = {'diagnostic_only': True, 'release_acceptance': False, 'completed_without_crash': passed,
        'returncode': result.returncode, 'seconds': round(time.monotonic()-started, 3), 'container_state': state,
        'probe': a.probe, 'timed_out': timed_out, 'timeout_seconds': a.timeout,
        'image': a.image, 'image_id': image_id, 'sequence': sequence, 'completed_iterations': len(completed),
        'gc_policy': a.gc, 'source_sha256': sources, 'runner_sha256': sha(runner), 'checker_sha256': sha(Path(__file__)),
        'artifacts_sha256': {f.name: sha(f) for f in a.output.iterdir() if f.is_file()},
        'limits': ['Frozen HTML exports, not captured PDF-entry HTML or full DSW queue replay',
            'No network, keyring, database, S3, private configuration or host home mount',
            'A clean bounded replay does not establish absence of an intermittent crash']}
    assert not state['Running']
    subprocess.run(['docker', 'rm', container], check=True, capture_output=True)
    report['stopped_probe_container_removed'] = True
    (a.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: report[k] for k in ['completed_without_crash', 'returncode', 'seconds', 'completed_iterations', 'gc_policy']}), flush=True)
    if not passed:
        raise SystemExit(1)


if __name__ == '__main__': main()
