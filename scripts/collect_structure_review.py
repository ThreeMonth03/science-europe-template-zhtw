"""Archive bounded stock/experimental-worker evidence, never a release."""
import argparse
import json
import shutil
from pathlib import Path

from compare_runtime_outputs import sha

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--variant', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    comparison = json.loads((args.variant / 'runtime-comparison.json').read_text())
    assert comparison['selected_comparison_passed'] and comparison['release_acceptance'] is False
    assert json.loads((args.variant / 'pilot-report.json').read_text())['passed'] is True
    assert json.loads((args.baseline / 'pilot-report.json').read_text())['passed'] is False
    for name, checksum in comparison['package_sha256'].items():
        assert sha(args.baseline / name) == sha(args.variant / name) == checksum
    for side, root in [('stock', args.baseline), ('tables', args.variant)]:
        for name, checksum in comparison['artifact_sha256'][side].items():
            assert sha(root / name) == checksum, (side, name)
        report = json.loads((root / 'structure-report.json').read_text())
        assert report['selected_regressions_passed']
        assert report['checker_sha256'] == sha(ROOT / 'scripts/check_structure_outputs.py')
    assert comparison['checker_sha256'] == sha(ROOT / 'scripts/compare_runtime_outputs.py')
    args.destination.mkdir(parents=True, exist_ok=False)
    for side, root in [('stock', args.baseline), ('tables', args.variant)]:
        target = args.destination / side
        target.mkdir()
        for case in ('structured', 'structured-partial'):
            for language in ('english', 'chinese'):
                for fmt in ('html', 'pdf', 'docx'):
                    name = f'{case}-{language}.{fmt}'
                    for suffix in ('', '.fixture.json'):
                        shutil.copy2(root / 'renders' / (name + suffix), target / (name + suffix))
        for name in ('manifest.json', 'pilot-report.json', 'render-results.json', 'structure-report.json', 'readability-checks.json'):
            shutil.copy2(root / name, target / name)
        shutil.copytree(root / 'word-preview', target / 'word-preview')
    for name in ('translation-audit.json', 'structure-audit.json', 'readability-checks.json',
                 'answer-retention-report.json', 'km-binding-audit.json', 'markdown-probe.json',
                 'translated-branch-probe.json', 'ethical-branches-english.html', 'ethical-branches-chinese.html'):
        shutil.copy2(args.baseline / name, args.destination / 'stock' / name)
    # Preserve the old unitless/payment selections as an explicit counterexample.
    for suffix in ('', '.fixture.json'):
        name = 'representative-chinese.pdf' + suffix
        shutil.copy2(args.baseline / 'renders' / name, args.destination / 'stock' / name)
    shutil.copy2(args.variant / 'runtime-comparison.json', args.destination / 'runtime-comparison.json')
    shutil.copy2(ROOT / 'docs/structure-tables-review.md', args.destination / 'README.md')
    (args.destination / 'checksums.json').write_text(json.dumps({str(p.relative_to(args.destination)): sha(p)
        for p in sorted(args.destination.rglob('*')) if p.is_file()}, indent=2) + '\n')
    print(args.destination)


if __name__ == '__main__':
    main()
