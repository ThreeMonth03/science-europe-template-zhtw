"""Archive both sides of the bounded Q11 paragraph experiment without promoting it."""
import argparse
import json
import shutil
from pathlib import Path
from artifact_utils import sha

ROOT = Path(__file__).resolve().parents[1]
CASES = ['preservation-complete', 'preservation-partial']
PAIRS = {(c, l) for c in CASES for l in ['english', 'chinese']}
KINDS = ['context', 'preservation', 'sharing', 'polish', 'format', 'reading', 'quality']
PROBES = [('format-translation-probe', 'format_translation'), ('sharing-translation-probe', 'sharing_translation'),
          ('preservation-translation-probe', 'preservation_translation'), ('answer-state-probe', 'answer_states'),
          ('repository-reading-probe', 'repository_reading'), ('contact-translation-probe', 'contact_translation')]


def read(root, name): return json.loads((root / name).read_text())


def verify_files(root, hashes):
    for name, digest in hashes.items(): assert sha(root / name) == digest, (root, name, 'Stale evidence')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['baseline', 'variant', 'prior-stock', 'prior-tables', 'rebuild', 'english', 'binding-audit', 'review-document', 'destination']:
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args(); assert not a.destination.exists(), 'Never overwrite an archive'
    packages = {n: sha(a.baseline / n) for n in ['english.zip', 'chinese.zip']}
    prior_packages = {n: sha(a.prior_stock / n) for n in packages}
    copies = []
    def keep(source, name): copies.append((source, Path(name)))
    for side, root, expected_packages in [('stock', a.baseline, packages), ('tables', a.variant, packages),
                                          ('prior-stock', a.prior_stock, prior_packages), ('prior-tables', a.prior_tables, prior_packages)]:
        tables = side.endswith('tables')
        manifest, pilot, renders = [read(root, n) for n in ['manifest.json', 'pilot-report.json', 'render-results.json']]
        assert manifest['status'] == ('runtime-experiment' if tables else 'candidate')
        assert all(not v['dirty'] for v in manifest['checkouts'].values())
        assert manifest['source']['version'] == ('0.3.11' if side.startswith('prior-') else '0.3.12')
        verify_files(root, expected_packages)
        assert all(manifest['sha256'][n] == h for n, h in expected_packages.items())
        assert pilot['semantic_checks_passed'] and pilot['package_sha256'] == expected_packages
        expected = set() if tables else {(c, l, code) for c, l in PAIRS for code in ['markdown-table-unsupported', 'docx-table-missing']}
        assert {(r['case'], r['language'], r['code']) for r in pilot['blocking_issues']} == expected
        assert len(pilot['blocking_issues']) == len(expected) and pilot['passed'] == (not expected)
        assert len(renders) == 12 and all(r['passed'] for r in renders)
        assert {(r['case'], r['language'], r['format']) for r in renders} == {(c, l, f) for c, l in PAIRS for f in ['html', 'pdf', 'docx']}
        verify_files(root / 'renders', pilot['sha256'])
        for name in ['manifest.json', 'pilot-report.json', 'render-results.json']: keep(root / name, f'{side}/{name}')
        for case, language in sorted(PAIRS):
            for fmt in ['html', 'pdf', 'docx']:
                for suffix in ['', '.fixture.json']:
                    name = f'{case}-{language}.{fmt}{suffix}'; keep(root / 'renders' / name, f'{side}/{name}')
            name = f'{case}-{language}.pdf'; keep(root / 'word-preview' / name, f'{side}/word-preview/{name}')
        if side.startswith('prior-'): continue
        for kind in KINDS:
            name = kind + '-report.json'; report = read(root, name)
            assert report['selected_checks_passed'] and report['release_acceptance'] is False
            assert report['package_sha256'] == packages and report['checker_sha256'] == sha(ROOT / f'scripts/check_{kind}_outputs.py')
            assert len(report['rows']) == 4 and {(r['case'], r['language']) for r in report['rows']} == PAIRS
            verify_files(ROOT / 'scripts', report.get('helper_sha256', {}))
            for key, folder in [('artifact_sha256', root), ('render_sha256', root / 'renders')]: verify_files(folder, report.get(key, {}))
            if kind == 'context':
                assert report['prior_package_sha256'] == prior_packages
                assert sum(r['controlled_question_comparisons'] for r in report['rows']) == 60
                assert all(r['owned_paragraphs_joined_away'] == 2 for r in report['rows'])
                verify_files(a.prior_tables if tables else a.prior_stock, report['prior_artifact_sha256'])
            keep(root / name, f'{side}/{name}')
    for name, script in PROBES:
        report = read(a.baseline, name + '.json')
        assert report['passed'] and report['release_acceptance'] is False and report['package_sha256'] == packages
        assert report['checker_sha256'] == sha(ROOT / f'scripts/probe_{script}.py')
        verify_files(ROOT / 'scripts', report.get('helper_sha256', {}))
        verify_files(a.english, report.get('source_helper_sha256', {}))
        keep(a.baseline / (name + '.json'), 'stock/' + name + '.json')
    for name in ['translation-audit.json', 'structure-audit.json']:
        assert read(a.baseline, name) == []; keep(a.baseline / name, 'stock/' + name)
    runtime = read(a.variant, 'runtime-comparison.json')
    assert runtime['selected_comparison_passed'] and runtime['release_acceptance'] is False
    assert runtime['package_sha256'] == packages and runtime['checker_sha256'] == sha(ROOT / 'scripts/compare_runtime_outputs.py')
    assert {(r['case'], r['language']) for r in runtime['checks']} == PAIRS
    for side, root in [('stock', a.baseline), ('tables', a.variant)]: verify_files(root, runtime['artifact_sha256'][side])
    keep(a.variant / 'runtime-comparison.json', 'runtime-comparison.json')
    audit = json.loads(a.binding_audit.read_text())
    assert not audit['source_dirty'] and audit['source_commit'] == read(a.baseline, 'manifest.json')['source']['commit']
    assert len(audit['templates']) == 33 and all(not t['unbound_variables'] and not t['absent_entities'] for t in audit['templates'])
    keep(a.binding_audit, 'binding-audit.json')
    keep(a.english / 'docs/preservation-context-flow.md', 'english-scope.md')
    rebuild = read(a.rebuild, 'manifest.json')
    assert rebuild['status'] == 'candidate' and all(not v['dirty'] for v in rebuild['checkouts'].values())
    verify_files(a.rebuild, packages); keep(a.rebuild / 'manifest.json', 'rebuild-manifest.json')
    delta = {}
    for locale in ['en', 'translated']:
        old, new = [{str(f.relative_to(root / locale)): sha(f) for f in sorted((root / locale / 'src').rglob('*')) if f.is_file()} for root in [a.prior_stock, a.baseline]]
        changed = sorted(n for n in old if old[n] != new.get(n))
        assert old.keys() == new.keys() and changed == ['src/preservation-dataset.html.j2', 'src/questions/11-data-preservation.html.j2']
        delta[locale] = {'changed_source_paths': changed, 'prior_source_sha256': old, 'source_sha256': new,
                         'css_lua_reference_and_other_sources_byte_identical': True}
    keep(a.review_document, 'README.md')
    payload = (json.dumps(delta, indent=2) + '\n').encode()
    size = len(payload) + sum(source.stat().st_size for source, _ in copies)
    assert size < 25_000_000 and len({n for _, n in copies}) == len(copies)
    a.destination.mkdir(parents=True, exist_ok=False); hashes = {}
    for source, name in copies:
        target = a.destination / name; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target); hashes[str(name)] = sha(target)
    target = a.destination / 'context-source-delta.json'; target.write_bytes(payload); hashes[target.name] = sha(target)
    (a.destination / 'checksums.json').write_text(json.dumps(hashes, indent=2) + '\n')
    print(json.dumps({'hashed_files': len(hashes), 'bytes': size, 'destination': str(a.destination)}))


if __name__ == '__main__': main()
