"""Archive a failed-acceptance research review; never publish a release."""

import argparse
import json
import shutil
import subprocess
from pathlib import Path

from artifact_utils import sha

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--upstream', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads((args.build / 'manifest.json').read_text())
    pilot = json.loads((args.build / 'pilot-report.json').read_text())
    retention = json.loads((args.build / 'answer-retention-report.json').read_text())
    if manifest['status'] != 'candidate' or not pilot['semantic_checks_passed'] or not retention['selected_regressions_passed']:
        raise ValueError('Need a locked build and passing selected regressions, not necessarily release acceptance')
    for name in ('english.zip', 'chinese.zip'):
        if sha(args.build / name) != pilot['package_sha256'][name]:
            raise ValueError('Pilot report does not match this package')
    for name, checksum in retention['sha256'].items():
        if sha(args.build / name) != checksum:
            raise ValueError('Retention report does not match rendered artifacts')
    if sha(ROOT / 'scripts/check_answer_retention.py') != retention['checker_sha256']:
        raise ValueError('Retention checker changed; regenerate its report')
    args.destination.mkdir(parents=True, exist_ok=False)
    for case in ('representative', 'retention-partial'):
        for language in ('english', 'chinese'):
            for extension in ('html', 'pdf', 'docx'):
                name = f'{case}-{language}.{extension}'
                shutil.copyfile(args.build / 'renders' / name, args.destination / name)
                shutil.copyfile(args.build / 'renders' / (name + '.fixture.json'), args.destination / (name + '.fixture.json'))
    for name in ('manifest.json', 'pilot-report.json', 'render-results.json', 'translation-audit.json', 'structure-audit.json',
                 'readability-checks.json', 'answer-retention-report.json', 'km-binding-audit.json', 'markdown-probe.json'):
        shutil.copyfile(args.build / name, args.destination / name)
    shutil.copytree(args.build / 'word-preview', args.destination / 'word-preview')
    upstream = args.destination / 'upstream'
    upstream.mkdir()
    for name in ('upstream-partial-english.html', 'upstream-representative-english.html', 'upstream-representative-english.pdf'):
        shutil.copyfile(args.upstream / 'renders' / name, upstream / name)
        shutil.copyfile(args.upstream / 'renders' / (name + '.fixture.json'), upstream / (name + '.fixture.json'))
    (upstream / 'source.json').write_text(json.dumps({'repository': 'https://github.com/ds-wizard/science-europe-template.git',
        'commit': '22d60aae4b63ee677477ac0c73097807284aaf9f', 'version': '1.30.1',
        'package_sha256': sha(args.upstream / 'english.zip'), 'template_modified': False}, indent=2) + '\n')
    shutil.copyfile(ROOT / 'docs/answer-retention-review.md', args.destination / 'README.md')
    runtime = subprocess.check_output(['docker', 'inspect', '--format', '{{.Name}} {{.Config.Image}} {{.Image}}',
        'science-europe-pilot-server-1', 'science-europe-pilot-docworker-1'], text=True)
    (args.destination / 'runtime-images.txt').write_text(runtime)
    (args.destination / 'checksums.json').write_text(json.dumps({str(p.relative_to(args.destination)): sha(p)
        for p in sorted(args.destination.rglob('*')) if p.is_file()}, indent=2) + '\n')
    print(args.destination)


if __name__ == '__main__':
    main()
