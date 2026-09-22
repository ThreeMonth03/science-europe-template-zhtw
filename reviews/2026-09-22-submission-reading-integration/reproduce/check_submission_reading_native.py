"""Native 0.3.45 paired-package parity, not global or Microsoft Word acceptance."""
import argparse
import json
from pathlib import Path
import sys
import zipfile
from bs4 import BeautifulSoup
from docx import Document
from artifact_utils import sha
from submission_reading_integration import CONTRACT, frozen_package, check
from check_budget_grouping_integration import project_metadata
from check_submission_preview_native import compare_docx, word_html_inventory
from check_word_short_budget_outputs import verify_preview_paragraphs
from check_header_controls import raster_digest
from rehearse_profile_pagination import geometry
from prepare_runtime_variant import require_tables_only_sources
from preview_word_short_budget import report_name

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / CONTRACT['prototype_archive']
CASES = ['ethics-missing', 'ethics-answered', 'ethics-long']
sys.path[:0] = [str(ROOT / 'experiments/word-short-tables'), str(ROOT / 'experiments/mixed-budget-header')]
from table_native import table_placement
from compact import compact_source
from notice_native import check_visible


def run(after, fixtures, english, compacted=False, control=None):
    assert sha(ARCHIVE / 'checksums.json') == CONTRACT['prototype_seal_sha256']
    for name, digest in json.loads((ARCHIVE / 'checksums.json').read_text()).items():
        assert sha(ARCHIVE / name) == digest, name
    assert control is not None, 'Compare unchanged prototype and candidate rendered on the same day'
    before = control
    control_manifest = json.loads((before / 'manifest.json').read_text())
    original_manifest = json.loads((ARCHIVE / 'after/manifest.json').read_text())
    control_note = control_manifest.pop('same_day_control')
    assert control_note['source_seal'] == CONTRACT['prototype_seal_sha256']
    assert control_manifest == original_manifest
    manifest = json.loads((after / 'manifest.json').read_text())
    assert manifest['status'] == 'runtime-experiment'
    assert manifest['source']['version'] == manifest['translation']['version'] == '0.3.45'
    require_tables_only_sources(manifest['runtime_variant']['reviewed_source_sha256'])
    assert manifest['runtime_variant']['worker_image_id'] == 'sha256:6d3cbcab3294e760a4d92e27bec72d4fb23a0adb2cc1734d981478688741ab11'
    hashes = manifest['identical_package_sha256']; assert set(hashes) == {'english.zip', 'chinese.zip'}
    old_manifest = control_manifest
    if not compacted:
        candidate = Path(manifest['baseline_build']); check(candidate, english)
    for language in ['english', 'chinese']:
        name = language + '.zip'
        assert hashes[name] == manifest['sha256'][name]
        if compacted:
            package = json.loads((after / (language + '.json')).read_text())
        else:
            assert sha(after / name) == sha(candidate / name) == hashes[name]
            with zipfile.ZipFile(after / name) as z: package = json.loads(z.read('template/template.json'))
        project_metadata(package, frozen_package(language), manifest['package_timestamp'], versions=('0.3.44', '0.3.45'))
        if compacted:
            previous = json.loads((before / (language + '.json')).read_text())
        else:
            assert sha(before / name) == old_manifest['sha256'][name]
            with zipfile.ZipFile(before / name) as z: previous = json.loads(z.read('template/template.json'))
        assert previous == json.loads((ARCHIVE / 'after' / (language + '.json')).read_text())
    rendered = json.loads((after / 'missing-info-render-report.json').read_text())
    expected = {(c + '-' + p, l, f) for c in CASES for p in ['review', 'submission']
                for l in ['english', 'chinese'] for f in ['html', 'pdf', 'docx']}
    assert rendered['all_renders_succeeded'] and len(rendered['renders']) == len(expected)
    assert {(r['case'], r['language'], r['format']) for r in rendered['renders'] if r['rendered']} == expected
    assert rendered['package_sha256'] == hashes
    old_report = json.loads((before / 'missing-info-render-report.json').read_text())
    assert old_report['all_renders_succeeded'] and len(old_report['renders']) == len(expected)
    assert {(r['case'], r['language'], r['format']) for r in old_report['renders'] if r['rendered']} == expected
    assert old_report['package_sha256'] == {n: old_manifest['sha256'][n] for n in hashes}
    preview = json.loads((after / report_name([c + '-' + p for c in CASES for p in ['review', 'submission']])).read_text())
    assert preview['completed'] and len(preview['rows']) == 12
    assert {r['name'] for r in preview['rows']} == {n + '-' + l for n, l, _ in expected}
    for row in preview['rows']:
        assert sha(after / 'renders' / (row['name'] + '.docx')) == row['docx_sha256']
        assert sha(after / 'word-preview' / (row['name'] + '.pdf')) == row['preview_sha256']
    prior_preview = json.loads((before / report_name([c + '-' + p for c in CASES for p in ['review', 'submission']])).read_text())
    assert prior_preview['completed'] and len(prior_preview['rows']) == 12
    assert {r['name'] for r in prior_preview['rows']} == {n + '-' + l for n, l, _ in expected}
    for row in prior_preview['rows']:
        assert sha(before / 'renders' / (row['name'] + '.docx')) == row['docx_sha256']
        assert sha(before / 'word-preview' / (row['name'] + '.pdf')) == row['preview_sha256']
    rows = []
    for case in CASES:
        for language, locale in [('english', 'en'), ('chinese', 'zh-Hant')]:
            recipe = fixtures / locale / (case + '.json'); events = fixtures / locale / (case + '.events.json')
            bundle = recipe.parent / json.loads(recipe.read_text())['knowledge_model_package_id']
            model_hash = json.loads((fixtures / 'knowledge-model-sha256.json').read_text())[bundle.name] if compacted else sha(bundle)
            for profile in ['review', 'submission']:
                stem = case + '-' + profile + '-' + language
                old, new = [r / 'renders' / stem for r in [before, after]]
                for fmt in ['html', 'pdf', 'docx']:
                    receipts = [json.loads(p.with_suffix('.' + fmt + '.fixture.json').read_text()) for p in [old, new]]
                    for key in ['recipe_sha256', 'events_sha256', 'km_sha256', 'output_profile', 'format_uuid', 'runner_sha256']:
                        assert receipts[0][key] == receipts[1][key], (stem, fmt, key)
                    assert receipts[0]['package_sha256'] == old_manifest['sha256'][language + '.zip']
                    assert receipts[1]['package_sha256'] == hashes[language + '.zip']
                    assert receipts[1]['recipe_sha256'] == sha(recipe) and receipts[1]['events_sha256'] == sha(events)
                    assert receipts[1]['km_sha256'] == model_hash and receipts[1]['output_profile'] == profile
                if compacted:
                    receipt = json.loads(old.with_suffix('.html.compact.json').read_text())
                    assert sha(old.with_suffix('.html')) == receipt['compact_html_sha256']
                    prior_raw = old.with_suffix('.html').read_bytes(); prior_sha = receipt['original_html_sha256']; prior_fonts = receipt['fonts']
                    actual = json.loads(new.with_suffix('.html.compact.json').read_text())
                    raw = new.with_suffix('.html').read_bytes(); html_sha = actual['original_html_sha256']; fonts = actual['fonts']
                    assert sha(new.with_suffix('.html')) == actual['compact_html_sha256']
                else:
                    prior_raw, prior_fonts = compact_source(old.with_suffix('.html').read_bytes()); prior_sha = sha(old.with_suffix('.html'))
                    raw, fonts = compact_source(new.with_suffix('.html').read_bytes()); html_sha = sha(new.with_suffix('.html'))
                assert html_sha == prior_sha and fonts == prior_fonts, (stem, 'Native HTML drift')
                assert raw == prior_raw
                compare_docx(old.with_suffix('.docx'), new.with_suffix('.docx'))
                soup = BeautifulSoup(raw, 'html.parser'); document = Document(new.with_suffix('.docx'))
                assert len(soup.select('.question')) == 15 and len(soup.select('.dmp-section')) == 6
                inventory = word_html_inventory(document, soup)
                results = {}
                for engine, paths in [('native_pdf', [p.with_suffix('.pdf') for p in [old, new]]),
                    ('word_preview', [r / 'word-preview' / (stem + '.pdf') for r in [before, after]])]:
                    assert geometry(paths[0]) == geometry(paths[1]), (stem, engine, 'Geometry drift')
                    assert raster_digest(paths[0]) == raster_digest(paths[1]), (stem, engine, 'Pixel drift')
                    visible = check_visible(paths[1], soup, word=engine == 'word_preview')
                    assert not visible['bounds_issues'], (stem, engine)
                    results[engine] = dict(**visible, pixels_and_geometry_identical=True,
                        before_sha256=sha(paths[0]), after_sha256=sha(paths[1]))
                placement = table_placement(after / 'word-preview' / (stem + '.pdf'), soup, document) if case == 'ethics-long' else None
                count = verify_preview_paragraphs(document, after / 'word-preview' / (stem + '.pdf'), soup)
                artifacts = {fmt: sha(new.with_suffix('.' + fmt)) for fmt in ['html', 'pdf', 'docx']}; artifacts['html'] = html_sha
                rows.append(dict(case=case, language=language, profile=profile, html_bytes_identical=True,
                    word_components_identical_except_timestamps=True, word_html_paragraph_inventory=inventory,
                    rendered=results, table_placement=placement, preview_paragraphs=count, artifacts=artifacts))
    assert len(rows) == 12 and sum(bool(r['table_placement']) for r in rows) == 4
    return rows


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['after', 'control', 'fixtures', 'english', 'output']: p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args(); assert not a.output.exists()
    report = dict(passed=False, source_integrated=True, source_version='0.3.45', release_acceptance=False,
        microsoft_word_acceptance=False, global_switch_complete=False, checker_sha256=sha(Path(__file__)))
    try:
        report['rows'] = run(a.after.resolve(), a.fixtures.resolve(), a.english.resolve(), control=a.control.resolve())
        report.update(passed=True, native_rebuilt_source_checked=True, exact_prototype_parity=True, same_day_control=True)
    except Exception as error: report['failure'] = repr(error); raise
    finally:
        with a.output.open('x') as stream: stream.write(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(passed=True, pairs=len(report['rows']))))
