"""Collect fresh evidence without modifying the earlier failed visual gate."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile
from lead_recipe import ROOT, ARCHIVE, SEAL, TARGET, baseline, patch
from lead_trial import CASES

sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'experiments/mixed-budget-header')]
from artifact_utils import sha
from compact import compact_source


def collect(before, long_before, after, failed_attempt, second_failed_attempt, fixtures, native, structure,
            quota, first_quota, second_quota, output):
    proof = json.loads(native.read_text())
    assert proof['content_contract_passed'] and len(proof['rows']) == 12
    assert not proof['passed'] and not proof['visual_gate_passed']
    assert proof['visual_blockers'] == [dict(case='ethics-long', language='chinese', profile='submission',
        engine='native_pdf', issue='page-count-increase', before_pages=7, after_pages=8)]
    structural = json.loads(structure.read_text()); assert structural['passed'] and len(structural['rows']) == 544
    allowance = json.loads(quota.read_text()); assert allowance['restored'] and allowance['before'] == allowance['after']
    first_allowance = json.loads(first_quota.read_text())
    assert first_allowance['restored'] and first_allowance['before'] == first_allowance['after'] == allowance['before']
    second_allowance = json.loads(second_quota.read_text())
    assert second_allowance['restored'] and second_allowance['before'] == second_allowance['after'] == allowance['before']
    life = json.loads((after / 'worker-lifecycle.json').read_text())
    assert life['stock_worker_restored'] and len(life['after']) == 4 and all(r['status'] == 'exited' for r in life['after'])
    roots = [('before-core', before, CASES[:2]), ('before-long', long_before, CASES[2:]), ('after', after, CASES)]
    for _, root, cases in roots:
        cleanup = json.loads((root / 'owned-test-template-cleanup.json').read_text())
        assert cleanup['run_completed_successfully'] and len(cleanup['deleted']) == 2
        assert cleanup['project_references'] == cleanup['document_references'] == 0
    failed_cleanup = json.loads((failed_attempt / 'owned-test-template-cleanup.json').read_text())
    assert failed_cleanup['run_completed_successfully'] and len(failed_cleanup['deleted']) == 2
    assert failed_cleanup['project_references'] == failed_cleanup['document_references'] == 0
    failed = json.loads((failed_attempt / 'native-2.json').read_text())
    assert not failed['passed'] and 'More pages' in failed['failure'] and 'ethics-long-submission-chinese' in failed['failure']
    second_cleanup = json.loads((second_failed_attempt / 'owned-test-template-cleanup.json').read_text())
    assert second_cleanup['run_completed_successfully'] and len(second_cleanup['deleted']) == 2
    assert second_cleanup['project_references'] == second_cleanup['document_references'] == 0
    second_failed = json.loads((second_failed_attempt / 'native-1.json').read_text())
    assert not second_failed['passed'] and 'More pages' in second_failed['failure']
    for key, name in [('checker_sha256', 'lead_native.py'), ('recipe_sha256', 'lead_recipe.py')]:
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
    keep(first_quota, 'provenance/first-storage-allowance.json')
    keep(second_quota, 'provenance/second-storage-allowance.json')
    for name in ['native-1.json', 'native-2.json', 'manifest.json', 'prototype.json',
                 'missing-info-render-report.json', 'owned-test-template-cleanup.json', 'worker-lifecycle.json']:
        keep(failed_attempt / name, 'failed-attempt/' + name)
    keep(failed_attempt / 'renders/ethics-long-submission-chinese.pdf', 'failed-attempt/zh-long-8-pages.pdf')
    keep(failed_attempt / 'renders/ethics-long-submission-chinese.pdf.fixture.json', 'failed-attempt/zh-long-8-pages.pdf.fixture.json')
    for language in ['english', 'chinese']:
        with zipfile.ZipFile(failed_attempt / (language + '.zip')) as package:
            candidate = json.loads(package.read('template/template.json'))
        final, operations = patch(baseline(language), language)
        file = next(f for f in final['files'] if f['fileName'] == TARGET)
        release = next(op for op in operations[TARGET] if op['kind'] == 'release-final-name-only-item')
        assert file['content'].count(release['after']) == 1
        file['content'] = file['content'].replace(release['after'], release['before'])
        with zipfile.ZipFile(second_failed_attempt / (language + '.zip')) as package:
            second_candidate = json.loads(package.read('template/template.json'))
        assert second_candidate == final
        write('failed-spacing-attempt/' + language + '.json', second_candidate)
        assert file['content'].count('<p class="answer-lead" style="margin-bottom: 0">') == 1
        file['content'] = file['content'].replace('<p class="answer-lead" style="margin-bottom: 0">', '<p class="answer-lead">')
        assert candidate == final, 'First attempt must differ only by owned lead spacing'
        write('failed-attempt/' + language + '.json', candidate)
    for name in ['native-1.json', 'manifest.json', 'prototype.json', 'missing-info-render-report.json',
                 'owned-test-template-cleanup.json', 'worker-lifecycle.json']:
        keep(second_failed_attempt / name, 'failed-spacing-attempt/' + name)
    for suffix in ['', '.fixture.json']:
        keep(second_failed_attempt / ('renders/ethics-long-submission-chinese.pdf' + suffix),
             'failed-spacing-attempt/zh-long-8-pages.pdf' + suffix)
    members = {}
    for phase, root, cases in roots:
        members[phase] = {}
        for name in ['manifest.json', 'prototype.json', 'missing-info-render-report.json', 'owned-test-template-cleanup.json']:
            keep(root / name, phase + '/' + name)
        for receipt in root.glob('word-preview-*.json'): keep(receipt, phase + '/' + receipt.name)
        for row in proof['rows']:
            if row['case'] not in cases: continue
            stem = row['case'] + '-' + row['profile'] + '-' + row['language']
            for fmt in ['html', 'pdf', 'docx']:
                source = root / 'renders' / (stem + '.' + fmt); name = phase + '/renders/' + source.name
                if phase == 'after': assert sha(source) == row['artifacts'][fmt]
                if fmt == 'html':
                    raw, fonts = compact_source(source.read_bytes())
                    target = output / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
                    write(name + '.compact.json', dict(original_html_sha256=sha(source), compact_html_sha256=sha(target),
                                                      fonts=fonts, native_pdf_entry_input=False))
                else: keep(source, name)
                keep(source.with_suffix('.' + fmt + '.fixture.json'), name + '.fixture.json')
            preview = root / 'word-preview' / (stem + '.pdf')
            side = 'after' if phase == 'after' else 'before'
            assert sha(preview) == row['rendered']['word_preview'][side + '_sha256']
            keep(preview, phase + '/word-preview/' + preview.name)
        for language in ['english', 'chinese']:
            with zipfile.ZipFile(root / (language + '.zip')) as package:
                members[phase][language] = {n: hashlib.sha256(package.read(n)).hexdigest() for n in package.namelist()}
                write(phase + '/' + language + '.json', json.loads(package.read('template/template.json')))
        if phase == 'after':
            for image in (root / 'visual').glob('*.png'): keep(image, 'visual/' + image.name)
    for language in ['english', 'chinese']:
        old, control, new = [members[phase][language] for phase in ['before-core', 'before-long', 'after']]
        assert old == control and old.keys() == new.keys()
        assert {n for n in old if old[n] != new[n]} == {'template/template.json'}
    write('provenance/package-members.json', members)
    for locale in ['en', 'zh-Hant']:
        for case in CASES:
            for suffix in ['.json', '.events.json']:
                keep(fixtures / locale / (case + suffix), 'fixtures/' + locale + '/' + case + suffix)
    write('fixtures/knowledge-model-sha256.json', {p.name: sha(p) for p in (fixtures / 'knowledge-models').iterdir() if p.is_file()})
    for source in Path(__file__).parent.glob('*.py'): keep(source, 'reproduce/' + source.name)
    write('inventory.json', dict(baseline_version='0.3.44', parent_prototype='2026-09-21-ethics-prompts',
        parent_seal_sha256=SEAL, source_integrated=False, translation_tree_modified=False, prototype_only=True,
        lead_separation_resolved=True, source_integration_allowed=False, changed_jinja_files=1, source_edit_count=6,
        structural_checks=544, native_pairs=12, native_artifacts=72, reused_native_artifacts=24, new_native_artifacts=48,
        unsuccessful_attempt_native_artifacts_generated=72, total_new_native_artifacts_generated_this_turn=120,
        word_previews=24, unchanged_native_review_controls=6,
        deleted_owned_local_templates_this_run=8, prior_cleanup_receipt_retained=True, storage_allowance_restored=True,
        unsuccessful_native_attempt_preserved=True,
        production_touched=False, visual_gate_passed=False, visual_blockers=proof['visual_blockers'],
        known_preexisting_visual_issues=proof['known_preexisting_visual_issues'], full_visual_acceptance=False,
        native_stress_scope='Long first purpose paragraph followed by authored list and table; first-list/table boundaries are structural tests only.',
        global_switch_complete=False, release_acceptance=False, microsoft_word_acceptance=False,
        collector_sha256=sha(Path(__file__))))
    return output


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['before', 'long-before', 'after', 'failed-attempt', 'second-failed-attempt', 'fixtures', 'native',
                 'structure', 'quota', 'first-quota', 'second-quota', 'output']:
        p.add_argument('--' + name, type=Path, required=True)
    print(collect(**vars(p.parse_args())))
