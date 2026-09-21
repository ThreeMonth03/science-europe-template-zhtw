"""Collect new integration evidence without modifying any earlier review archive."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile
from artifact_utils import sha
from prepare_submission_preview_native import CASES

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'experiments/mixed-budget-header'))
from compact import compact_source


def collect(candidate, run, fixtures, native, output):
    assert not output.exists()
    result = json.loads(native.read_text())
    assert result['passed'] and len(result['rows']) == 16
    assert result['checker_sha256'] == sha(ROOT / 'scripts/check_submission_preview_native.py')
    before, current = [json.loads((p / 'manifest.json').read_text()) for p in [candidate, run]]
    assert before['status'] == 'candidate' and all(not s['dirty'] for s in before['checkouts'].values())
    assert before['source']['version'] == before['translation']['version'] == '0.3.44'
    cleanup = json.loads((run / 'owned-test-template-cleanup.json').read_text())
    assert cleanup['run_completed_successfully'] and len(cleanup['deleted']) == 2
    assert cleanup['project_references'] == cleanup['document_references'] == 0
    life = json.loads((run / 'worker-lifecycle.json').read_text())
    assert life['stock_worker_restored'] and all(v['status'] == 'exited' for v in life['after'])
    output.mkdir(parents=True)
    def keep(path, name):
        target = output / name; target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(path, target)
    def write(name, value):
        path = output / name; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    for name in ['manifest.json', 'submission-preview-integration.json', 'submission-preview-structure.json',
                 'budget-grouping-scope.json', 'identifier-spacing-preflight.json', 'structure-audit.json', 'translation-audit.json']:
        keep(candidate / name, 'provenance/candidate-' + name)
    keep(native, 'provenance/native.json')
    for name in ['manifest.json', 'missing-info-render-report.json']:
        keep(run / name, 'native/' + name)
    for name in ['worker-lifecycle.json', 'owned-test-template-cleanup.json']:
        keep(run / name, 'provenance/' + name)
    for path in run.glob('word-preview-*.json'): keep(path, 'native/' + path.name)
    for row in result['rows']:
        stem = row['stem']
        for fmt in ['html', 'pdf', 'docx']:
            source = run / 'renders' / (stem + '.' + fmt)
            assert sha(source) == row['artifacts'][fmt]
            if fmt == 'html':
                compressed, fonts = compact_source(source.read_bytes())
                target = output / 'native/renders' / source.name; target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(compressed)
                write('native/renders/' + source.name + '.compact.json', dict(original_html_sha256=sha(source),
                    compact_html_sha256=sha(target), fonts=fonts, native_pdf_entry_input=False))
            else: keep(source, 'native/renders/' + source.name)
            keep(source.with_suffix('.' + fmt + '.fixture.json'), 'native/renders/' + source.name + '.fixture.json')
        preview = run / 'word-preview' / (stem + '.pdf')
        assert sha(preview) == row['rendered']['word_preview']['sha256']
        keep(preview, 'native/word-preview/' + preview.name)
    members = {}
    for language in ['english', 'chinese']:
        name = language + '.zip'
        assert sha(candidate / name) == sha(run / name) == current['identical_package_sha256'][name] == before['sha256'][name]
        assert cleanup['backups'][name]['sha256'] == sha(run / name)
        with zipfile.ZipFile(run / name) as package:
            write('package/' + language + '.json', json.loads(package.read('template/template.json')))
            members[language] = {n: hashlib.sha256(package.read(n)).hexdigest() for n in package.namelist()}
    write('provenance/package-members.json', members)
    keep(fixtures / 'provenance.json', 'fixtures/provenance.json')
    for locale in ['en', 'zh-Hant']:
        for case in CASES:
            for suffix in ['.json', '.events.json']:
                keep(fixtures / locale / (case + suffix), 'fixtures/' + locale + '/' + case + suffix)
    for name in ['prepare_submission_preview_native.py', 'check_submission_preview_native.py', 'collect_submission_preview_native.py',
                 'submission_preview_integration.py', 'probe_submission_preview.py']:
        keep(ROOT / 'scripts' / name, 'reproduce/' + name)
    for name in ['submission-preview-prepared-delta.json', 'submission-preview-translation-delta.json']:
        keep(ROOT / 'docs' / name, 'provenance/' + name)
    for path in (run / 'visual').glob('*.png'): keep(path, 'visual/' + path.name)
    write('inventory.json', dict(source_version='0.3.44', source_integrated=True,
        source_commit=before['source']['commit'], translation_commit=before['checkouts']['translation']['commit'],
        native_integrated_render_checked=True, native_pairs=16, native_artifacts=48, word_previews=16,
        structural_checks=544, deleted_owned_local_templates=2, production_touched=False,
        global_switch_complete=False, release_acceptance=False, microsoft_word_acceptance=False,
        collector_sha256=sha(Path(__file__))))
    return output


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['candidate', 'build', 'fixtures', 'native', 'output']: p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args(); print(collect(a.candidate, a.build, a.fixtures, a.native, a.output))
