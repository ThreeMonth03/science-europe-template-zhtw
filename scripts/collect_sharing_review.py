"""Archive only checksum-bound sharing/preservation samples; never overwrite a review."""
import argparse
import json
import shutil
from pathlib import Path
from artifact_utils import sha

ROOT = Path(__file__).resolve().parents[1]
CASES = ('structured', 'storage-sharing', 'storage-sharing-partial', 'narrative-long', 'sharing-custom', 'sharing-missing')


def read(root, name): return json.loads((root / name).read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('baseline', 'variant', 'rebuild', 'english', 'destination', 'review-document'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    assert not args.destination.exists(), 'Never overwrite an earlier review'
    comparison = read(args.variant, 'runtime-comparison.json')
    assert comparison['selected_comparison_passed'] and comparison['release_acceptance'] is False
    assert comparison['checker_sha256'] == sha(ROOT / 'scripts/compare_runtime_outputs.py')
    assert {(r['case'], r['language']) for r in comparison['checks']} == {(c,l) for c in CASES for l in ('english','chinese')}
    packages = comparison['package_sha256']
    copies = []
    def keep(source, name): copies.append((source, Path(name)))
    for side, root in (('stock', args.baseline), ('tables', args.variant)):
        manifest = read(root, 'manifest.json'); pilot = read(root, 'pilot-report.json')
        assert manifest['status'] == ('candidate' if side == 'stock' else 'runtime-experiment')
        assert pilot['semantic_checks_passed'] and pilot['checker_sha256'] == sha(ROOT / 'scripts/run_pilot.py')
        assert all(row['passed'] for row in read(root, 'render-results.json'))
        if side == 'tables': assert pilot['passed'] and not pilot['blocking_issues']
        else:
            assert not pilot['passed'] and len(pilot['blocking_issues']) == 24
            assert {r['code'] for r in pilot['blocking_issues']} == {'markdown-table-unsupported', 'docx-table-missing'}
        for name, expected in packages.items(): assert sha(root / name) == expected == manifest['sha256'][name] == pilot['package_sha256'][name]
        for name, expected in comparison['artifact_sha256'][side].items(): assert sha(root / name) == expected
        cases = list(CASES) + (['empty'] if side == 'stock' else [])
        required = {(c,l) for c in cases for l in ('english','chinese')}
        for kind in ('sharing', 'polish', 'format', 'reading', 'quality'):
            name = kind + '-report.json'; report = read(root, name)
            assert report['selected_checks_passed'] and report['release_acceptance'] is False
            assert report['checker_sha256'] == sha(ROOT / f'scripts/check_{kind}_outputs.py')
            assert report['package_sha256'] == packages
            assert {(r['case'],r['language']) for r in report['rows']} == required
            for path, expected in report.get('artifact_sha256', {}).items(): assert sha(root / path) == expected
            for path, expected in report.get('render_sha256', {}).items(): assert sha(root / 'renders' / path) == expected
            if 'text_extractor_sha256' in report: assert report['text_extractor_sha256'] == sha(ROOT / 'scripts/check_narrative_outputs.py')
            if 'date_helper_sha256' in report: assert report['date_helper_sha256'] == sha(ROOT / 'scripts/check_polish_outputs.py')
            keep(root / name, f'{side}/{name}')
        for name in ('manifest.json', 'pilot-report.json', 'render-results.json'): keep(root / name, f'{side}/{name}')
        samples = [(c,'chinese') for c in cases] + [('structured','english')]
        for case, language in samples:
            for fmt in ('pdf','docx'):
                for suffix in ('', '.fixture.json'):
                    name = f'{case}-{language}.{fmt}{suffix}'; keep(root / 'renders' / name, f'{side}/{name}')
            if case != 'empty':
                name = f'{case}-{language}.pdf'; keep(root / 'word-preview' / name, f'{side}/word-preview/{name}')
    for kind in ('sharing', 'format', 'reading', 'quality'):
        name = kind + '-translation-probe.json'; report = read(args.baseline, name)
        assert report['passed'] and report['package_sha256'] == packages
        assert report['checker_sha256'] == sha(ROOT / f'scripts/probe_{kind}_translation.py')
        keep(args.baseline / name, f'stock/{name}')
    word = read(args.baseline, 'word-sharing-probe.json')
    assert word['passed'] and word['word_filter_sha256'] == sha(args.english / 'src/word/pilot.lua')
    assert word['checker_sha256'] == sha(ROOT / 'scripts/probe_word_sharing.py')
    for name in ('word-sharing-probe.json', 'km-binding-audit.json', 'translation-audit.json', 'structure-audit.json'):
        keep(args.baseline / name, f'stock/{name}')
    rebuild = read(args.rebuild, 'manifest.json')
    assert rebuild['status'] == 'candidate' and all(not state['dirty'] for state in rebuild['checkouts'].values())
    for name, expected in packages.items(): assert sha(args.rebuild / name) == expected == rebuild['sha256'][name]
    keep(args.rebuild / 'manifest.json', 'rebuild-manifest.json')
    keep(args.variant / 'runtime-comparison.json', 'runtime-comparison.json')
    keep(args.review_document, 'README.md')
    size = sum(p.stat().st_size for p,_ in copies)
    assert size <= 25_000_000, (size, 'Review exceeds size budget')
    args.destination.mkdir(parents=True, exist_ok=False)
    checksums = {}
    for source, name in copies:
        target = args.destination / name; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target); checksums[str(name)] = sha(target)
    (args.destination / 'checksums.json').write_text(json.dumps(checksums, indent=2) + '\n')
    print(json.dumps({'hashed_files': len(checksums), 'bytes': size, 'destination': str(args.destination)}))


if __name__ == '__main__': main()
