"""Archive completed native controls separately from the previous frozen trial."""
import argparse
import json
from pathlib import Path
import shutil
import sys
from artifact_utils import sha

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'experiments/mixed-budget-header'))
from compact import compact_source


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['before', 'after', 'fixtures', 'check', 'lifecycle', 'output']:
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args(); assert not a.output.exists()
    check = json.loads(a.check.read_text())
    assert check['prototype_only'] and check['selected_checks_passed'] and len(check['rows']) == 20
    assert not check['release_acceptance'] and not check['full_control_matrix_complete']
    assert check['checker_sha256'] == sha(ROOT / 'scripts/check_header_controls.py')
    life = json.loads(a.lifecycle.read_text())
    assert life['stock_worker_restored'] and life['deleted_owned_templates'] == 4
    assert not life['capture_observer_attached'] and all(r['status'] == 'exited' for r in life['after'])
    a.output.mkdir(parents=True)
    def keep(path, name):
        target = a.output / name; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    def write(name, value):
        target = a.output / name; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    keep(a.check, 'provenance/comparison.json')
    keep(a.lifecycle, 'provenance/worker-lifecycle.json')
    keep(a.after / 'prototype.json', 'provenance/prototype.json')
    for phase, folder in [('before', a.before), ('after', a.after)]:
        for name in ['manifest.json', 'missing-info-render-report.json', 'owned-test-template-cleanup.json']:
            keep(folder / name, 'provenance/' + phase + '-' + name)
        renders = json.loads((folder / 'missing-info-render-report.json').read_text())
        assert renders['all_renders_succeeded'] and len(renders['renders']) == 60
        assert all(r['rendered'] for r in renders['renders'])
        previews = {}
        for path in folder.glob('word-preview-*.json'):
            value = json.loads(path.read_text()); assert value['completed']
            keep(path, 'provenance/' + phase + '-' + path.name)
            for row in value['rows']:
                assert row['name'] not in previews
                assert sha(folder / 'renders' / (row['name'] + '.docx')) == row['docx_sha256']
                assert sha(folder / 'word-preview' / (row['name'] + '.pdf')) == row['preview_sha256']
                previews[row['name']] = row
        assert len(previews) == 20
        for row in check['rows']:
            stem = row['stem']
            for fmt in ['html', 'pdf', 'docx']:
                source = folder / 'renders' / (stem + '.' + fmt)
                target = phase + '/renders/' + source.name
                if fmt == 'html':
                    data, assets = compact_source(source.read_bytes())
                    path = a.output / target; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
                    write(target + '.compact.json', {'original_html_sha256': sha(source), 'fonts': assets,
                        'compact_html_sha256': sha(path), 'native_pdf_entry_input': False})
                else: keep(source, target)
                keep(source.with_suffix('.' + fmt + '.fixture.json'), target + '.fixture.json')
            keep(folder / 'word-preview' / (stem + '.pdf'), phase + '/word-preview/' + stem + '.pdf')
    keep(a.fixtures / 'provenance.json', 'fixtures/provenance.json')
    for locale in ['en', 'zh-Hant']:
        for path in (a.fixtures / locale).glob('*.json'):
            keep(path, 'fixtures/' + locale + '/' + path.name)
    # Large KM packages are recoverable from the locked EN source; hashes are in every receipt.
    for name in ['prepare_header_controls.py', 'check_header_controls.py', 'collect_header_controls.py',
                 'run_missing_info.py', 'render.py', 'preview_word_short_budget.py', 'cleanup_owned_runtime_templates.py']:
        keep(ROOT / 'scripts' / name, 'reproduce/' + name)
    for name in ['prototype.py', 'compact.py', 'finish.py']:
        keep(ROOT / 'experiments/mixed-budget-header' / name, 'reproduce/experiment/' + name)
    for path in a.check.parent.glob('header-control-*.png'):
        keep(path, 'visual/' + path.name)
    write('inventory.json', dict(prototype_only=True, version='0.3.42', source_repo_modified=False,
        translation_modified=False, version_modified=False, release_acceptance=False,
        microsoft_word_acceptance=False, native_pairs=20, native_format_artifacts=120,
        word_previews=40, native_pdf_entry_captured=False, full_control_matrix_complete=False,
        collector_sha256=sha(Path(__file__))))
    print(a.output)


if __name__ == '__main__': main()
