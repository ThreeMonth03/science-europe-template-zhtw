"""Freeze the marked-notice trial, including quota failure and scoped cleanup."""
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
    for name in ['before', 'after', 'failed', 'fixtures', 'comparison', 'probe', 'output']:
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args(); assert not a.output.exists()
    comparison = json.loads(a.comparison.read_text()); probe = json.loads(a.probe.read_text())
    assert comparison['selected_checks_passed'] and len(comparison['rows']) == 12
    assert comparison['checker_sha256'] == sha(Path(__file__).with_name('notice_native.py'))
    assert probe['selected_checks_passed'] and len(probe['rows']) == 264
    assert probe['checker_sha256'] == sha(Path(__file__).with_name('notice_probe.py'))
    assert probe['recipe_sha256'] == sha(Path(__file__).with_name('notice_recipe.py'))
    life = json.loads((a.after / 'worker-lifecycle.json').read_text())
    assert life['stock_worker_restored'] and all(r['status'] == 'exited' for r in life['after'])
    assert not life['production_touched']
    cleanups = {}
    for phase, root, count in [('before', a.before, 2), ('failed', a.failed, 1), ('after', a.after, 2)]:
        report = json.loads((root / 'owned-test-template-cleanup.json').read_text())
        assert len(report['deleted']) == count
        assert report['project_references'] == report['document_references'] == 0
        for name, backup in report['backups'].items(): assert sha(root / name) == backup['sha256']
        cleanups[phase] = report
    a.output.mkdir(parents=True)
    def keep(path, name):
        target = a.output / name; target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(path, target)
    def write(name, value):
        target = a.output / name; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    keep(a.comparison, 'provenance/native.json'); keep(a.probe, 'provenance/structural.json')
    keep(a.after / 'worker-lifecycle.json', 'provenance/lifecycle.json')
    keep(a.after / 'prototype.json', 'provenance/prototype.json')
    for phase, root in [('before', a.before), ('after', a.after)]:
        for name in ['manifest.json', 'missing-info-render-report.json']:
            keep(root / name, 'provenance/' + phase + '-' + name)
        write('provenance/' + phase + '-cleanup.json', cleanups[phase])
        expected_count = 18 if phase == 'before' else 36
        assert len(json.loads((root / 'missing-info-render-report.json').read_text())['renders']) == expected_count
        preview_rows = {}
        for path in root.glob('word-preview-*.json'):
            receipt = json.loads(path.read_text()); assert receipt['completed']
            keep(path, 'provenance/' + phase + '-' + path.name)
            for row in receipt['rows']:
                assert row['name'] not in preview_rows
                assert sha(root / 'renders' / (row['name'] + '.docx')) == row['docx_sha256']
                assert sha(root / 'word-preview' / (row['name'] + '.pdf')) == row['preview_sha256']
                preview_rows[row['name']] = row
        assert len(preview_rows) == expected_count // 3
        for stem in preview_rows:
            for fmt in ['html', 'pdf', 'docx']:
                source = root / 'renders' / (stem + '.' + fmt)
                if fmt == 'html':
                    compact, fonts = compact_source(source.read_bytes())
                    target = a.output / phase / 'renders' / source.name; target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(compact)
                    write(phase + '/renders/' + source.name + '.compact.json', dict(original_html_sha256=sha(source),
                        compact_html_sha256=sha(target), fonts=fonts, native_pdf_entry_input=False))
                else: keep(source, phase + '/renders/' + source.name)
                keep(source.with_suffix('.' + fmt + '.fixture.json'), phase + '/renders/' + source.name + '.fixture.json')
            keep(root / 'word-preview' / (stem + '.pdf'), phase + '/word-preview/' + stem + '.pdf')
    package_members = {}
    for language in ['english', 'chinese']:
        package_members[language] = {}
        for phase, root in [('before', a.before), ('after', a.after)]:
            with zipfile.ZipFile(root / (language + '.zip')) as package:
                write('package/' + phase + '-' + language + '.json', json.loads(package.read('template/template.json')))
                package_members[language][phase] = {name: hashlib.sha256(package.read(name)).hexdigest() for name in package.namelist()}
    write('provenance/package-members.json', package_members)
    for path in Path(__file__).parent.glob('*.py'): keep(path, 'reproduce/' + path.name)
    keep(ROOT / 'scripts/cleanup_owned_runtime_templates.py', 'reproduce/cleanup_owned_runtime_templates.py')
    keep(ROOT / 'pipeline.yml', 'reproduce/pipeline.yml')
    for path in a.fixtures.rglob('*.json'):
        if 'knowledge-models' not in path.parts: keep(path, 'fixtures/' + str(path.relative_to(a.fixtures)))
    write('provenance/failed-cleanup.json', cleanups['failed'])
    for name in ['missing-info-render-report.json', 'render-empty-review-english-html.log']:
        keep(a.failed / name, 'failed-quota/' + name)
    for name in ['empty-submission-chinese-p2.png', 'notice-mixed-submission-chinese-p2.png']:
        keep(a.after / name, 'visual/' + name)
    write('inventory.json', dict(prototype_only=True, version='0.3.43', source_repo_modified=False,
        translation_tree_modified=False, native_pairs=12, native_artifacts=54, word_previews=18,
        structural_cases=264, deleted_owned_local_templates=5, release_acceptance=False,
        microsoft_word_acceptance=False, global_switch_complete=False, collector_sha256=sha(Path(__file__))))
    print(a.output)


if __name__ == '__main__': main()
