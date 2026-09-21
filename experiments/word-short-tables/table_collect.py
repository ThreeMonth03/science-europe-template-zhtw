"""Fresh bounded Word acceptance evidence, separate from prior diagnostics."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import zipfile
from table_recipe import ROOT, HERE, ARCHIVE, SEAL, LUA, baseline, patch, sha
from table_trial import CASES

sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'experiments/mixed-budget-header')]
from compact import compact_source


def collect(after, fixtures, engine, quota, first, first_quota, translation, translation_asset, output):
    native = after / 'native-1.json'; proof = json.loads(native.read_text())
    assert proof['passed'] and proof['bounded_word_fix_verified'] and len(proof['rows']) == 12
    assert proof['checker_sha256'] == sha((HERE / 'table_native.py').read_bytes())
    structural = json.loads((engine / 'report.json').read_text()); assert structural['passed'] and len(structural['rows']) == 37
    for name, digest in structural['source_sha256'].items(): assert sha((HERE / name).read_bytes()) == digest
    preview = json.loads((engine / 'preview-verified.json').read_text()); assert preview['passed']
    assert preview['checker_sha256'] == sha((HERE / 'engine_preview.py').read_bytes())
    allowance = json.loads(quota.read_text()); assert allowance['restored'] and allowance['before'] == allowance['after']
    cleanup = json.loads((after / 'owned-test-template-cleanup.json').read_text())
    assert cleanup['run_completed_successfully'] and len(cleanup['deleted']) == 2
    assert cleanup['project_references'] == cleanup['document_references'] == 0
    life = json.loads((after / 'worker-lifecycle.json').read_text())
    assert life['stock_worker_restored'] and len(life['after']) == 4 and all(r['status'] == 'exited' for r in life['after'])
    assert sha((ARCHIVE / 'checksums.json').read_bytes()) == SEAL
    first_allowance = json.loads(first_quota.read_text())
    assert first_allowance['restored'] and first_allowance['before'] == first_allowance['after'] == allowance['before']
    first_cleanup = json.loads((first / 'owned-test-template-cleanup.json').read_text())
    assert first_cleanup['run_completed_successfully'] and len(first_cleanup['deleted']) == 2
    assert first_cleanup['project_references'] == first_cleanup['document_references'] == 0
    translation_reports = {}
    for label, folder in [('jinja', translation), ('asset', translation_asset)]:
        report = json.loads((folder / 'report.json').read_text())
        assert report['checker_sha256'] == sha((HERE / 'translation_probe.py').read_bytes())
        assert report['minimal_shared_files_probe'] and not report['full_source_integration']
        assert report['storage'] == label
        translation_reports[label] = report
    rejected = translation_reports['jinja']; alternative = translation_reports['asset']
    assert not rejected['passed'] and rejected['integration_blocked'] and rejected['translation_units'] == 7
    assert rejected['issue'] == 'machine-xml-misclassified-as-translatable-prose'
    assert alternative['passed'] and alternative['translation_units'] == 0
    assert not alternative['native_asset_pipeline_checked']
    for relative, digest in rejected['source_sha256'].items():
        assert sha((HERE / Path(relative).name).read_bytes()) == digest
        assert alternative['unchanged_file_sha256'][relative.removesuffix('.j2')] == digest
    assert not output.exists(); output.mkdir(parents=True)

    def keep(source, name):
        target = output / name; target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, target)

    def write(name, value):
        target = output / name; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

    for source, name in [(native, 'native'), (quota, 'storage-allowance'), (after / 'worker-lifecycle.json', 'worker-lifecycle')]:
        keep(source, 'provenance/' + name + '.json')
    keep(first_quota, 'initial-guard/storage-allowance.json')
    for name in ['native-1.json', 'manifest.json', 'prototype.json', 'missing-info-render-report.json',
                 'owned-test-template-cleanup.json', 'worker-lifecycle.json']:
        keep(first / name, 'initial-guard/' + name)
    for name in ['manifest.json', 'prototype.json', 'missing-info-render-report.json', 'owned-test-template-cleanup.json']:
        keep(after / name, 'after/' + name)
    for path in after.glob('word-preview-*.json'): keep(path, 'after/' + path.name)
    for row in proof['rows']:
        stem = row['case'] + '-' + row['profile'] + '-' + row['language']
        for fmt in ['html', 'pdf', 'docx']:
            source = after / 'renders' / (stem + '.' + fmt); name = 'after/renders/' + source.name
            assert sha(source.read_bytes()) == row['artifacts'][fmt]
            if fmt == 'html':
                raw, fonts = compact_source(source.read_bytes()); target = output / name
                target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
                write(name + '.compact.json', dict(original_html_sha256=sha(source.read_bytes()), compact_html_sha256=sha(raw), fonts=fonts))
            else: keep(source, name)
            keep(source.with_suffix('.' + fmt + '.fixture.json'), name + '.fixture.json')
        keep(after / 'word-preview' / (stem + '.pdf'), 'after/word-preview/' + stem + '.pdf')
    members = {}
    for language in ['english', 'chinese']:
        with zipfile.ZipFile(after / (language + '.zip')) as z:
            package = json.loads(z.read('template/template.json')); assert package == patch(baseline(language), language)
            assert z.read('template/assets/' + LUA) == (HERE / 'short-tables.lua').read_bytes()
            write('after/' + language + '.json', package)
            members[language] = {n: sha(z.read(n)) for n in z.namelist()}
        with zipfile.ZipFile(first / (language + '.zip')) as z:
            initial = json.loads(z.read('template/template.json'))
        write('initial-guard/' + language + '.json', initial)
        old_file = next(f for f in initial['files'] if f['fileName'] == 'src/word/short-tables.xml.j2')
        new_file = next(f for f in package['files'] if f['fileName'] == 'src/word/short-tables.xml.j2')
        guard = ("    {# Reject self-closing/attributed/additional paragraph variants as well. #}\n"
                 "    {%- for paragraphToken in row.split('<w:p')[1:] -%}\n"
                 "      {{- require(paragraphToken.startswith('>') or paragraphToken.startswith('Pr>') or paragraphToken.startswith('Style ')) -}}\n"
                 "    {%- endfor -%}\n")
        assert new_file['content'].count(guard) == 1
        assert old_file['content'] == new_file['content'].replace(guard, '', 1)
        old_file['content'] = new_file['content']; assert initial == package
    write('provenance/package-members.json', members)
    for locale in ['en', 'zh-Hant']:
        for case in CASES:
            for suffix in ['.json', '.events.json']: keep(fixtures / locale / (case + suffix), 'fixtures/' + locale + '/' + case + suffix)
    write('fixtures/knowledge-model-sha256.json', {p.name: sha(p.read_bytes()) for p in (fixtures / 'knowledge-models').iterdir() if p.is_file()})
    for path in engine.iterdir():
        if path.is_file(): keep(path, 'engine/' + path.name)
    for path in (after / 'visual').glob('*.png'): keep(path, 'visual/' + path.name)
    for label, folder in [('jinja', translation), ('asset', translation_asset)]:
        for path in folder.rglob('*'):
            if path.is_file(): keep(path, 'translation/' + label + '/' + str(path.relative_to(folder)))
    for path in HERE.iterdir():
        if path.is_file() and path.suffix in ['.py', '.lua', '.j2']: keep(path, 'reproduce/' + path.name)
    write('inventory.json', dict(baseline_version='0.3.44', parent_prototype='2026-09-21-empty-budget', parent_seal_sha256=SEAL,
        prototype_only=True, source_integrated=False, translation_tree_modified=False, production_touched=False,
        new_shared_word_files=2, changed_word_formats=2, existing_assets_unchanged=True,
        word_engine_cases=37, native_pairs=12, new_native_artifacts=36, reused_native_artifacts=36,
        new_word_previews=12, reused_word_previews=12, changed_native_word_tables=4, unchanged_native_word_controls=8,
        unchanged_html_pdf_pairs=12, bounded_word_fix_verified=True, scoped_visual_gate_passed=True,
        inherited_pdf_tail_page_fix_preserved=True, deleted_owned_local_templates_this_run=4, storage_allowance_restored=True,
        initial_guard_native_artifacts_generated=36, total_new_native_artifacts_generated_this_turn=72,
        source_integration_pending=True, source_integration_allowed=False,
        integration_blocker='machine-xml-misclassified-as-translatable-prose',
        unexpected_machine_translation_units=7, asset_translation_rehearsal_passed=True,
        native_asset_pipeline_checked=False, full_visual_acceptance=False, global_switch_complete=False,
        release_acceptance=False, microsoft_word_acceptance=False, collector_sha256=sha(Path(__file__).read_bytes())))
    return output


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['after', 'fixtures', 'engine', 'quota', 'first', 'first-quota', 'translation', 'translation-asset', 'output']:
        p.add_argument('--' + name, type=Path, required=True)
    print(collect(**vars(p.parse_args())))
