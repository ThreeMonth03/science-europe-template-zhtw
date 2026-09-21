"""Restore and stop only the completed, explicitly named synthetic pilot."""
import argparse
import json
import os
from pathlib import Path
import subprocess

SERVICES = ['science-europe-pilot-' + name + '-1' for name in ['docworker', 'server', 'minio', 'postgres']]
STOCK = 'sha256:5e5c5e1e436feb49fc4cbcd62c2e0ab2785db2141b0fe40d2926906bcfeaebfc'


def state():
    rows = []
    for name in SERVICES:
        value = json.loads(subprocess.check_output(['docker', 'inspect', name]))[0]
        assert value['Config']['Labels']['com.docker.compose.project'] == 'science-europe-pilot'
        rows.append({'name': name, 'image': value['Image'], 'command': value['Config']['Cmd'],
                     'status': value['State']['Status'], 'exit_code': value['State']['ExitCode'],
                     'oom_killed': value['State']['OOMKilled'], 'restart_count': value['RestartCount']})
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['before', 'after', 'compose', 'output']:
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    assert not a.output.exists()
    cleanups = [json.loads((root / 'owned-test-template-cleanup.json').read_text()) for root in [a.before, a.after]]
    assert all(c['run_completed_successfully'] and len(c['deleted']) == 2 for c in cleanups)
    assert len({r['uuid'] for c in cleanups for r in c['deleted']}) == 4
    initial = state()
    assert initial[0]['command'] == ['python', '-u', '/capture.py']
    report = {'before': initial, 'deleted_owned_templates': 4, 'production_touched': False,
              'template_zip_backups_retained': True}
    env = dict(os.environ)
    for key in ['DSW_CI_POSTGRES_USER', 'DSW_CI_POSTGRES_PASSWORD', 'DSW_CI_MINIO_ROOT_USER', 'DSW_CI_MINIO_ROOT_PASSWORD']:
        env[key] = 'unused-worker-only-interpolation'
    subprocess.run(['docker', 'compose', '-p', 'science-europe-pilot', '-f', str(a.compose),
                    'up', '-d', '--no-deps', 'docworker'], env=env, check=True)
    restored = state()[0]
    assert restored['image'] == STOCK and restored['command'] == ['dsw-document-worker', 'run']
    report['stock_worker_restored'] = True
    report['restored_worker'] = restored
    subprocess.run(['docker', 'stop', '--time', '10', *SERVICES], check=True)
    report['after'] = state()
    assert all(row['status'] == 'exited' for row in report['after'])
    a.output.write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
