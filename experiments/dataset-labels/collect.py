"""Freeze native label coverage; earlier overview/quality archives remain unchanged."""
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
    for name in ['before', 'after', 'superseded', 'fixtures', 'probe', 'native', 'output']: p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args(); assert not a.output.exists()
    structural, native = [json.loads(f.read_text()) for f in [a.probe, a.native]]
    assert structural['passed'] and len(structural['rows']) == 528
    assert native['passed'] and len(native['rows']) == 4
    assert structural['recipe_sha256'] == sha(Path(__file__).with_name('label_recipe.py'))
    assert structural['checker_sha256'] == sha(Path(__file__).with_name('label_probe.py'))
    assert native['checker_sha256'] == sha(Path(__file__).with_name('label_native.py'))
    life = json.loads((a.after / 'worker-lifecycle.json').read_text())
    assert life['stock_worker_restored'] and all(r['status'] == 'exited' for r in life['after'])
    a.output.mkdir(parents=True)
    def keep(path, name):
        target = a.output / name; target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(path, target)
    def write(name, data):
        target = a.output / name; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    keep(a.probe, 'provenance/structural.json'); keep(a.native, 'provenance/native.json')
    for name in ['worker-lifecycle.json', 'prototype.json']: keep(a.after / name, 'provenance/' + name)
    members = {}
    for phase, root, count in [('before', a.before, 6), ('after', a.after, 12)]:
        report = json.loads((root / 'missing-info-render-report.json').read_text())
        assert report['all_renders_succeeded'] and len(report['renders']) == count
        for name in ['manifest.json', 'missing-info-render-report.json']:
            keep(root / name, 'provenance/' + phase + '-' + name)
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
    for phase, root in [('before', a.before), ('after', a.after), ('superseded', a.superseded)]:
        cleanup = json.loads((root / 'owned-test-template-cleanup.json').read_text())
        assert cleanup['run_completed_successfully'] and len(cleanup['deleted']) == 2
        assert cleanup['project_references'] == cleanup['document_references'] == 0
        assert all(sha(root / name) == r['sha256'] for name, r in cleanup['backups'].items())
        keep(root / 'owned-test-template-cleanup.json', 'provenance/' + phase + '-owned-test-template-cleanup.json')
    for name in ['manifest.json', 'missing-info-render-report.json']:
        keep(a.superseded / name, 'provenance/superseded-' + name)
    for path in a.fixtures.rglob('*.json'):
        if 'knowledge-models' not in path.parts: keep(path, 'fixtures/' + str(path.relative_to(a.fixtures)))
    for path in Path(__file__).parent.glob('*.py'): keep(path, 'reproduce/' + path.name)
    for folder, names in [('submission-polish', ['polish_recipe.py', 'polish_probe.py']),
                          ('submission-notices', ['notice_recipe.py', 'notice_probe.py', 'notice_native.py'])]:
        for name in names: keep(ROOT / 'experiments' / folder / name, 'reproduce/' + name)
    for path in (a.after / 'visual').glob('*.png'): keep(path, 'visual/' + path.name)
    write('inventory.json', dict(prototype_only=True, source_version='0.3.43', source_repo_modified=False,
        translation_tree_modified=False, release_acceptance=False, global_switch_complete=False, microsoft_word_acceptance=False,
        structural_cases=528, native_pairs=4, native_artifacts=18, word_previews=6,
        superseded_baseline_render_count=6, deleted_owned_local_templates=6, collector_sha256=sha(Path(__file__))))
    print(a.output)


if __name__ == '__main__': main()
