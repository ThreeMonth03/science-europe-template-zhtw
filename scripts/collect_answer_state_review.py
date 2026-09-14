"""Immutable, hash-bound 0.3.9 review; stock table failures remain explicit."""
import argparse
import json
import shutil
from pathlib import Path
from artifact_utils import sha

ROOT = Path(__file__).resolve().parents[1]
STOCK = {'preservation-complete', 'empty', 'support-mixed'}
TABLES = {'preservation-complete', 'support-mixed'}
REPORTS = ['preservation', 'sharing', 'polish', 'format', 'reading', 'quality', 'answer-state']


def read(root, name): return json.loads((root / name).read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['baseline', 'variant', 'prior-stock', 'prior-tables', 'rebuild', 'destination', 'review-document', 'english', 'binding-audit']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    assert not args.destination.exists(), 'Never overwrite a review'
    packages = {n: sha(args.baseline / n) for n in ['english.zip', 'chinese.zip']}
    copies = []
    def keep(source, name): copies.append((source, Path(name)))
    comparison = read(args.variant, 'runtime-comparison.json')
    assert comparison['selected_comparison_passed'] and comparison['release_acceptance'] is False
    assert comparison['package_sha256'] == packages and comparison['checker_sha256'] == sha(ROOT / 'scripts/compare_runtime_outputs.py')
    assert {(r['case'], r['language']) for r in comparison['checks']} == {(c, l) for c in TABLES for l in ['english', 'chinese']}
    for side, root, prior, cases in [('stock', args.baseline, args.prior_stock, STOCK), ('tables', args.variant, args.prior_tables, TABLES)]:
        pairs = {(c, l) for c in cases for l in ['english', 'chinese']}
        manifest = read(root, 'manifest.json'); pilot = read(root, 'pilot-report.json'); renders = read(root, 'render-results.json')
        assert manifest['status'] == ('candidate' if side == 'stock' else 'runtime-experiment')
        assert all(not s['dirty'] for s in manifest['checkouts'].values())
        assert pilot['semantic_checks_passed'] and pilot['checker_sha256'] == sha(ROOT / 'scripts/run_pilot.py')
        assert len(renders) == len(pairs) * 3 and all(r['passed'] for r in renders)
        assert {(r['case'], r['language'], r['format']) for r in renders} == {(c, l, f) for c, l in pairs for f in ['html', 'pdf', 'docx']}
        if side == 'stock':
            expected = {(c, l, code) for c, l in pairs if c != 'empty' for code in ['markdown-table-unsupported', 'docx-table-missing']}
            assert not pilot['passed'] and len(pilot['blocking_issues']) == len(expected)
            assert {(r['case'], r['language'], r['code']) for r in pilot['blocking_issues']} == expected
        else: assert pilot['passed'] and not pilot['blocking_issues']
        for n, digest in packages.items(): assert digest == sha(root / n) == manifest['sha256'][n] == pilot['package_sha256'][n]
        for name, digest in pilot['sha256'].items(): assert sha(root / 'renders' / name) == digest
        for name, digest in comparison['artifact_sha256'][side].items(): assert sha(root / name) == digest
        for kind in REPORTS:
            name = kind + '-report.json'; report = read(root, name)
            assert report['selected_checks_passed'] and report['release_acceptance'] is False
            assert report['package_sha256'] == packages and report['checker_sha256'] == sha(ROOT / f'scripts/check_{kind.replace("-", "_")}_outputs.py')
            assert len(report['rows']) == len(pairs) and {(r['case'], r['language']) for r in report['rows']} == pairs
            for p, digest in report.get('artifact_sha256', {}).items(): assert sha(root / p) == digest
            for p, digest in report.get('render_sha256', {}).items(): assert sha(root / 'renders' / p) == digest
            for p, digest in report.get('helper_sha256', {}).items(): assert sha(ROOT / 'scripts' / p) == digest
            for key, p in [('text_extractor_sha256', 'check_narrative_outputs.py'), ('date_helper_sha256', 'check_polish_outputs.py')]:
                if key in report: assert report[key] == sha(ROOT / 'scripts' / p)
            if kind == 'answer-state':
                assert report['prior_package_sha256'] == {n: sha(prior / n) for n in packages}
                for p, digest in report['prior_artifact_sha256'].items(): assert sha(prior / p) == digest
                assert sum(r['controlled_question_comparisons'] for r in report['rows']) == (60 if side == 'stock' else 30)
                assert report['new_cases_without_prior'] == ['support-mixed']
            keep(root / name, f'{side}/{name}')
        for name in ['manifest.json', 'pilot-report.json', 'render-results.json']: keep(root / name, f'{side}/{name}')
        for case, lang in sorted(pairs):
            for fmt in ['pdf', 'docx']:
                for extra in ['', '.fixture.json']:
                    name = f'{case}-{lang}.{fmt}{extra}'; keep(root / 'renders' / name, f'{side}/{name}')
            name = f'{case}-{lang}.pdf'; keep(root / 'word-preview' / name, f'{side}/word-preview/{name}')
    for kind, script in [('answer-state', 'probe_answer_states.py'), ('preservation-translation', 'probe_preservation_translation.py'), ('sharing-translation', 'probe_sharing_translation.py'), ('format-translation', 'probe_format_translation.py')]:
        name = kind + '-probe.json'; probe = read(args.baseline, name)
        assert probe['passed'] and probe['release_acceptance'] is False and probe['package_sha256'] == packages
        assert probe['checker_sha256'] == sha(ROOT / 'scripts' / script)
        keep(args.baseline / name, 'stock/' + name)
    for name in ['translation-audit.json', 'structure-audit.json']:
        assert read(args.baseline, name) == []; keep(args.baseline / name, 'stock/' + name)
    audit = json.loads(args.binding_audit.read_text())
    assert not audit['source_dirty'] and audit['source_commit'] == read(args.baseline, 'manifest.json')['checkouts']['english']['commit']
    assert all(not q['unbound_variables'] and not q['absent_entities'] for q in audit['templates'])
    keep(args.binding_audit, 'binding-audit.json')
    keep(args.english / 'docs/answer-state-claims.md', 'english-scope.md')
    rebuild = read(args.rebuild, 'manifest.json')
    assert rebuild['status'] == 'candidate' and all(not s['dirty'] for s in rebuild['checkouts'].values())
    assert {n: sha(args.rebuild / n) for n in packages} == packages
    keep(args.rebuild / 'manifest.json', 'rebuild-manifest.json')
    keep(args.variant / 'runtime-comparison.json', 'runtime-comparison.json')
    keep(args.review_document, 'README.md')
    delta = {}
    for side in ['en', 'translated']:
        a, b = [{str(p.relative_to(r / side)): sha(p) for p in sorted((r / side / 'src').rglob('*')) if p.is_file()} for r in [args.prior_stock, args.baseline]]
        assert a.keys() == b.keys()
        changes = [p for p in a if a[p] != b[p]]
        assert changes == ['src/questions/05-store-backup.html.j2', 'src/questions/11-data-preservation.html.j2', 'src/uuids.j2'], (side, changes)
        delta[side] = {'changed_source_paths': changes, 'prior_source_sha256': a, 'source_sha256': b}
    delta_bytes = (json.dumps(delta, indent=2) + '\n').encode()
    size = sum(p.stat().st_size for p, _ in copies) + len(delta_bytes)
    assert size <= 25_000_000 and len({n for _, n in copies}) == len(copies)
    args.destination.mkdir(parents=True, exist_ok=False); hashes = {}
    for source, name in copies:
        target = args.destination / name; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target); hashes[str(name)] = sha(target)
    target = args.destination / 'content-source-delta.json'; target.write_bytes(delta_bytes); hashes[target.name] = sha(target)
    (args.destination / 'checksums.json').write_text(json.dumps(hashes, indent=2) + '\n')
    print(json.dumps({'hashed_files': len(hashes), 'bytes': size, 'destination': str(args.destination)}))


if __name__ == '__main__': main()
