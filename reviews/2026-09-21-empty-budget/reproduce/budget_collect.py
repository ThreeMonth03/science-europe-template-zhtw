"""Collect fresh, explicitly unintegrated Q15 and Word diagnostic evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile
from budget_recipe import ROOT, ARCHIVE, SEAL, baseline, patch
from budget_trial import CASES

sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'experiments/mixed-budget-header')]
from artifact_utils import sha
from compact import compact_source


def collect(after, fixtures, native, structure, quota, diagnostic, output):
    proof = json.loads(native.read_text()); assert proof['content_contract_passed'] and len(proof['rows']) == 12
    assert not proof['passed'] and not proof['visual_gate_passed']
    assert proof['visual_blockers'] == [dict(case='ethics-long', language='chinese', profile='review',
        engine='word_preview', issue='header-only-table-continuation', preexisting=True)]
    structural = json.loads(structure.read_text()); assert structural['passed'] and len(structural['rows']) == 816
    allowance = json.loads(quota.read_text()); assert allowance['restored'] and allowance['before'] == allowance['after']
    life = json.loads((after / 'worker-lifecycle.json').read_text())
    assert life['stock_worker_restored'] and len(life['after']) == 4 and all(r['status'] == 'exited' for r in life['after'])
    cleanup = json.loads((after / 'owned-test-template-cleanup.json').read_text())
    assert cleanup['run_completed_successfully'] and len(cleanup['deleted']) == 2
    assert cleanup['project_references'] == cleanup['document_references'] == 0
    diag = json.loads((diagnostic / 'report.json').read_text()); assert diag['completed'] and len(diag['rows']) == 20
    assert diag['diagnostic_only'] and not diag['native_checked'] and not diag['release_acceptance']
    assert diag['script_sha256'] == sha(Path(__file__).with_name('diagnose_word.py'))
    for key, name in [('checker_sha256', 'budget_native.py'), ('recipe_sha256', 'budget_recipe.py')]:
        assert proof[key] == sha(Path(__file__).with_name(name))
    assert sha(ARCHIVE / 'checksums.json') == SEAL
    assert not output.exists(); output.mkdir(parents=True)

    def keep(source, name):
        target = output / name; target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, target)

    def write(name, data):
        target = output / name; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')

    for source, name in [(native, 'native'), (structure, 'structural'), (quota, 'storage-allowance'),
                         (after / 'worker-lifecycle.json', 'worker-lifecycle')]: keep(source, 'provenance/' + name + '.json')
    for name in ['manifest.json', 'prototype.json', 'missing-info-render-report.json', 'owned-test-template-cleanup.json']:
        keep(after / name, 'after/' + name)
    for receipt in after.glob('word-preview-*.json'): keep(receipt, 'after/' + receipt.name)
    for row in proof['rows']:
        stem = row['case'] + '-' + row['profile'] + '-' + row['language']
        for fmt in ['html', 'pdf', 'docx']:
            source = after / 'renders' / (stem + '.' + fmt); name = 'after/renders/' + source.name
            assert sha(source) == row['artifacts'][fmt]
            if fmt == 'html':
                raw, fonts = compact_source(source.read_bytes()); target = output / name
                target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
                write(name + '.compact.json', dict(original_html_sha256=sha(source), compact_html_sha256=sha(target), fonts=fonts))
            else: keep(source, name)
            keep(source.with_suffix('.' + fmt + '.fixture.json'), name + '.fixture.json')
        keep(after / 'word-preview' / (stem + '.pdf'), 'after/word-preview/' + stem + '.pdf')
    members = {}
    for language in ['english', 'chinese']:
        with zipfile.ZipFile(after / (language + '.zip')) as package:
            candidate = json.loads(package.read('template/template.json')); assert candidate == patch(baseline(language), language)[0]
            write('after/' + language + '.json', candidate)
            members[language] = {n: hashlib.sha256(package.read(n)).hexdigest() for n in package.namelist()}
    write('provenance/package-members.json', members)
    for locale in ['en', 'zh-Hant']:
        for case in CASES:
            for suffix in ['.json', '.events.json']:
                keep(fixtures / locale / (case + suffix), 'fixtures/' + locale + '/' + case + suffix)
    write('fixtures/knowledge-model-sha256.json', {p.name: sha(p) for p in (fixtures / 'knowledge-models').iterdir() if p.is_file()})
    for row in diag['rows']:
        stem = 'ethics-long-' + row['profile'] + '-' + row['language']
        assert sha(ARCHIVE / 'after/renders' / (stem + '.docx')) == row['source_sha256']
        name = stem + '-' + row['mode']
        for suffix, key in [('.docx', 'docx_sha256'), ('.pdf', 'pdf_sha256')]:
            assert sha(diagnostic / (name + suffix)) == row[key]
            keep(diagnostic / (name + suffix), 'word-diagnostic/' + name + suffix)
    keep(diagnostic / 'report.json', 'word-diagnostic/report.json')
    for image in (after / 'visual').glob('*.png'): keep(image, 'visual/' + image.name)
    for source in Path(__file__).parent.glob('*.py'): keep(source, 'reproduce/' + source.name)
    write('inventory.json', dict(baseline_version='0.3.44', parent_prototype='2026-09-21-ethics-lead',
        parent_seal_sha256=SEAL, source_integrated=False, source_integration_allowed=False,
        translation_tree_modified=False, prototype_only=True, changed_jinja_files=1, source_edit_count=3,
        structural_checks=816, native_pairs=12, new_native_artifacts=36, reused_native_artifacts=36,
        new_word_previews=12, reused_word_previews=12, unchanged_native_review_controls=6,
        word_diagnostic_variants=20, word_diagnostic_not_native_fix=True,
        pdf_tail_page_regression_resolved=True, deleted_owned_local_templates_this_run=2,
        storage_allowance_restored=True, production_touched=False, visual_gate_passed=False,
        visual_blockers=proof['visual_blockers'], full_visual_acceptance=False,
        global_switch_complete=False, release_acceptance=False, microsoft_word_acceptance=False,
        collector_sha256=sha(Path(__file__))))
    return output


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['after', 'fixtures', 'native', 'structure', 'quota', 'diagnostic', 'output']:
        p.add_argument('--' + name, type=Path, required=True)
    print(collect(**vars(p.parse_args())))
