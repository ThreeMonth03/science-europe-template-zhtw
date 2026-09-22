"""Freeze integrated 0.3.45 evidence without changing older review archives."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import shutil
import sys
import zipfile
from artifact_utils import sha
from check_submission_reading_native import CASES
from submission_reading_integration import CONTRACT

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'experiments/mixed-budget-header'))
from compact import compact_source


def collect(candidate, run, control, fixtures, native, quota, ci_build, output):
    assert not output.exists()
    result = json.loads(native.read_text())
    assert result['passed'] and result['native_rebuilt_source_checked'] and len(result['rows']) == 12
    assert result['same_day_control']
    assert result['checker_sha256'] == sha(ROOT / 'scripts/check_submission_reading_native.py')
    before, current, preview = [json.loads((p / 'manifest.json').read_text()) for p in [candidate, run, ci_build]]
    assert before['status'] == 'candidate' and all(not s['dirty'] for s in before['checkouts'].values())
    assert before['source']['version'] == before['translation']['version'] == '0.3.45'
    assert before['translation_units'] == 767 and not before['untranslated_units']
    assert json.loads((candidate / 'submission-reading-integration.json').read_text())['passed']
    structural = json.loads((candidate / 'submission-reading-structure.json').read_text())
    assert structural['passed'] and len(structural['rows']) == 3312
    cleanup = json.loads((run / 'owned-test-template-cleanup.json').read_text())
    assert cleanup['run_completed_successfully'] and len(cleanup['deleted']) == 2
    assert cleanup['project_references'] == cleanup['document_references'] == 0
    control_cleanup = json.loads((control / 'owned-test-template-cleanup.json').read_text())
    assert control_cleanup['run_completed_successfully'] and len(control_cleanup['deleted']) == 2
    assert control_cleanup['project_references'] == control_cleanup['document_references'] == 0
    life = json.loads((run / 'worker-lifecycle.json').read_text())
    assert life['stock_worker_restored'] and len(life['after']) == 4 and all(v['status'] == 'exited' for v in life['after'])
    allowance = json.loads(quota.read_text()); assert allowance['restored'] and allowance['before'] == allowance['after']
    assert preview['status'] == 'preview'
    output.mkdir(parents=True)

    def keep(path, name):
        target = output / name; target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(path, target)

    def write(name, value):
        target = output / name; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

    for name in ['manifest.json', 'submission-reading-integration.json', 'submission-reading-structure.json',
                 'structure-audit.json', 'translation-audit.json', 'english-build.log', 'chinese-build.log']:
        keep(candidate / name, 'provenance/candidate-' + name)
    # Earlier local lifecycle probes used a preview checkout. Bind its identical
    # package hashes explicitly; do not relabel that manifest as a clean candidate.
    for path in ci_build.glob('*.json'):
        if path.name.endswith(('-scope.json', '-engine.json', '-preflight.json')) or path.name == 'manifest.json':
            keep(path, 'preview-ci/' + path.name)
    keep(native, 'provenance/native.json'); keep(quota, 'provenance/storage-allowance.json')
    for name in ['manifest.json', 'missing-info-render-report.json', 'owned-test-template-cleanup.json']:
        keep(run / name, 'native/' + name)
    keep(run / 'worker-lifecycle.json', 'provenance/worker-lifecycle.json')
    for path in run.glob('word-preview-*.json'): keep(path, 'native/' + path.name)
    for name in ['manifest.json', 'missing-info-render-report.json', 'owned-test-template-cleanup.json']:
        keep(control / name, 'control/' + name)
    for path in control.glob('word-preview-*.json'): keep(path, 'control/' + path.name)
    dates = []
    for row in result['rows']:
        stem = row['case'] + '-' + row['profile'] + '-' + row['language']
        for fmt in ['html', 'pdf', 'docx']:
            path = run / 'renders' / (stem + '.' + fmt); name = 'native/renders/' + path.name
            assert sha(path) == row['artifacts'][fmt]
            if fmt == 'html':
                raw, fonts = compact_source(path.read_bytes()); target = output / name
                archived = ROOT / CONTRACT['prototype_archive'] / 'after/renders' / path.name
                prior = archived.read_bytes()
                old_date = re.findall(rb'<p class="document-meta">[^<]+</p>', prior)
                new_date = re.findall(rb'<p class="document-meta">[^<]+</p>', raw)
                assert len(old_date) == len(new_date) == 1
                dates.append(dict(stem=stem, archived_date=old_date[0].decode(), current_date=new_date[0].decode(),
                    only_date_differs=prior.replace(old_date[0], new_date[0], 1) == raw,
                    comparison_only=True, native_files_modified=False))
                target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
                write(name + '.compact.json', dict(original_html_sha256=sha(path), compact_html_sha256=sha(target), fonts=fonts))
            else: keep(path, name)
            keep(path.with_suffix('.' + fmt + '.fixture.json'), name + '.fixture.json')
        path = run / 'word-preview' / (stem + '.pdf')
        assert sha(path) == row['rendered']['word_preview']['after_sha256']
        keep(path, 'native/word-preview/' + path.name)
        for fmt in ['html', 'pdf', 'docx']:
            path = control / 'renders' / (stem + '.' + fmt); name = 'control/renders/' + path.name
            if fmt == 'html':
                assert sha(path) == row['artifacts']['html']
                raw, fonts = compact_source(path.read_bytes()); target = output / name
                target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
                write(name + '.compact.json', dict(original_html_sha256=sha(path), compact_html_sha256=sha(target), fonts=fonts))
            else: keep(path, name)
            keep(path.with_suffix('.' + fmt + '.fixture.json'), name + '.fixture.json')
        path = control / 'word-preview' / (stem + '.pdf')
        assert sha(path) == row['rendered']['word_preview']['before_sha256']
        keep(path, 'control/word-preview/' + path.name)
    members = {}
    for language in ['english', 'chinese']:
        name = language + '.zip'
        assert sha(candidate / name) == sha(run / name) == sha(ci_build / name)
        assert sha(run / name) == current['identical_package_sha256'][name] == before['sha256'][name] == preview['sha256'][name]
        assert cleanup['backups'][name]['sha256'] == sha(run / name)
        with zipfile.ZipFile(run / name) as z:
            write('native/' + language + '.json', json.loads(z.read('template/template.json')))
            members[language] = {n: hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()}
    write('provenance/package-members.json', members)
    prior_manifest = json.loads((ROOT / CONTRACT['prototype_archive'] / 'after/manifest.json').read_text())
    control_members = {}
    for language in ['english', 'chinese']:
        path = control / (language + '.zip')
        assert sha(path) == prior_manifest['sha256'][path.name] == control_cleanup['backups'][path.name]['sha256']
        with zipfile.ZipFile(path) as z:
            write('control/' + language + '.json', json.loads(z.read('template/template.json')))
            control_members[language] = {n: hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()}
    assert control_members == json.loads((ROOT / CONTRACT['prototype_archive'] / 'provenance/package-members.json').read_text())
    write('provenance/control-package-members.json', control_members)
    write('diagnostics/cross-day-date.json', dates)
    for locale in ['en', 'zh-Hant']:
        for case in CASES:
            for suffix in ['.json', '.events.json']: keep(fixtures / locale / (case + suffix), 'fixtures/' + locale + '/' + case + suffix)
    write('fixtures/knowledge-model-sha256.json', {p.name: sha(p) for p in (fixtures / 'knowledge-models').iterdir() if p.is_file()})
    for name in ['check_submission_reading_native.py', 'collect_submission_reading_native.py', 'prepare_submission_reading_control.py',
                 'submission_reading_integration.py', 'probe_submission_reading.py']:
        keep(ROOT / 'scripts' / name, 'reproduce/' + name)
    for name in ['submission-reading-prepared-delta.json', 'submission-reading-translation-delta.json']:
        keep(ROOT / 'docs' / name, 'provenance/' + name)
    for path in (run / 'visual').glob('*.png'): keep(path, 'visual/' + path.name)
    write('inventory.json', dict(source_version='0.3.45', source_integrated=True,
        source_commit=before['source']['commit'], translation_commit=before['checkouts']['translation']['commit'],
        prototype_archive=CONTRACT['prototype_archive'], prototype_seal_sha256=CONTRACT['prototype_seal_sha256'],
        native_rebuilt_source_checked=True, native_pairs=12, native_artifacts=36, word_previews=12,
        same_day_control=True, new_control_native_artifacts=36, new_control_word_previews=12,
        structural_checks=3312, retained_translation_pairs=762, added_translation_pairs=5,
        deleted_owned_local_templates=4, storage_allowance_restored=True, production_touched=False,
        preview_ci_packages_identical_to_candidate=True, full_visual_acceptance=False,
        global_switch_complete=False, release_acceptance=False, microsoft_word_acceptance=False,
        collector_sha256=sha(Path(__file__))))
    return output


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['candidate', 'run', 'control', 'fixtures', 'native', 'quota', 'ci-build', 'output']:
        p.add_argument('--' + name, type=Path, required=True)
    print(collect(**vars(p.parse_args())))
