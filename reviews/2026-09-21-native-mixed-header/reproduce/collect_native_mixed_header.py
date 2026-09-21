"""Freeze captured input, native prototype evidence and the remaining limits."""
import argparse
import json
from pathlib import Path
import shutil
import sys
from bs4 import BeautifulSoup
from artifact_utils import sha

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'experiments/mixed-budget-header'))
from compact import compact_source


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['before', 'after', 'captures', 'check', 'trial', 'failed', 'legacy', 'tooling', 'output']:
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    assert not a.output.exists()
    result = json.loads((a.check / 'report.json').read_text())
    assert result['selected_checks_passed'] and len(result['rows']) == 8
    assert result['prototype_only'] and not result['release_acceptance']
    assert result['checker_sha256'] == sha(ROOT / 'scripts/check_native_mixed_header.py')
    lifecycle = json.loads((a.captures / 'worker-lifecycle.json').read_text())
    assert lifecycle['stock_worker_restored'] and lifecycle['deleted_owned_templates'] == 4
    assert all(r['status'] == 'exited' for r in lifecycle['after'])
    a.output.mkdir(parents=True)
    def keep(source, name):
        target = a.output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    def write(name, data):
        target = a.output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    keep(a.check / 'report.json', 'provenance/native-comparison.json')
    keep(a.captures / 'worker-lifecycle.json', 'provenance/worker-lifecycle.json')
    keep(a.after / 'prototype.json', 'provenance/prototype.json')
    for phase, folder in [('before', a.before), ('after', a.after)]:
        for name in ['manifest.json', 'missing-info-render-report.json', 'owned-test-template-cleanup.json']:
            keep(folder / name, 'provenance/' + phase + '-' + name)
        previews = {}
        for path in folder.glob('word-preview-*.json'):
            keep(path, 'provenance/' + phase + '-' + path.name)
            for row in json.loads(path.read_text())['rows']:
                assert row['name'] not in previews
                assert sha(folder / 'renders' / (row['name'] + '.docx')) == row['docx_sha256']
                assert sha(folder / 'word-preview' / (row['name'] + '.pdf')) == row['preview_sha256']
                previews[row['name']] = row
        assert len(previews) == 8
        for row in result['rows']:
            stem = row['stem']
            for fmt in ['pdf', 'docx']:
                name = stem + '.' + fmt
                keep(folder / 'renders' / name, phase + '/native/' + name)
                keep(folder / 'renders' / (name + '.fixture.json'), phase + '/native/' + name + '.fixture.json')
            keep(folder / 'word-preview' / (stem + '.pdf'), phase + '/word-preview/' + stem + '.pdf')
            name = stem + '-' + phase + '.input.html'
            keep(a.check / name, phase + '/pdf-input/' + stem + '.html')
            proof = json.loads((a.check / Path(name).with_suffix('.json')).read_text())
            write(phase + '/pdf-input/' + stem + '.json', proof)
            keep(a.captures / (proof['capture_prefix'] + '.trace.json'), phase + '/trace/' + stem + '.json')
            html = folder / 'renders' / (stem + '.html')
            compacted, assets = compact_source(html.read_bytes())
            target = a.output / phase / 'html-input' / (stem + '.html')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(compacted)
            write(phase + '/html-input/' + stem + '.json', {'full_input_sha256': sha(html), 'fonts': assets})
    # Retain the failed quota attempt; retry reused the same staged English UUID.
    keep(a.failed / 'missing-info-render-report.json', 'provenance/quota-failed-render-report.json')
    keep(a.failed / 'render-mixed-long-last-review-english-html.log', 'provenance/quota-failed-render.log')
    for name in ['prototype.json', 'manifest.json']:
        keep(a.failed / name, 'provenance/quota-attempt-' + name)
    for path in a.trial.glob('*.pdf'):
        keep(path, 'replay/' + path.name)
        keep(path.with_suffix('.trace.json'), 'replay/' + path.stem + '.trace.json')
    keep(a.trial / 'report.json', 'replay/report.json')
    source = a.captures / '001.input.html'
    data, assets = compact_source(source.read_bytes())
    target = a.output / 'replay/captured.input.html'
    target.write_bytes(data)
    write('replay/captured.input.json', {'full_input_sha256': sha(source), 'compact_input_sha256': sha(target), 'fonts': assets})
    keep(a.captures / '001.trace.json', 'replay/captured.trace.json')
    keep(a.captures / '001.output.pdf', 'replay/captured.pdf')
    legacy_data, _ = compact_source(a.legacy.read_bytes())
    native_style = BeautifulSoup(data, 'html.parser').style.get_text()
    legacy_style = BeautifulSoup(legacy_data, 'html.parser').style.get_text()
    start = '/* DSW Document Template Tool CJK font fallback:start */'
    end = '/* DSW Document Template Tool CJK font fallback:end */'
    assert native_style.count(start) == native_style.count(end) == 1 and start not in legacy_style
    block = native_style[native_style.index(start):native_style.index(end) + len(end)]
    projected = native_style.replace(block, '', 1).replace('"DSW Noto Sans TC", "Open Sans", sans-serif', '"Open Sans", sans-serif')
    assert projected.strip() == legacy_style.strip(), 'Other CSS differences need explicit investigation'
    (a.output / 'provenance/native-review-extra-css.css').write_text(block + '\n')
    localization = a.tooling / 'src/dsw_document_template_tool/_template_transform/localization.py'
    keep(localization, 'reproduce/tooling-localization.py')
    write('provenance/input-difference.json', {'cause_confirmed_for_baseline_mismatch': True,
        'legacy_reconstructed_input_sha256': sha(a.legacy), 'captured_input_sha256': sha(source),
        'only_style_delta': 'Format-UUID-specific CJK fallback and typography block plus four font-family prefixes',
        'localization_sha256': sha(localization), 'pdf_review_format_uuid': '68c26e34-5e77-4e15-9bf7-06ff92582257',
        'worker_font_lifetime_cause_claimed': False})
    for path in (ROOT / 'experiments/mixed-budget-header').glob('*.py'):
        keep(path, 'reproduce/experiment/' + path.name)
    keep(ROOT / 'experiments/mixed-budget-header/compose.capture.yml', 'reproduce/experiment/compose.capture.yml')
    for name in ['check_native_mixed_header.py', 'rehearse_native_mixed_header.py', 'collect_native_mixed_header.py', 'restore_captured_pdf_input.py']:
        keep(ROOT / 'scripts' / name, 'reproduce/' + name)
    for path in a.check.glob('*.png'):
        keep(path, 'visual/' + path.name)
    write('inventory.json', {'prototype_only': True, 'source_template_version': '0.3.42',
        'source_repo_modified': False, 'translation_modified': False, 'version_modified': False,
        'release_acceptance': False, 'microsoft_word_acceptance': False, 'native_pairs': 8,
        'native_format_artifacts': 48, 'word_previews': 16, 'captured_pdf_entry_inputs': 16,
        'captured_baseline_replay_exact': True, 'page_increase_cases': ['mixed-long-last-review-chinese'],
        'full_control_matrix_complete': False, 'collector_sha256': sha(Path(__file__))})
    print(a.output)


if __name__ == '__main__':
    main()
