"""Collect a new immutable experiment; never overwrite or reseal prior reviews."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'experiments/mixed-budget-header')]
from artifact_utils import sha
from compact import compact_source


def collect(before, after, fixtures, native, structure, quota, failed, output):
    proof = json.loads(native.read_text()); assert proof['passed'] and len(proof['rows']) == 4
    structural = json.loads(structure.read_text()); assert structural['passed'] and len(structural['rows']) == 1056
    allowance = json.loads(quota.read_text()); assert allowance['restored'] and allowance['before'] == allowance['after']
    lifecycle = json.loads((after / 'worker-lifecycle.json').read_text())
    assert lifecycle['stock_worker_restored'] and all(r['status'] == 'exited' for r in lifecycle['after'])
    for root, count in [(before, 2), (after, 2), (failed, 1)]:
        cleanup = json.loads((root / 'owned-test-template-cleanup.json').read_text())
        assert len(cleanup['deleted']) == count and cleanup['project_references'] == cleanup['document_references'] == 0
    assert proof['checker_sha256'] == sha(Path(__file__).with_name('entity_native.py'))
    assert proof['recipe_sha256'] == sha(Path(__file__).with_name('entity_recipe.py'))
    assert not output.exists(); output.mkdir(parents=True)
    def keep(source, name):
        target = output / name; target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, target)
    def write(name, data):
        target = output / name; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    for source, name in [(native, 'native'), (structure, 'structural'), (quota, 'storage-allowance')]:
        keep(source, 'provenance/' + name + '.json')
    keep(after / 'worker-lifecycle.json', 'provenance/worker-lifecycle.json')
    keep(after / 'prototype.json', 'provenance/prototype.json')
    for name in ['missing-info-render-report.json', 'owned-test-template-cleanup.json']:
        keep(failed / name, 'provenance/failed-' + name)
    keep(failed / 'render-entity-labels-review-english-html.log', 'provenance/failed-render.log')
    members = {}
    for phase, root in [('before', before), ('after', after)]:
        members[phase] = {}
        for name in ['manifest.json', 'missing-info-render-report.json', 'owned-test-template-cleanup.json',
                     'word-preview-entity-labels-review-entity-labels-submission.json']:
            keep(root / name, phase + '/' + name)
        for row in proof['rows']:
            stem = 'entity-labels-' + row['profile'] + '-' + row['language']
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
        old, new = [members[p][language] for p in ['before', 'after']]
        assert old.keys() == new.keys()
        assert {n for n in old if old[n] != new[n]} == {'template/template.json'}
    write('provenance/package-members.json', members)
    for locale in ['en', 'zh-Hant']:
        for suffix in ['.json', '.events.json']:
            keep(fixtures / locale / ('entity-labels' + suffix), 'fixtures/' + locale + '/entity-labels' + suffix)
    write('fixtures/knowledge-model-sha256.json', {p.name: sha(p) for p in (fixtures / 'knowledge-models').iterdir() if p.is_file()})
    for source in Path(__file__).parent.glob('*.py'): keep(source, 'reproduce/' + source.name)
    write('inventory.json', dict(baseline_version='0.3.44', source_integrated=False, translation_tree_modified=False,
        prototype_only=True, changed_jinja_files=5, structural_checks=1056, native_pairs=4,
        native_artifacts=24, word_previews=8, deleted_owned_local_templates=5,
        failed_quota_run_retained=True, storage_allowance_restored=True, production_touched=False,
        global_switch_complete=False, release_acceptance=False, microsoft_word_acceptance=False,
        collector_sha256=sha(Path(__file__))))
    return output


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['before', 'after', 'fixtures', 'native', 'structure', 'quota', 'failed', 'output']:
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args(); print(collect(**vars(a)))
