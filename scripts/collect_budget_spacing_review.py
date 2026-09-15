"""Archive native 0.3.18 checks; reference the immutable prior review by hash."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import zipfile
from artifact_utils import sha
from collect_context_review import read, verify_files
from collect_paper_review import PROBES
from check_budget_spacing_outputs import compare_styles

ROOT = Path(__file__).resolve().parents[1]
CASES = ['preservation-complete', 'budget-long', 'budget-many']
KINDS = ['budget-spacing', 'preservation', 'sharing', 'polish', 'format', 'reading', 'quality']


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['baseline', 'variant', 'prior-stock', 'prior-tables', 'prior-review', 'rebuild', 'english', 'review-document', 'destination']:
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args(); assert not a.destination.exists(), 'Never overwrite a review'
    packages = {n: sha(a.baseline / n) for n in ['english.zip', 'chinese.zip']}
    prior_packages = {n: sha(a.prior_stock / n) for n in packages}
    prior_hashes = read(a.prior_review, 'checksums.json'); verify_files(a.prior_review, prior_hashes)
    copies = []
    def keep(source, name): copies.append((source, Path(name)))
    for side, root, prior in [('stock', a.baseline, a.prior_stock), ('tables', a.variant, a.prior_tables)]:
        cases = CASES if side == 'tables' else CASES[:1]
        pairs = {(c, l) for c in cases for l in ['english', 'chinese']}
        manifest, pilot, renders = [read(root, name) for name in ['manifest.json', 'pilot-report.json', 'render-results.json']]
        assert manifest['status'] == ('candidate' if side == 'stock' else 'runtime-experiment')
        assert manifest['source']['version'] == '0.3.18'
        assert all(not checkout['dirty'] for checkout in manifest['checkouts'].values())
        verify_files(root, packages); assert all(manifest['sha256'][n] == digest for n, digest in packages.items())
        assert pilot['semantic_checks_passed'] and pilot['package_sha256'] == packages
        expected = {(c, l, f) for c, l in pairs for f in ['html', 'pdf', 'docx']}
        assert {(r['case'], r['language'], r['format']) for r in renders} == expected
        assert len(renders) == len(expected) and all(r['passed'] for r in renders)
        issues = set() if side == 'tables' else {(c, l, k) for c, l in pairs for k in ['markdown-table-unsupported', 'docx-table-missing']}
        assert {(r['case'], r['language'], r['code']) for r in pilot['blocking_issues']} == issues
        assert len(pilot['blocking_issues']) == len(issues) and pilot['passed'] == (side == 'tables')
        verify_files(root / 'renders', pilot['sha256'])
        for name in ['manifest.json', 'pilot-report.json', 'render-results.json']: keep(root / name, f'{side}/{name}')
        for case, language in sorted(pairs):
            for fmt in ['pdf', 'docx']:
                for suffix in ['', '.fixture.json']:
                    name = f'{case}-{language}.{fmt}{suffix}'; keep(root / 'renders' / name, f'{side}/{name}')
                    assert sha(prior / 'renders' / name) == prior_hashes[f'{side}/{name}'], 'Prior render differs from immutable review'
            name = f'{case}-{language}.pdf'; keep(root / 'word-preview' / name, f'{side}/word-preview/{name}')
            assert sha(prior / 'word-preview' / name) == prior_hashes[f'{side}/word-preview/{name}']
        for kind in KINDS:
            name = kind + '-report.json'; report = read(root, name)
            assert report['selected_checks_passed'] and report['release_acceptance'] is False
            assert report['package_sha256'] == packages
            assert report['checker_sha256'] == sha(ROOT / ('scripts/check_' + kind.replace('-', '_') + '_outputs.py'))
            assert {(r['case'], r['language']) for r in report['rows']} == pairs and len(report['rows']) == len(pairs)
            verify_files(ROOT / 'scripts', report.get('helper_sha256', {}))
            verify_files(root, report.get('artifact_sha256', {})); verify_files(root / 'renders', report.get('render_sha256', {}))
            if kind == 'budget-spacing':
                assert report['prior_package_sha256'] == prior_packages
                verify_files(prior, report['prior_artifact_sha256'])
                for row in report['rows']:
                    assert row['question_comparisons'] == 15 and row['question_word_xml_unchanged']
                    if row['case'] == 'budget-long':
                        assert row['pdf']['complete_purpose_paragraphs'] == row['word']['complete_purpose_paragraphs'] == 60
                        assert row['word']['tail_shares_last_purpose_page']
            keep(root / name, f'{side}/{name}')
    for name, script in PROBES + [('identifier-translation-probe', 'identifier_translation')]:
        report = read(a.baseline, name + '.json')
        assert report['passed'] and report['release_acceptance'] is False and report['package_sha256'] == packages
        assert report['checker_sha256'] == sha(ROOT / f'scripts/probe_{script}.py')
        verify_files(a.english if script == 'repository_reading' else ROOT / 'scripts', report.get('helper_sha256', {}))
        verify_files(a.english, report.get('source_helper_sha256', {}))
        keep(a.baseline / (name + '.json'), 'stock/' + name + '.json')
    manifest = read(a.baseline, 'manifest.json')
    for name, count in [('budget-word-probe', 24), ('long-budget-word-probe', 28)]:
        report = read(a.baseline, name + '.json')
        assert report['passed'] and report['release_acceptance'] is False and len(report['rows']) == count
        assert report['source_commit'] == manifest['source']['commit']
        assert report['checker_sha256'] == sha(a.english / ('scripts/probe_' + name.replace('-probe', '').replace('-', '_') + '.py'))
        assert report['lua_sha256'] == sha(a.baseline / 'en/src/word/pilot.lua') == sha(a.baseline / 'translated/src/word/pilot.lua')
        verify_files(a.english, report.get('helper_sha256', {}))
        keep(a.baseline / (name + '.json'), name + '.json')
    assert manifest['translation_units'] == 720 and manifest['untranslated_units'] == []
    for name in ['translation-audit.json', 'structure-audit.json']:
        assert read(a.baseline, name) == []; keep(a.baseline / name, 'stock/' + name)
    audit = read(a.baseline, 'km-binding-audit.json')
    assert audit['source_commit'] == manifest['source']['commit'] and not audit['source_dirty']
    assert len(audit['templates']) == 34 and all(not t['unbound_variables'] and not t['absent_entities'] for t in audit['templates'])
    keep(a.baseline / 'km-binding-audit.json', 'binding-audit.json')
    runtime = read(a.variant, 'runtime-comparison.json')
    assert runtime['selected_comparison_passed'] and runtime['release_acceptance'] is False
    assert runtime['package_sha256'] == packages and runtime['checker_sha256'] == sha(ROOT / 'scripts/compare_runtime_outputs.py')
    assert {(r['case'], r['language']) for r in runtime['checks']} == {(CASES[0], l) for l in ['english', 'chinese']}
    for side, root in [('stock', a.baseline), ('tables', a.variant)]: verify_files(root, runtime['artifact_sha256'][side])
    keep(a.variant / 'runtime-comparison.json', 'runtime-comparison.json')
    rebuild = read(a.rebuild, 'manifest.json')
    assert rebuild['status'] == 'candidate' and all(not c['dirty'] for c in rebuild['checkouts'].values())
    assert rebuild['source'] == manifest['source']; verify_files(a.rebuild, packages)
    keep(a.rebuild / 'manifest.json', 'rebuild-manifest.json')
    delta = {}
    for locale in ['en', 'translated']:
        old, new = [{str(f.relative_to(root / locale)): sha(f) for f in sorted((root / locale / 'src').rglob('*')) if f.is_file()} for root in [a.prior_stock, a.baseline]]
        assert old.keys() == new.keys()
        changed = sorted(n for n in old if old[n] != new[n]); assert changed == ['src/layout.css', 'src/word/reference.docx']
        refs = [root / locale / 'src/word/reference.docx' for root in [a.prior_stock, a.baseline]]
        compare_styles(*refs)
        with zipfile.ZipFile(refs[0]) as z1, zipfile.ZipFile(refs[1]) as z2:
            assert set(z1.namelist()) == set(z2.namelist())
            assert [n for n in z1.namelist() if z1.read(n) != z2.read(n)] == ['word/styles.xml']
        delta[locale] = {'changed_paths': changed, 'prior_source_sha256': old, 'source_sha256': new}
    source_changes = subprocess.check_output(['git', '-C', str(a.english), 'diff', '--name-only', read(a.prior_stock, 'manifest.json')['source']['commit'], manifest['source']['commit'], '--', 'src', 'scripts/prepare_layout.py'], text=True).splitlines()
    assert source_changes == ['scripts/prepare_layout.py', 'src/layout.css']
    keep(a.english / 'docs/budget-spacing-experiment.md', 'english-scope.md'); keep(a.review_document, 'README.md')
    payload = (json.dumps({'source_delta': delta, 'git_source_changes': source_changes,
        'collector_sha256': sha(Path(__file__)), 'release_acceptance': False,
        'prior_review': {'path': str(a.prior_review.relative_to(ROOT)), 'checksums_sha256': sha(a.prior_review / 'checksums.json')}}, indent=2) + '\n').encode()
    size = len(payload) + sum(source.stat().st_size for source, _ in copies)
    assert size < 15_000_000 and len({n for _, n in copies}) == len(copies)
    a.destination.mkdir(parents=True, exist_ok=False); hashes = {}
    for source, name in copies:
        target = a.destination / name; target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, target); hashes[str(name)] = sha(target)
    target = a.destination / 'source-delta.json'; target.write_bytes(payload); hashes[target.name] = sha(target)
    (a.destination / 'checksums.json').write_text(json.dumps(hashes, indent=2) + '\n')
    print(json.dumps({'hashed_files': len(hashes), 'bytes': size, 'destination': str(a.destination)}))


if __name__ == '__main__':
    main()
