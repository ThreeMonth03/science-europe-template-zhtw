"""Extend the bounded PDF/Word review archive with Q10 and polish evidence."""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from artifact_utils import sha

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('baseline', 'variant', 'rebuild', 'destination', 'review-document'): parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    baseline = json.loads((args.baseline / 'manifest.json').read_text())
    rebuild = json.loads((args.rebuild / 'manifest.json').read_text())
    assert rebuild['status'] == 'candidate' and all(not state['dirty'] for state in rebuild['checkouts'].values())
    assert rebuild['package_timestamp'] == baseline['package_timestamp']
    for name in ('english.zip', 'chinese.zip'):
        assert sha(args.rebuild / name) == rebuild['sha256'][name] == sha(args.baseline / name)
    for build in (args.baseline, args.variant):
        report = json.loads((build / 'polish-report.json').read_text())
        assert report['selected_checks_passed'] and report['release_acceptance'] is False
        assert report['checker_sha256'] == sha(ROOT / 'scripts/check_polish_outputs.py')
        assert report['text_extractor_sha256'] == sha(ROOT / 'scripts/check_narrative_outputs.py')
        for name, expected in report['package_sha256'].items(): assert sha(build / name) == expected
        for name, expected in report['artifact_sha256'].items(): assert sha(build / name) == expected
        checked = {(r['case'], r['language']) for r in report['rows']}
        for case in ('storage-sharing', 'storage-sharing-partial', 'narrative-long'): assert (case, 'chinese') in checked
    subprocess.run([sys.executable, str(ROOT / 'scripts/collect_format_review.py'), '--baseline', str(args.baseline), '--variant', str(args.variant), '--destination', str(args.destination), '--review-document', str(args.review_document)], check=True)
    shutil.copy2(args.rebuild / 'manifest.json', args.destination / 'rebuild-manifest.json')
    for label, build in [('stock', args.baseline), ('tables', args.variant)]:
        out = args.destination / label
        shutil.copy2(build / 'polish-report.json', out / 'polish-report.json')
        for case in ('storage-sharing', 'storage-sharing-partial', 'narrative-long'):
            for fmt in ('pdf', 'docx'):
                for suffix in ('', '.fixture.json'):
                    name = f'{case}-chinese.{fmt}{suffix}'
                    shutil.copy2(build / 'renders' / name, out / name)
    paths = [p for p in args.destination.rglob('*') if p.is_file() and p.name != 'checksums.json']
    size = sum(p.stat().st_size for p in paths)
    assert size <= 25_000_000, (size, 'Do not commit oversized review')
    (args.destination / 'checksums.json').write_text(json.dumps({str(p.relative_to(args.destination)): sha(p) for p in sorted(paths)}, indent=2) + '\n')
    print(json.dumps({'hashed_files': len(paths), 'bytes': size, 'destination': str(args.destination)}))


if __name__ == '__main__': main()
