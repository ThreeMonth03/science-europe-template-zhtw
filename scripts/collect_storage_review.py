"""Archive compact PDF/DOCX evidence; keep font-heavy HTML in local build outputs."""
import argparse
import json
import shutil
from pathlib import Path
from artifact_utils import sha

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--variant', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    comparison = json.loads((args.variant / 'runtime-comparison.json').read_text())
    assert comparison['selected_comparison_passed']
    assert comparison['checker_sha256'] == sha(ROOT / 'scripts/compare_runtime_outputs.py')
    assert json.loads((args.baseline / 'manifest.json').read_text())['status'] == 'candidate'
    assert json.loads((args.variant / 'manifest.json').read_text())['status'] == 'runtime-experiment'
    assert json.loads((args.variant / 'pilot-report.json').read_text())['passed']
    for name, expected in comparison['package_sha256'].items():
        assert sha(args.baseline / name) == sha(args.variant / name) == expected
    for side, root in [('stock', args.baseline), ('tables', args.variant)]:
        manifest = json.loads((root / 'manifest.json').read_text())
        pilot = json.loads((root / 'pilot-report.json').read_text())
        assert pilot['semantic_checks_passed']
        assert pilot['package_sha256'] == comparison['package_sha256']
        for name, expected in comparison['package_sha256'].items():
            assert manifest['sha256'][name] == expected
        report = json.loads((root / 'storage-sharing-report.json').read_text())
        assert report['selected_checks_passed'] and report['release_acceptance'] is False
        assert report['checker_sha256'] == sha(ROOT / 'scripts/check_storage_sharing_outputs.py')
        for name, expected in report['sha256'].items(): assert sha(root / name) == expected
        for name, expected in comparison['artifact_sha256'][side].items(): assert sha(root / name) == expected
    args.destination.mkdir(parents=True, exist_ok=False)
    for side, root in [('stock', args.baseline), ('tables', args.variant)]:
        out = args.destination / side; out.mkdir()
        for case, language in [('structured', 'chinese'), ('storage-sharing', 'chinese'), ('storage-sharing-partial', 'chinese'), ('storage-sharing', 'english')]:
            for fmt in ('pdf', 'docx'):
                name = f'{case}-{language}.{fmt}'
                for suffix in ('', '.fixture.json'):
                    shutil.copy2(root / 'renders' / (name + suffix), out / (name + suffix))
        for name in ('manifest.json', 'pilot-report.json', 'render-results.json', 'storage-sharing-report.json'):
            shutil.copy2(root / name, out / name)
        shutil.copytree(root / 'word-preview', out / 'word-preview')
    for name in ('storage-mapping-audit.json', 'km-binding-audit.json', 'translation-audit.json', 'structure-audit.json', 'readability-checks.json'):
        shutil.copy2(args.baseline / name, args.destination / 'stock' / name)
    shutil.copy2(args.variant / 'runtime-comparison.json', args.destination / 'runtime-comparison.json')
    shutil.copy2(ROOT / 'docs/storage-sharing-review.md', args.destination / 'README.md')
    (args.destination / 'checksums.json').write_text(json.dumps({str(p.relative_to(args.destination)): sha(p)
        for p in sorted(args.destination.rglob('*')) if p.is_file()}, indent=2) + '\n')
    print(args.destination)


if __name__ == '__main__': main()
