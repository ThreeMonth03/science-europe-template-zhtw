"""Archive only the explicitly selected synthetic, isolated diagnostics."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
from artifact_utils import sha

ROOT = Path(__file__).resolve().parents[1]
RUNS = ['worker-replay-budget-natural', 'worker-replay-budget-gc',
    'worker-lifetime-stock', 'worker-lifetime-patched', 'worker-mixed-baseline', 'worker-mixed-patched']


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--font-source', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    comparison_path = ROOT/'outputs/worker-mixed-comparison.json'
    comparison = json.loads(comparison_path.read_text())
    assert comparison['selected_checks_passed'] is True
    args.output.mkdir(parents=True, exist_ok=False)
    sources = {}
    for name in RUNS:
        folder = ROOT/'outputs'/name
        report = json.loads((folder/'report.json').read_text())
        for file, expected in report['artifacts_sha256'].items():
            assert Path(file).name == file and sha(folder/file) == expected
        for file, expected in report['source_sha256'].items():
            base = args.font_source if file.endswith('.ttf') else args.source/'renders'
            assert Path(file).name == file and sha(base/file) == expected
            sources[file] = {'sha256': expected, 'path': base/file}
        shutil.copytree(folder, args.output/name)
    shutil.copy2(comparison_path, args.output/'comparison.json')
    # One stream with a 32 MiB dictionary deduplicates the same embedded font in
    # fourteen HTML documents. Only explicit synthetic basenames enter the tar.
    with tarfile.open(args.output/'synthetic-inputs.tar.xz', 'w:xz', preset=8) as bundle:
        for name, data in sorted(sources.items()):
            bundle.add(data['path'], arcname=name, recursive=False)
        bundle.add(args.font_source/'OFL.txt', arcname='OFL.txt', recursive=False)
    incident = args.output/'historical-incident'; incident.mkdir()
    for name in ['worker-exit-139.json', 'worker-recovery.json', 'runtime-restoration.json', 'manifest.json']:
        shutil.copy2(args.source/name, incident/name)
    scripts = args.output/'reproduce'; scripts.mkdir()
    for name in ['collect_worker_stability_review.py', 'probe_worker_pdf_lifecycle.py', 'compare_worker_replays.py',
                 'prepare_runtime_variant.py', 'artifact_utils.py']:
        shutil.copy2(ROOT/'scripts'/name, scripts/name)
    shutil.copytree(ROOT/'experiments/worker-pdf-stability', args.output/'experiment',
                    ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copy2(ROOT/'experiments/markdown-tables/patch_worker.py', scripts/'patch_worker.py')
    names = ['science-europe-pilot-'+name+'-1' for name in ['docworker', 'server', 'postgres', 'minio']]
    states = [json.loads(line) for line in subprocess.check_output(['docker', 'inspect', '--format',
        '{"name":{{json .Name}},"state":{{json .State.Status}},"image":{{json .Image}}}', *names], text=True).splitlines()]
    assert all(state['state'] == 'exited' for state in states)
    assert states[0]['image'] == 'sha256:5e5c5e1e436feb49fc4cbcd62c2e0ab2785db2141b0fe40d2926906bcfeaebfc'
    provenance = {'diagnostic_only': True, 'release_acceptance': False,
        'sources_sha256': {name: data['sha256'] for name, data in sources.items()},
        'package_sha256': {name: sha(args.source/name) for name in ['english.zip', 'chinese.zip']},
        'pilot_services_still_stopped': states,
        'template_version_unchanged': '0.3.25', 'no_production_or_native_queue_writes_this_round': True}
    (args.output/'provenance.json').write_text(json.dumps(provenance, indent=2)+'\n')
    checksums = {str(file.relative_to(args.output)): sha(file) for file in sorted(args.output.rglob('*')) if file.is_file()}
    (args.output/'checksums.json').write_text(json.dumps(checksums, indent=2)+'\n')
    print(json.dumps({'files': len(checksums), 'path': str(args.output)}), flush=True)


if __name__ == '__main__':
    main()
