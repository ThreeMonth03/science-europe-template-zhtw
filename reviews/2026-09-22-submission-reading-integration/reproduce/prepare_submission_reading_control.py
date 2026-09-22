"""Copy sealed prototype ZIPs unchanged for a same-day native control run."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile
from artifact_utils import sha
from submission_reading_integration import CONTRACT
from prepare_runtime_variant import require_tables_only_sources

ROOT = Path(__file__).resolve().parents[1]


def prepare(source):
    archive = ROOT / CONTRACT['prototype_archive']
    assert sha(archive / 'checksums.json') == CONTRACT['prototype_seal_sha256']
    for name, digest in json.loads((archive / 'checksums.json').read_text()).items():
        assert sha(archive / name) == digest, name
    manifest = json.loads((source / 'manifest.json').read_text())
    assert manifest == json.loads((archive / 'after/manifest.json').read_text())
    members = json.loads((archive / 'provenance/package-members.json').read_text())
    assert subprocess.check_output(['docker', 'inspect', '--format', '{{.Image}}', 'science-europe-pilot-docworker-1'], text=True).strip() == 'sha256:6d3cbcab3294e760a4d92e27bec72d4fb23a0adb2cc1734d981478688741ab11'
    observed = json.loads(subprocess.check_output(['docker', 'exec', 'science-europe-pilot-docworker-1', 'python', '-c',
        'import hashlib,importlib.util,json; from pathlib import Path; names=' + repr(list(manifest['prototype']['observed_worker_sources'])) + '; '
        'print(json.dumps({n:hashlib.sha256(Path(importlib.util.find_spec(n).origin).read_bytes()).hexdigest() for n in names}))'], text=True))
    require_tables_only_sources(observed)
    output = Path(tempfile.mkdtemp(prefix='reading-same-day-control-', dir=ROOT / 'outputs'))
    for language in ['english', 'chinese']:
        path = source / (language + '.zip'); assert sha(path) == manifest['sha256'][path.name]
        with zipfile.ZipFile(path) as z:
            assert {n: hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()} == members[language]
        shutil.copy2(path, output / path.name)
    manifest['same_day_control'] = dict(source_archive=CONTRACT['prototype_archive'], source_seal=CONTRACT['prototype_seal_sha256'],
        reason='Generated date changed across days; regenerate unmodified prototype, never mask or edit document pixels.')
    (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    return output


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--source', type=Path, required=True)
    print(prepare(p.parse_args().source.resolve()))
