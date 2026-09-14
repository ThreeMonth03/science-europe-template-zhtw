"""Archive the bounded repository-reading experiment, without overriding failures."""
import argparse
import json
import shutil
import zipfile
from pathlib import Path
from lxml import etree
from artifact_utils import sha

ROOT = Path(__file__).resolve().parents[1]
STOCK = {'support-mixed', 'empty', 'repository-gap', 'repository-long'}
TABLES = STOCK - {'empty'}
REPORTS = ['preservation', 'sharing', 'polish', 'format', 'reading', 'quality', 'repository']


def read(root, name): return json.loads((root / name).read_text())


def reference_delta(before, after):
    with zipfile.ZipFile(before) as z: old = {n: z.read(n) for n in z.namelist()}
    with zipfile.ZipFile(after) as z: new = {n: z.read(n) for n in z.namelist()}
    assert old.keys() == new.keys()
    assert [n for n in old if old[n] != new[n]] == ['word/styles.xml']
    root = etree.fromstring(new['word/styles.xml']); removed = []
    ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
    for style in list(root):
        if style.get(ns + 'styleId') in ['PilotRepositoryLead', 'PilotRepositoryItem']:
            removed.append(style.get(ns + 'styleId')); root.remove(style)
    assert set(removed) == {'PilotRepositoryLead', 'PilotRepositoryItem'}
    assert etree.tostring(root, method='c14n') == etree.tostring(etree.fromstring(old['word/styles.xml']), method='c14n')
    return {'only_added_styles': removed, 'all_other_zip_parts_byte_identical': True}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['baseline', 'variant', 'prior-stock', 'prior-tables', 'rebuild', 'destination', 'review-document', 'english', 'binding-audit']:
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args(); assert not a.destination.exists(), 'Never overwrite a review'
    packages = {n: sha(a.baseline / n) for n in ['english.zip', 'chinese.zip']}; copies = []
    def keep(path, name): copies.append((path, Path(name)))
    comparison = read(a.variant, 'runtime-comparison.json')
    assert comparison['selected_comparison_passed'] and comparison['release_acceptance'] is False
    assert comparison['package_sha256'] == packages and comparison['checker_sha256'] == sha(ROOT / 'scripts/compare_runtime_outputs.py')
    assert {(r['case'], r['language']) for r in comparison['checks']} == {(c, l) for c in TABLES for l in ['english', 'chinese']}
    for side, root, prior, cases in [('stock', a.baseline, a.prior_stock, STOCK), ('tables', a.variant, a.prior_tables, TABLES)]:
        pairs = {(c, l) for c in cases for l in ['english', 'chinese']}
        m = read(root, 'manifest.json'); pilot = read(root, 'pilot-report.json'); renders = read(root, 'render-results.json')
        assert m['status'] == ('candidate' if side == 'stock' else 'runtime-experiment') and all(not v['dirty'] for v in m['checkouts'].values())
        assert pilot['semantic_checks_passed'] and pilot['checker_sha256'] == sha(ROOT / 'scripts/run_pilot.py')
        assert len(renders) == len(pairs) * 3 and all(r['passed'] for r in renders)
        assert {(r['case'], r['language'], r['format']) for r in renders} == {(c, l, f) for c, l in pairs for f in ['html', 'pdf', 'docx']}
        expected = {(c, l, code) for c, l in pairs if c != 'empty' for code in ['markdown-table-unsupported', 'docx-table-missing']} if side == 'stock' else set()
        assert {(r['case'], r['language'], r['code']) for r in pilot['blocking_issues']} == expected
        assert len(pilot['blocking_issues']) == len(expected) and pilot['passed'] == (not expected)
        for n, digest in packages.items(): assert digest == sha(root / n) == m['sha256'][n] == pilot['package_sha256'][n]
        for name, digest in pilot['sha256'].items(): assert sha(root / 'renders' / name) == digest
        for name, digest in comparison['artifact_sha256'][side].items(): assert sha(root / name) == digest
        for kind in REPORTS:
            name = kind + '-report.json'; r = read(root, name)
            assert r['selected_checks_passed'] and r['release_acceptance'] is False and r['package_sha256'] == packages
            assert r['checker_sha256'] == sha(ROOT / f'scripts/check_{kind}_outputs.py')
            assert len(r['rows']) == len(pairs) and {(v['case'], v['language']) for v in r['rows']} == pairs
            for path, digest in r.get('artifact_sha256', {}).items(): assert sha(root / path) == digest
            for path, digest in r.get('render_sha256', {}).items(): assert sha(root / 'renders' / path) == digest
            for path, digest in r.get('helper_sha256', {}).items(): assert sha(ROOT / 'scripts' / path) == digest
            for key, path in [('text_extractor_sha256', 'check_narrative_outputs.py'), ('date_helper_sha256', 'check_polish_outputs.py')]:
                if key in r: assert r[key] == sha(ROOT / 'scripts' / path)
            if kind == 'repository':
                assert r['prior_package_sha256'] == {n: sha(prior / n) for n in packages}
                for path, digest in r['prior_artifact_sha256'].items(): assert sha(prior / path) == digest
                assert sum(v['controlled_question_comparisons'] for v in r['rows']) == (60 if side == 'stock' else 30)
                assert set(r['new_cases_without_prior']) == {'repository-gap', 'repository-long'}
            keep(root / name, f'{side}/{name}')
        for name in ['manifest.json', 'pilot-report.json', 'render-results.json']: keep(root / name, f'{side}/{name}')
        for case, lang in sorted(pairs):
            for fmt in ['pdf', 'docx']:
                for extra in ['', '.fixture.json']:
                    name = f'{case}-{lang}.{fmt}{extra}'; keep(root / 'renders' / name, f'{side}/{name}')
            name = f'{case}-{lang}.pdf'; keep(root / 'word-preview' / name, f'{side}/word-preview/{name}')
    for name, script in [('repository-reading-probe.json', 'probe_repository_reading.py'), ('answer-state-probe.json', 'probe_answer_states.py')] + [(k + '-translation-probe.json', 'probe_' + k + '_translation.py') for k in ['preservation', 'sharing', 'format']]:
        r = read(a.baseline, name)
        assert r['passed'] and r['release_acceptance'] is False and r['package_sha256'] == packages
        assert r['checker_sha256'] == sha(ROOT / 'scripts' / script)
        keep(a.baseline / name, 'stock/' + name)
    for name in ['translation-audit.json', 'structure-audit.json']:
        assert read(a.baseline, name) == []; keep(a.baseline / name, 'stock/' + name)
    audit = json.loads(a.binding_audit.read_text())
    assert not audit['source_dirty'] and audit['source_commit'] == read(a.baseline, 'manifest.json')['checkouts']['english']['commit']
    assert all(not q['unbound_variables'] and not q['absent_entities'] for q in audit['templates'])
    keep(a.binding_audit, 'binding-audit.json'); keep(a.english / 'docs/repository-reading.md', 'english-scope.md')
    rebuild = read(a.rebuild, 'manifest.json')
    assert rebuild['status'] == 'candidate' and all(not v['dirty'] for v in rebuild['checkouts'].values())
    assert {n: sha(a.rebuild / n) for n in packages} == packages
    keep(a.rebuild / 'manifest.json', 'rebuild-manifest.json'); keep(a.variant / 'runtime-comparison.json', 'runtime-comparison.json')
    keep(a.review_document, 'README.md')
    delta = {}
    for side in ['en', 'translated']:
        old, new = [{str(f.relative_to(r / side)): sha(f) for f in sorted((r / side / 'src').rglob('*')) if f.is_file()} for r in [a.prior_stock, a.baseline]]
        assert old.keys() == new.keys()
        changes = [f for f in old if old[f] != new[f]]
        assert changes == ['src/layout.css', 'src/questions/11-data-preservation.html.j2', 'src/word/pilot.lua', 'src/word/reference.docx'], (side, changes)
        delta[side] = {'changed_source_paths': changes, 'prior_source_sha256': old, 'source_sha256': new,
                       'reference_delta': reference_delta(a.prior_stock / side / 'src/word/reference.docx', a.baseline / side / 'src/word/reference.docx')}
    delta_bytes = (json.dumps(delta, indent=2) + '\n').encode(); size = len(delta_bytes) + sum(f.stat().st_size for f, _ in copies)
    assert size <= 25_000_000 and len({n for _, n in copies}) == len(copies)
    a.destination.mkdir(parents=True, exist_ok=False); hashes = {}
    for source, name in copies:
        target = a.destination / name; target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, target); hashes[str(name)] = sha(target)
    target = a.destination / 'repository-source-delta.json'; target.write_bytes(delta_bytes); hashes[target.name] = sha(target)
    (a.destination / 'checksums.json').write_text(json.dumps(hashes, indent=2) + '\n')
    print(json.dumps({'hashed_files': len(hashes), 'bytes': size, 'destination': str(a.destination)}))


if __name__ == '__main__': main()
