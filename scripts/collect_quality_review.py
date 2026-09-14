"""Archive selected non-release samples after checking their provenance/hashes."""
import argparse
import json
import shutil
from pathlib import Path
from artifact_utils import sha

ROOT = Path(__file__).resolve().parents[1]


def validate(root, comparison, side):
    manifest = json.loads((root / 'manifest.json').read_text())
    assert manifest['status'] == ('candidate' if side == 'stock' else 'runtime-experiment')
    pilot = json.loads((root / 'pilot-report.json').read_text())
    assert pilot['semantic_checks_passed']
    if side == 'tables': assert pilot['passed']
    report = json.loads((root / 'quality-report.json').read_text())
    assert report['selected_checks_passed'] and report['release_acceptance'] is False
    assert report['checker_sha256'] == sha(ROOT / 'scripts/check_quality_outputs.py')
    for name, expected in comparison['package_sha256'].items():
        assert sha(root / name) == expected == manifest['sha256'][name] == pilot['package_sha256'][name] == report['package_sha256'][name]
    for name, expected in report['render_sha256'].items(): assert sha(root / 'renders' / name) == expected
    for name, expected in comparison['artifact_sha256'][side].items(): assert sha(root / name) == expected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--variant', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--review-document', type=Path, required=True)
    args = parser.parse_args()
    comparison = json.loads((args.variant / 'runtime-comparison.json').read_text())
    assert comparison['selected_comparison_passed'] and comparison['release_acceptance'] is False
    assert comparison['checker_sha256'] == sha(ROOT / 'scripts/compare_runtime_outputs.py')
    for side, root in [('stock', args.baseline), ('tables', args.variant)]: validate(root, comparison, side)
    probe = json.loads((args.baseline / 'quality-translation-probe.json').read_text())
    assert probe['passed'] and probe['checker_sha256'] == sha(ROOT / 'scripts/probe_quality_translation.py')
    assert probe['assertion_helper_sha256'] == sha(ROOT / 'scripts/check_quality_outputs.py')
    assert probe['package_sha256'] == comparison['package_sha256']
    args.destination.mkdir(parents=True, exist_ok=False)
    for side, root in [('stock', args.baseline), ('tables', args.variant)]:
        out = args.destination / side; out.mkdir()
        cases = [('structured', 'chinese'), ('quality-rich', 'chinese'), ('quality-partial', 'chinese'), ('structured', 'english')]
        if side == 'stock': cases += [('archive-only', 'chinese'), ('empty', 'chinese')]
        checked = {(row['case'], row['language']) for row in json.loads((root / 'quality-report.json').read_text())['rows']}
        for case, language in cases:
            assert (case, language) in checked
            for fmt in ('pdf', 'docx'):
                name = f'{case}-{language}.{fmt}'
                for suffix in ('', '.fixture.json'): shutil.copy2(root / 'renders' / (name + suffix), out / (name + suffix))
        for name in ('manifest.json', 'pilot-report.json', 'render-results.json', 'quality-report.json'):
            shutil.copy2(root / name, out / name)
        shutil.copytree(root / 'word-preview', out / 'word-preview')
    for name in ('km-binding-audit.json', 'translation-audit.json', 'structure-audit.json', 'quality-translation-probe.json', 'storage-sharing-report.json', 'narrative-report.json'):
        shutil.copy2(args.baseline / name, args.destination / 'stock' / name)
    shutil.copy2(args.variant / 'runtime-comparison.json', args.destination / 'runtime-comparison.json')
    shutil.copy2(args.review_document, args.destination / 'README.md')
    (args.destination / 'checksums.json').write_text(json.dumps({str(p.relative_to(args.destination)): sha(p)
        for p in sorted(args.destination.rglob('*')) if p.is_file()}, indent=2) + '\n')
    print(args.destination)


if __name__ == '__main__': main()
