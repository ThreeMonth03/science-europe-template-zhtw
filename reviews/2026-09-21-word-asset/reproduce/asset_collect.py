"""Freeze asset-native parity separately from the full-source build rehearsal."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import zipfile
from asset_recipe import ROOT, HERE, ARCHIVE, SEAL, XML, LUA, CASES, baseline, helper, patch, sha

sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'experiments/mixed-budget-header')]
from compact import compact_source


def collect(after, fixtures, quota, source, initial_source, parity, initial_parity, cli_failure, output):
    proof = json.loads((after / 'native-2.json').read_text())
    assert proof['passed'] and proof['native_asset_pipeline_checked'] and len(proof['rows']) == 12
    assert proof['checker_sha256'] == sha((HERE / 'asset_native.py').read_bytes())
    assert proof['recipe_sha256'] == sha((HERE / 'asset_recipe.py').read_bytes())
    allowance = json.loads(quota.read_text()); assert allowance['restored'] and allowance['before'] == allowance['after']
    cleanup = json.loads((after / 'owned-test-template-cleanup.json').read_text())
    assert cleanup['run_completed_successfully'] and len(cleanup['deleted']) == 2
    assert cleanup['project_references'] == cleanup['document_references'] == 0
    life = json.loads((after / 'worker-lifecycle.json').read_text())
    assert life['stock_worker_restored'] and len(life['after']) == 4 and all(r['status'] == 'exited' for r in life['after'])
    assert sha((ARCHIVE / 'checksums.json').read_bytes()) == SEAL
    initial = json.loads((initial_parity / 'report.json').read_text()); final = json.loads((parity / 'report.json').read_text())
    assert not initial['passed'] and sum(not r['passed'] for r in initial['rows']) == 102
    assert final['passed'] and len(final['rows']) == len(initial['rows']) == 3312
    for report in [initial, final]: assert report['checker_sha256'] == sha((HERE / 'source_parity.py').read_bytes())
    assert not output.exists(); output.mkdir(parents=True)

    def keep(path, name):
        target = output / name; target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(path, target)

    def write(name, value):
        target = output / name; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

    for path, name in [(after / 'native-2.json', 'native'), (quota, 'storage-allowance'), (after / 'worker-lifecycle.json', 'worker-lifecycle')]:
        keep(path, 'provenance/' + name + '.json')
    for name in ['manifest.json', 'prototype.json', 'missing-info-render-report.json', 'owned-test-template-cleanup.json']:
        keep(after / name, 'after/' + name)
    for path in after.glob('word-preview-*.json'): keep(path, 'after/' + path.name)
    for row in proof['rows']:
        stem = row['case'] + '-' + row['profile'] + '-' + row['language']
        for fmt in ['html', 'pdf', 'docx']:
            path = after / 'renders' / (stem + '.' + fmt); name = 'after/renders/' + path.name
            assert sha(path.read_bytes()) == row['artifacts'][fmt]
            if fmt == 'html':
                raw, fonts = compact_source(path.read_bytes()); target = output / name
                target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
                write(name + '.compact.json', dict(original_html_sha256=sha(path.read_bytes()), compact_html_sha256=sha(raw), fonts=fonts))
            else: keep(path, name)
            keep(path.with_suffix('.' + fmt + '.fixture.json'), name + '.fixture.json')
        keep(after / 'word-preview' / (stem + '.pdf'), 'after/word-preview/' + stem + '.pdf')
    members = {}
    prior_members = json.loads((ARCHIVE / 'provenance/package-members.json').read_text())
    for language in ['english', 'chinese']:
        with zipfile.ZipFile(after / (language + '.zip')) as z:
            data = json.loads(z.read('template/template.json')); assert data == patch(baseline(language), language)
            assert z.read('template/assets/' + XML) == helper()
            write('after/' + language + '.json', data); members[language] = {n: sha(z.read(n)) for n in z.namelist()}
        previous = prior_members[language]
        assert set(members[language]) - set(previous) == {'template/assets/' + XML}
        assert {n for n in previous if members[language][n] != previous[n]} == {'template/template.json'}
    write('provenance/package-members.json', members)
    for locale in ['en', 'zh-Hant']:
        for case in CASES:
            for suffix in ['.json', '.events.json']: keep(fixtures / locale / (case + suffix), 'fixtures/' + locale + '/' + case + suffix)
    write('fixtures/knowledge-model-sha256.json', {p.name: sha(p.read_bytes()) for p in (fixtures / 'knowledge-models').iterdir() if p.is_file()})

    for label, build, comparison in [('initial-source', initial_source, initial_parity), ('source-rehearsal', source, parity)]:
        build_proof = json.loads((build / 'source-build.json').read_text())
        comparison_proof = json.loads((comparison / 'report.json').read_text())
        assert build_proof['passed'] and build_proof['machine_helper_translation_units'] == 0
        for language in ['english', 'chinese']:
            path = build / (language + '.zip')
            assert sha(path.read_bytes()) == build_proof['packages'][language]['sha256'] == comparison_proof['package_sha256'][language]
            with zipfile.ZipFile(path) as z:
                write(label + '/' + language + '.json', json.loads(z.read('template/template.json')))
                assets = {n: sha(z.read(n)) for n in z.namelist() if n.startswith('template/assets/')}
            assert assets == build_proof['packages'][language]['asset_sha256']
            assert assets == {n: d for n, d in members[language].items() if n.startswith('template/assets/')}
            keep(build / (language + '-build.log'), label + '/' + language + '-build.log')
        for name in ['source-proof.json', 'source-build.json', 'translation-delta.json', 'translation-preflight.json', 'migration.json', 'structure-audit.json']:
            keep(build / name, label + '/' + name)
        keep(comparison / 'report.json', label + '/parity.json')
        source_proof = json.loads((build / 'source-proof.json').read_text())
        for name, digest in source_proof['after_source_sha256'].items():
            if name not in source_proof['before_source_sha256'] or source_proof['before_source_sha256'][name] != digest:
                assert sha((build / 'source' / name).read_bytes()) == digest
                keep(build / 'source' / name, label + '/source/' + name)
        keep(build / 'source/template.json', label + '/source/template.json')
        blanks = json.loads((build / 'translation-preflight.json').read_text())['blanks']
        for unit in blanks: keep(build / 'reviewed' / unit['document_path'], label + '/reviewed/' + unit['document_path'])
    for path in (initial_source / 'reproduce').glob('*.py'): keep(path, 'initial-source/reproduce/' + path.name)
    for stem in ['chinese-False-html-review', 'chinese-False-html-submission']:
        for suffix in ['.diff', '-before.html', '-after.html']: keep(initial_parity / (stem + suffix), 'initial-source/examples/' + stem + suffix)
    keep(cli_failure / 'missing-info-render-report.json', 'diagnostics/fixture-cli-failure.json')
    keep(after / 'native-1.json', 'diagnostics/initial-checker.json')
    prior_checker = (HERE / 'asset_native.py').read_text().replace(
        "assert json.loads(json.dumps(visible)) == previous['rendered'][engine]['after']",
        "assert visible == previous['rendered'][engine]['after']", 1)
    assert sha(prior_checker.encode()) == json.loads((after / 'native-1.json').read_text())['checker_sha256']
    (output / 'diagnostics/initial-asset-native.py').write_text(prior_checker)
    for path in HERE.glob('*.py'): keep(path, 'reproduce/' + path.name)
    delta = json.loads((source / 'translation-delta.json').read_text())
    assert delta['before_units'] == delta['retained_pairs'] == 762 and delta['after_units'] == 767 and not delta['removed']
    write('inventory.json', dict(parent_prototype=ARCHIVE.name, parent_seal_sha256=SEAL, baseline_version='0.3.44',
        prototype_only=True, source_integrated=False, translation_tree_modified=False, production_touched=False,
        native_asset_pipeline_checked=True, native_pairs=12, new_native_artifacts=36, new_word_previews=12,
        reused_native_artifacts=36, reused_word_previews=12, all_html_pdf_word_outputs_preserved=True,
        full_source_translation_rehearsal_passed=True, full_source_structural_checks=3312,
        initial_source_structural_failures=102, machine_translation_units=0, retained_translation_pairs=762, new_translation_units=5,
        full_source_native_render_checked=False, source_integration_pending=True, source_integration_allowed=False,
        pending_gate='paired-source-integration-and-native-rebuilt-package-verification',
        full_visual_acceptance=False, global_switch_complete=False, release_acceptance=False, microsoft_word_acceptance=False,
        deleted_owned_local_templates=2, storage_allowance_restored=True, collector_sha256=sha(Path(__file__).read_bytes())))
    return output


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['after', 'fixtures', 'quota', 'source', 'initial-source', 'parity', 'initial-parity', 'cli-failure', 'output']:
        p.add_argument('--' + name, type=Path, required=True)
    print(collect(**vars(p.parse_args())))
