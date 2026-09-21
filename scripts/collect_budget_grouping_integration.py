"""Freeze the integrated candidate's native parity without modifying prior evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile
from artifact_utils import sha
from check_budget_grouping_integration import ARCHIVE, SEAL

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'experiments/mixed-budget-header'))
from compact import compact_source


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['candidate', 'runtime', 'english', 'output']: p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args(); assert not a.output.exists()
    comparison = json.loads((a.runtime / 'budget-grouping-native.json').read_text())
    assert comparison['selected_checks_passed'] and len(comparison['rows']) == 8
    assert comparison['checker_sha256'] == sha(ROOT / 'scripts/check_budget_grouping_native.py')
    integration = json.loads((a.candidate / 'budget-grouping-integration.json').read_text())
    assert integration['selected_checks_passed'] and integration['frozen_seal'] == SEAL
    assert integration['checker_sha256'] == sha(ROOT / 'scripts/check_budget_grouping_integration.py')
    life = json.loads((a.runtime / 'worker-lifecycle.json').read_text())
    assert life['deleted_owned_templates'] == 2 and life['stock_worker_restored']
    assert not life['production_touched'] and all(r['status'] == 'exited' for r in life['after'])
    renders = json.loads((a.runtime / 'missing-info-render-report.json').read_text())
    assert renders['all_renders_succeeded'] and len(renders['renders']) == 24
    a.output.mkdir(parents=True)
    def keep(path, name):
        target = a.output / name; target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(path, target)
    def write(name, value):
        target = a.output / name; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    for name in ['manifest.json', 'structure-audit.json', 'translation-audit.json',
                 'budget-grouping-integration.json', 'budget-grouping-scope.json', 'identifier-spacing-preflight.json']:
        keep(a.candidate / name, 'provenance/candidate-' + name)
    for name in ['manifest.json', 'missing-info-render-report.json', 'owned-test-template-cleanup.json',
                 'budget-grouping-native.json', 'worker-lifecycle.json']:
        keep(a.runtime / name, 'provenance/' + name)
    previews = {}
    for path in a.runtime.glob('word-preview-*.json'):
        receipt = json.loads(path.read_text()); assert receipt['completed']
        keep(path, 'provenance/' + path.name)
        for row in receipt['rows']:
            assert row['name'] not in previews
            assert row['docx_sha256'] == sha(a.runtime / 'renders' / (row['name'] + '.docx'))
            assert row['preview_sha256'] == sha(a.runtime / 'word-preview' / (row['name'] + '.pdf'))
            previews[row['name']] = row
    assert set(previews) == {r['stem'] for r in comparison['rows']}
    for row in comparison['rows']:
        stem = row['stem']
        for fmt in ['html', 'pdf', 'docx']:
            source = a.runtime / 'renders' / (stem + '.' + fmt)
            assert sha(source) == row['artifacts'][fmt]
            if fmt == 'html':
                compact, assets = compact_source(source.read_bytes())
                target = a.output / 'after/renders' / source.name; target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(compact)
                write('after/renders/' + source.name + '.compact.json', dict(original_html_sha256=sha(source),
                    compact_html_sha256=sha(target), fonts=assets, native_pdf_entry_input=False))
            else: keep(source, 'after/renders/' + source.name)
            keep(source.with_suffix('.' + fmt + '.fixture.json'), 'after/renders/' + source.name + '.fixture.json')
        preview = a.runtime / 'word-preview' / (stem + '.pdf')
        assert sha(preview) == row['word_preview_sha256']
        keep(preview, 'after/word-preview/' + preview.name)
    members = {}
    for language in ['english', 'chinese']:
        name = language + '.zip'
        assert sha(a.candidate / name) == sha(a.runtime / name) == comparison['package_sha256'][name]
        assert integration['packages'][language]['package_sha256'] == comparison['package_sha256'][name]
        with zipfile.ZipFile(a.runtime / name) as package:
            write('package/' + language + '.json', json.loads(package.read('template/template.json')))
            members[language] = {n: hashlib.sha256(package.read(n)).hexdigest() for n in package.namelist()}
    write('provenance/package-members.json', members)
    write('provenance/baseline-reference.json', dict(archive=ARCHIVE.name, phase='after', checksums_sha256=SEAL))
    for name in ['check_budget_grouping_integration.py', 'check_budget_grouping_native.py',
                 'collect_budget_grouping_integration.py', 'probe_metadata_gap_prose_scope.py', 'word_budget_geometry.py']:
        keep(ROOT / 'scripts' / name, 'reproduce/' + name)
    keep(ROOT / 'pipeline.yml', 'reproduce/pipeline.yml')
    for name in ['budget_grouping_contract.py', 'probe_long_budget_word.py', 'probe_pdf_budget_reading.py']:
        keep(a.english / 'scripts' / name, 'reproduce/english/' + name)
    for name in ['grouped-word-043.json', 'grouped-pdf-043.json']:
        keep(a.english / 'outputs' / name, 'structure/' + name)
    for name in ['zh-submission-final-page.png', 'zh-word-final-page.png']:
        keep(a.runtime / name, 'visual/' + name)
    write('inventory.json', dict(version='0.3.43', source_integrated=True, native_pairs=8,
        new_native_artifacts=24, new_word_previews=8, translation_modified=False,
        release_acceptance=False, microsoft_word_acceptance=False, production_touched=False,
        collector_sha256=sha(Path(__file__))))
    print(a.output)


if __name__ == '__main__': main()
