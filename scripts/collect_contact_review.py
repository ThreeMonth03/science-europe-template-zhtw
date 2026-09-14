"""Archive exact contact-reference evidence; refuse stale reports and known-failure promotion."""
import argparse
import json
import shutil
from pathlib import Path
from artifact_utils import sha

ROOT = Path(__file__).resolve().parents[1]
CASES = {'support-mixed', 'repository-long', 'contact-mixed'}
KINDS = ['preservation', 'sharing', 'polish', 'format', 'reading', 'quality', 'contact']


def read(root, name): return json.loads((root / name).read_text())


def source_delta(prior, current):
    result = {}
    for locale in ['en', 'translated']:
        old, new = [{str(f.relative_to(root / locale)): sha(f) for f in sorted((root / locale / 'src').rglob('*')) if f.is_file()} for root in [prior, current]]
        assert old.keys() == new.keys()
        changed = [n for n in old if old[n] != new[n]]
        assert changed == ['src/questions/10-share-restrictions.html.j2', 'src/questions/11-data-preservation.html.j2'], (locale, changed)
        result[locale] = {'changed_source_paths': changed, 'prior_source_sha256': old, 'source_sha256': new,
                          'css_lua_reference_and_other_sources_byte_identical': True}
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for n in ['baseline', 'variant', 'prior-stock', 'prior-tables', 'rebuild', 'destination', 'review-document', 'english', 'binding-audit']:
        p.add_argument('--' + n, type=Path, required=True)
    a = p.parse_args(); assert not a.destination.exists(), 'Never overwrite an archive'
    pairs = {(c, l) for c in CASES for l in ['english', 'chinese']}
    packages = {n: sha(a.baseline / n) for n in ['english.zip', 'chinese.zip']}
    copies = []
    def keep(source, target): copies.append((source, Path(target)))
    def helpers(report):
        for name, digest in report.get('helper_sha256', {}).items(): assert digest == sha(ROOT / 'scripts' / name)
        for key, name in [('text_extractor_sha256', 'check_narrative_outputs.py'), ('date_helper_sha256', 'check_polish_outputs.py')]:
            if key in report: assert report[key] == sha(ROOT / 'scripts' / name)
    runtime = read(a.variant, 'runtime-comparison.json')
    assert runtime['selected_comparison_passed'] and runtime['release_acceptance'] is False
    assert runtime['checker_sha256'] == sha(ROOT / 'scripts/compare_runtime_outputs.py') and runtime['package_sha256'] == packages
    assert {(r['case'], r['language']) for r in runtime['checks']} == pairs
    for side, root, prior in [('stock', a.baseline, a.prior_stock), ('tables', a.variant, a.prior_tables)]:
        manifest = read(root, 'manifest.json'); pilot = read(root, 'pilot-report.json'); renders = read(root, 'render-results.json')
        assert manifest['status'] == ('candidate' if side == 'stock' else 'runtime-experiment')
        assert all(not v['dirty'] for v in manifest['checkouts'].values())
        assert pilot['semantic_checks_passed'] and pilot['checker_sha256'] == sha(ROOT / 'scripts/run_pilot.py')
        assert len(renders) == 18 and all(r['passed'] for r in renders)
        assert {(r['case'], r['language'], r['format']) for r in renders} == {(c, l, f) for c, l in pairs for f in ['html', 'pdf', 'docx']}
        expected = {(c, l, code) for c, l in pairs for code in ['markdown-table-unsupported', 'docx-table-missing']} if side == 'stock' else set()
        assert {(r['case'], r['language'], r['code']) for r in pilot['blocking_issues']} == expected and len(pilot['blocking_issues']) == len(expected)
        assert pilot['passed'] == (not expected)
        for name, digest in packages.items(): assert digest == sha(root / name) == manifest['sha256'][name] == pilot['package_sha256'][name]
        for name, digest in pilot['sha256'].items(): assert sha(root / 'renders' / name) == digest
        for name, digest in runtime['artifact_sha256'][side].items(): assert sha(root / name) == digest
        for kind in KINDS:
            name = kind + '-report.json'; report = read(root, name)
            assert report['selected_checks_passed'] and report['release_acceptance'] is False and report['package_sha256'] == packages
            assert report['checker_sha256'] == sha(ROOT / f'scripts/check_{kind}_outputs.py')
            assert len(report['rows']) == len(pairs) and {(r['case'], r['language']) for r in report['rows']} == pairs
            helpers(report)
            for key, folder in [('artifact_sha256', root), ('render_sha256', root / 'renders')]:
                for name2, digest in report.get(key, {}).items(): assert sha(folder / name2) == digest
            if kind == 'contact':
                assert report['prior_package_sha256'] == {n: sha(prior / n) for n in packages}
                assert report['new_cases_without_prior'] == ['contact-mixed']
                assert sum(r['controlled_question_comparisons'] for r in report['rows']) == 60
                for name2, digest in report['prior_artifact_sha256'].items(): assert sha(prior / name2) == digest
            keep(root / name, f'{side}/{name}')
        for name in ['manifest.json', 'pilot-report.json', 'render-results.json']: keep(root / name, f'{side}/{name}')
        for case, lang in sorted(pairs):
            for fmt in ['pdf', 'docx']:
                for suffix in ['', '.fixture.json']:
                    name = f'{case}-{lang}.{fmt}{suffix}'; keep(root / 'renders' / name, f'{side}/{name}')
            name = f'{case}-{lang}.pdf'; keep(root / 'word-preview' / name, f'{side}/word-preview/{name}')
    probes = [('contact-translation-probe.json', 'probe_contact_translation.py'), ('repository-reading-probe.json', 'probe_repository_reading.py'), ('answer-state-probe.json', 'probe_answer_states.py')]
    probes += [(k + '-translation-probe.json', 'probe_' + k + '_translation.py') for k in ['format', 'sharing', 'preservation']]
    for name, script in probes:
        report = read(a.baseline, name)
        assert report['passed'] and report['release_acceptance'] is False and report['package_sha256'] == packages
        assert report['checker_sha256'] == sha(ROOT / 'scripts' / script)
        if name == 'contact-translation-probe.json':
            helpers(report)
            for source, digest in report['source_helper_sha256'].items(): assert digest == sha(a.english / source)
        keep(a.baseline / name, 'stock/' + name)
    for name in ['translation-audit.json', 'structure-audit.json']:
        assert read(a.baseline, name) == []; keep(a.baseline / name, 'stock/' + name)
    audit = json.loads(a.binding_audit.read_text())
    assert not audit['source_dirty'] and audit['source_commit'] == read(a.baseline, 'manifest.json')['checkouts']['english']['commit']
    assert all(not n['unbound_variables'] and not n['absent_entities'] for n in audit['templates'])
    keep(a.binding_audit, 'binding-audit.json'); keep(a.english / 'docs/repository-contact-reference.md', 'english-scope.md')
    rebuild = read(a.rebuild, 'manifest.json')
    assert rebuild['status'] == 'candidate' and all(not v['dirty'] for v in rebuild['checkouts'].values())
    assert {n: sha(a.rebuild / n) for n in packages} == packages
    keep(a.rebuild / 'manifest.json', 'rebuild-manifest.json'); keep(a.variant / 'runtime-comparison.json', 'runtime-comparison.json')
    keep(a.review_document, 'README.md')
    delta = (json.dumps(source_delta(a.prior_stock, a.baseline), indent=2) + '\n').encode()
    size = len(delta) + sum(f.stat().st_size for f, _ in copies)
    assert size <= 25_000_000 and len({n for _, n in copies}) == len(copies)
    a.destination.mkdir(parents=True, exist_ok=False); hashes = {}
    for source, name in copies:
        target = a.destination / name; target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, target); hashes[str(name)] = sha(target)
    target = a.destination / 'contact-source-delta.json'; target.write_bytes(delta); hashes[target.name] = sha(target)
    (a.destination / 'checksums.json').write_text(json.dumps(hashes, indent=2) + '\n')
    print(json.dumps({'hashed_files': len(hashes), 'bytes': size, 'destination': str(a.destination)}))


if __name__ == '__main__': main()
