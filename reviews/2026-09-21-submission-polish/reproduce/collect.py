"""Freeze the bounded overview/quality trial without modifying earlier reviews."""
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


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['before', 'after', 'fixtures', 'probe', 'native', 'output']: p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args(); assert not a.output.exists()
    structural, native = [json.loads(p.read_text()) for p in [a.probe, a.native]]
    assert structural['passed'] and len(structural['rows']) == 780
    assert native['passed'] and len(native['rows']) == 12
    assert structural['recipe_sha256'] == sha(Path(__file__).with_name('polish_recipe.py'))
    assert structural['checker_sha256'] == sha(Path(__file__).with_name('polish_probe.py'))
    assert native['checker_sha256'] == sha(Path(__file__).with_name('polish_native.py'))
    assert native['shared_checker_sha256'] == sha(ROOT / 'experiments/submission-notices/notice_native.py')
    life = json.loads((a.after / 'worker-lifecycle.json').read_text())
    assert life['stock_worker_restored'] and all(r['status'] == 'exited' for r in life['after'])
    assert life['deleted_owned_templates'] == 4 and not life['production_touched']
    a.output.mkdir(parents=True)
    def keep(path, name):
        target = a.output / name; target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(path, target)
    def write(name, value):
        target = a.output / name; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    keep(a.probe, 'provenance/structural.json'); keep(a.native, 'provenance/native.json')
    for name in ['worker-lifecycle.json', 'prototype.json']: keep(a.after / name, 'provenance/' + name)
    members = {}
    for phase, root, count in [('before', a.before, 18), ('after', a.after, 36)]:
        cleanup = json.loads((root / 'owned-test-template-cleanup.json').read_text())
        assert cleanup['run_completed_successfully'] and len(cleanup['deleted']) == 2
        assert cleanup['project_references'] == cleanup['document_references'] == 0
        assert all(sha(root / name) == receipt['sha256'] for name, receipt in cleanup['backups'].items())
        for name in ['manifest.json', 'missing-info-render-report.json', 'owned-test-template-cleanup.json']:
            keep(root / name, 'provenance/' + phase + '-' + name)
        renders = json.loads((root / 'missing-info-render-report.json').read_text())
        assert renders['all_renders_succeeded'] and len(renders['renders']) == count
        previews = {}
        for path in root.glob('word-preview-*.json'):
            receipt = json.loads(path.read_text()); assert receipt['completed']
            keep(path, 'provenance/' + phase + '-' + path.name)
            for row in receipt['rows']:
                assert row['name'] not in previews
                assert sha(root / 'renders' / (row['name'] + '.docx')) == row['docx_sha256']
                assert sha(root / 'word-preview' / (row['name'] + '.pdf')) == row['preview_sha256']
                previews[row['name']] = row
        assert len(previews) == count // 3
        for stem in previews:
            for fmt in ['html', 'pdf', 'docx']:
                source = root / 'renders' / (stem + '.' + fmt)
                if fmt == 'html':
                    compact, fonts = compact_source(source.read_bytes())
                    target = a.output / phase / 'renders' / source.name; target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(compact)
                    write(phase + '/renders/' + source.name + '.compact.json', dict(original_html_sha256=sha(source), compact_html_sha256=sha(target), fonts=fonts, native_pdf_entry_input=False))
                else: keep(source, phase + '/renders/' + source.name)
                keep(source.with_suffix('.' + fmt + '.fixture.json'), phase + '/renders/' + source.name + '.fixture.json')
            keep(root / 'word-preview' / (stem + '.pdf'), phase + '/word-preview/' + stem + '.pdf')
        members[phase] = {}
        for language in ['english', 'chinese']:
            with zipfile.ZipFile(root / (language + '.zip')) as package:
                write('package/' + phase + '-' + language + '.json', json.loads(package.read('template/template.json')))
                members[phase][language] = {name: hashlib.sha256(package.read(name)).hexdigest() for name in package.namelist()}
    write('provenance/package-members.json', members)
    for path in Path(__file__).parent.glob('*.py'): keep(path, 'reproduce/' + path.name)
    for name in ['notice_recipe.py', 'notice_probe.py', 'notice_native.py']:
        keep(ROOT / 'experiments/submission-notices' / name, 'reproduce/' + name)
    keep(ROOT / 'pipeline.yml', 'reproduce/pipeline.yml')
    for path in a.fixtures.rglob('*.json'):
        if 'knowledge-models' not in path.parts: keep(path, 'fixtures/' + str(path.relative_to(a.fixtures)))
    for path in (a.after / 'visual').glob('*.png'): keep(path, 'visual/' + path.name)
    write('inventory.json', dict(prototype_only=True, source_version='0.3.43', source_repo_modified=False,
        translation_tree_modified=False, global_switch_complete=False, release_acceptance=False,
        microsoft_word_acceptance=False, structural_cases=780, native_pairs=12, native_artifacts=54,
        word_previews=18, deleted_owned_local_templates=4, collector_sha256=sha(Path(__file__))))
    print(a.output)


if __name__ == '__main__': main()
