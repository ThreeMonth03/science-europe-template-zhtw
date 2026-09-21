"""Restore the worker and stop only this completed two-template native trial."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'experiments/mixed-budget-header'))
from finish import state, STOCK, SERVICES


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['build', 'compose', 'output']: p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args(); assert not a.output.exists()
    cleanup = json.loads((a.build / 'owned-test-template-cleanup.json').read_text())
    assert cleanup['run_completed_successfully'] and len(cleanup['deleted']) == 2
    assert cleanup['project_references'] == cleanup['document_references'] == 0
    initial = state()
    assert initial[0]['command'] == ['dsw-document-worker', 'run']
    assert initial[0]['image'] == 'sha256:6d3cbcab3294e760a4d92e27bec72d4fb23a0adb2cc1734d981478688741ab11'
    report = dict(before=initial, deleted_owned_templates=2, production_touched=False,
                  template_zip_backups_retained=True, capture_observer_attached=False)
    env = dict(os.environ)
    for key in ['DSW_CI_POSTGRES_USER', 'DSW_CI_POSTGRES_PASSWORD', 'DSW_CI_MINIO_ROOT_USER', 'DSW_CI_MINIO_ROOT_PASSWORD']:
        env[key] = 'unused-worker-only-interpolation'
    subprocess.run(['docker', 'compose', '-p', 'science-europe-pilot', '-f', str(a.compose),
                    'up', '-d', '--no-deps', 'docworker'], env=env, check=True)
    restored = state()[0]
    assert restored['image'] == STOCK and restored['command'] == ['dsw-document-worker', 'run']
    report.update(stock_worker_restored=True, restored_worker=restored)
    subprocess.run(['docker', 'stop', '--timeout', '10', *SERVICES], check=True)
    report['after'] = state(); assert all(r['status'] == 'exited' for r in report['after'])
    a.output.write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__': main()
