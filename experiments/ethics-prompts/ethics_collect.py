"""Create a fresh Q9 review archive after native checks and scoped cleanup."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'experiments/mixed-budget-header'), str(Path(__file__).parent)]
from artifact_utils import sha
from compact import compact_source
from ethics_trial import CASES


def collect(before, after, fixtures, native, structure, quota, output):
    proof = json.loads(native.read_text()); assert proof['passed'] and len(proof['rows']) == 8
    structure_proof = json.loads(structure.read_text()); assert structure_proof['passed'] and len(structure_proof['rows']) == 536
    allowance = json.loads(quota.read_text()); assert allowance['restored'] and allowance['before'] == allowance['after']
    life = json.loads((after / 'worker-lifecycle.json').read_text())
    assert life['stock_worker_restored'] and all(r['status'] == 'exited' for r in life['after'])
    for root in [before, after]:
        cleanup = json.loads((root / 'owned-test-template-cleanup.json').read_text())
        assert cleanup['run_completed_successfully'] and len(cleanup['deleted']) == 2
        assert cleanup['project_references'] == cleanup['document_references'] == 0
    for key, name in [('checker_sha256', 'ethics_native.py'), ('recipe_sha256', 'ethics_recipe.py')]:
        assert proof[key] == sha(Path(__file__).with_name(name))
    assert not output.exists(); output.mkdir(parents=True)
    def keep(source, name):
        target = output / name; target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, target)
    def write(name, data):
        target = output / name; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    for source, name in [(native, 'native'), (structure, 'structural'), (quota, 'storage-allowance')]:
        keep(source, 'provenance/' + name + '.json')
    keep(after / 'worker-lifecycle.json', 'provenance/worker-lifecycle.json')
    members = {}
    for phase, root in [('before', before), ('after', after)]:
        members[phase] = {}
        for name in ['manifest.json', 'prototype.json', 'missing-info-render-report.json', 'owned-test-template-cleanup.json']:
            keep(root / name, phase + '/' + name)
        for receipt in root.glob('word-preview-*.json'): keep(receipt, phase + '/' + receipt.name)
        for row in proof['rows']:
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
            assert sha(preview) == row['rendered']['word_preview'][phase + '_sha256']
            keep(preview, phase + '/word-preview/' + preview.name)
        for language in ['english', 'chinese']:
            with zipfile.ZipFile(root / (language + '.zip')) as package:
                members[phase][language] = {n: hashlib.sha256(package.read(n)).hexdigest() for n in package.namelist()}
                write(phase + '/' + language + '.json', json.loads(package.read('template/template.json')))
        for image in (root / 'visual').glob('*.png'): keep(image, 'visual/' + phase + '-' + image.name)
    for language in ['english', 'chinese']:
        a, b = [members[p][language] for p in ['before', 'after']]
        assert a.keys() == b.keys() and {n for n in a if a[n] != b[n]} == {'template/template.json'}
    write('provenance/package-members.json', members)
    for locale in ['en', 'zh-Hant']:
        for case in CASES:
            for suffix in ['.json', '.events.json']:
                keep(fixtures / locale / (case + suffix), 'fixtures/' + locale + '/' + case + suffix)
    write('fixtures/knowledge-model-sha256.json', {p.name: sha(p) for p in (fixtures / 'knowledge-models').iterdir() if p.is_file()})
    for source in Path(__file__).parent.glob('*.py'): keep(source, 'reproduce/' + source.name)
    write('inventory.json', dict(baseline_version='0.3.44', parent_prototype='2026-09-21-entity-labels',
        source_integrated=False, source_integration_allowed=False, translation_tree_modified=False, prototype_only=True,
        changed_jinja_files=1, source_edit_count=2, structural_checks=536, native_pairs=8,
        native_artifacts=48, word_previews=16, unchanged_native_controls=6,
        deleted_owned_local_templates=4, storage_allowance_restored=True, production_touched=False,
        visual_gate_passed=proof['visual_gate_passed'], visual_blockers=proof['visual_blockers'],
        global_switch_complete=False, release_acceptance=False, microsoft_word_acceptance=False,
        collector_sha256=sha(Path(__file__))))
    return output


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['before', 'after', 'fixtures', 'native', 'structure', 'quota', 'output']:
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args(); print(collect(**vars(a)))
