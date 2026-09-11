"""Copy exact candidate packages into an explicitly non-release runtime experiment."""
import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads((args.build / 'manifest.json').read_text())
    assert manifest['status'] == 'candidate', 'Use a clean, locked candidate baseline'
    output = Path(tempfile.mkdtemp(prefix='runtime-tables-', dir=ROOT / 'outputs'))
    hashes = {}
    for name in ('english.zip', 'chinese.zip'):
        shutil.copy2(args.build / name, output / name)
        hashes[name] = hashlib.sha256((output / name).read_bytes()).hexdigest()
    image = json.loads(subprocess.check_output(['docker', 'inspect', '--format', '{{json .Image}}', 'science-europe-pilot-docworker-1'], text=True))
    manifest.update(status='runtime-experiment', release_acceptance=False,
                    baseline_build=str(args.build.resolve()), identical_package_sha256=hashes,
                    runtime_variant={'name': 'python-markdown-tables', 'worker_image_id': image,
                                     'dockerfile': 'experiments/markdown-tables/Dockerfile',
                                     'stock_worker': 'datastewardshipwizard/document-worker@sha256:5e5c5e1e436feb49fc4cbcd62c2e0ab2785db2141b0fe40d2926906bcfeaebfc'})
    (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(output)


if __name__ == '__main__':
    main()
