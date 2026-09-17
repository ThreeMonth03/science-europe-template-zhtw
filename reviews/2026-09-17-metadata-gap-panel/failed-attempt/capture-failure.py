import hashlib
import json
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
target = root / 'runtime-failure.json'
assert not target.exists()
report = json.loads((root / 'missing-info-render-report.json').read_text())
assert not report['all_renders_succeeded'] and len(report['renders']) == 18
assert report['renders'][-1]['rendered'] is False
worker = json.loads(subprocess.check_output(['docker', 'inspect', '--format', '{{json .State}}', 'science-europe-pilot-docworker-1']))
assert worker['Status'] == 'exited' and worker['ExitCode'] == 2
worker_log = subprocess.check_output(['docker', 'logs', '--since', '2026-09-17T08:00:57Z', '--until', '2026-09-17T08:04:28Z', 'science-europe-pilot-docworker-1'], stderr=subprocess.STDOUT, text=True)
queue = [line for line in worker_log.splitlines() if any(text in line for text in ['Waiting for notifications', 'Fetched 0 persistent commands', 'Nothing received in this cycle', 'Notification received:', 'Retrieved persistent command', 'InFailedSqlTransaction', 'record finalized'])]
postgres = subprocess.check_output(['docker', 'logs', '--since', '2026-09-17T08:04:12Z', '--until', '2026-09-17T08:04:14Z', 'science-europe-pilot-postgres-1'], stderr=subprocess.STDOUT, text=True)
deadlock = [line for line in postgres.splitlines() if any(text in line for text in ['deadlock detected', 'waits for ShareLock', 'Process 34:', 'Process 899:'])]
assert any('deadlock detected' in line for line in deadlock)
before_source = subprocess.check_output(['git', 'show', 'ac8d198:scripts/render.py'])
result = dict(passed=False, release_acceptance=False, failed_render=report['renders'][-1], successful_renders=17,
    queue_log_excerpt=queue, database_deadlock_excerpt=deadlock, worker_end_state=worker,
    original_timeout_seconds=180, retry_timeout_seconds=600,
    original_render_runner_sha256=hashlib.sha256(before_source).hexdigest(),
    render_report_sha256=sha(root / 'missing-info-render-report.json'),
    render_error_log_sha256=sha(root / 'render-metadata-private-text-chinese-docx.log'),
    package_sha256=report['package_sha256'],
    interpretation='Observed delayed queue retrieval and client timeout cleanup deadlocked on document finalization. Why the notification fetch saw no work is not established. Longer client wait is only a harness mitigation.',
    cleanup='Two own templates deleted only after zero-reference checks; files and ZIP backups retained.')
target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(dict(recorded=str(target), successful_renders=17, failed_renders=1)))
