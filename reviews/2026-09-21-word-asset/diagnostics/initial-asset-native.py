"""Prove native asset loading preserves every output and short-table fix."""
import argparse
import json
from pathlib import Path
import sys
import zipfile
from bs4 import BeautifulSoup
from docx import Document
from asset_recipe import ROOT, HERE, ARCHIVE, XML, CASES, baseline, helper, patch, sha
from table_native import table_placement, inputs as parent_inputs

sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'experiments/mixed-budget-header')]
from check_submission_preview_native import compare_docx, word_html_inventory
from check_word_short_budget_outputs import verify_preview_paragraphs
from check_header_controls import raster_digest
from rehearse_profile_pagination import geometry
from notice_native import check_visible
from compact import compact_source
from prepare_runtime_variant import require_tables_only_sources
from preview_word_short_budget import report_name


def digest(path): return sha(path.read_bytes())


def inputs(root, compacted):
    manifest = json.loads((root / 'manifest.json').read_text()); assert manifest['status'] == 'runtime-experiment'
    require_tables_only_sources(manifest['prototype']['observed_worker_sources'])
    assert manifest['prototype']['observed_word_sources'] == json.loads((ARCHIVE / 'engine/runtime.json').read_text())['sources']
    report = json.loads((root / 'missing-info-render-report.json').read_text())
    expected = {(c + '-' + p, l, f) for c in CASES for p in ['review', 'submission']
                for l in ['english', 'chinese'] for f in ['html', 'pdf', 'docx']}
    assert report['all_renders_succeeded'] and len(report['renders']) == len(expected)
    assert {(r['case'], r['language'], r['format']) for r in report['renders'] if r['rendered']} == expected
    preview = json.loads((root / report_name([c + '-' + p for c in CASES for p in ['review', 'submission']])).read_text())
    assert preview['completed'] and len(preview['rows']) == 12
    assert {r['name'] for r in preview['rows']} == {n + '-' + l for n, l, _ in expected}
    for row in preview['rows']:
        assert digest(root / 'renders' / (row['name'] + '.docx')) == row['docx_sha256']
        assert digest(root / 'word-preview' / (row['name'] + '.pdf')) == row['preview_sha256']
    for language in ['english', 'chinese']:
        if compacted:
            package = json.loads((root / (language + '.json')).read_text())
            members = json.loads((root.parent / 'provenance/package-members.json').read_text())[language]
            assert members['template/assets/' + XML] == sha(helper())
        else:
            with zipfile.ZipFile(root / (language + '.zip')) as z:
                package = json.loads(z.read('template/template.json'))
                assert z.read('template/assets/' + XML) == helper()
            assert digest(root / (language + '.zip')) == manifest['sha256'][language + '.zip']
        assert package == patch(baseline(language), language)
        assert report['package_sha256'][language + '.zip'] == manifest['sha256'][language + '.zip']
    return manifest


def run(after, fixtures, compacted=False):
    before = ARCHIVE / 'after'; manifests = {before: parent_inputs(before, True), after: inputs(after, compacted)}
    prior = json.loads((ARCHIVE / 'provenance/native.json').read_text()); rows = []
    for case in CASES:
        for language, locale in [('english', 'en'), ('chinese', 'zh-Hant')]:
            recipe = fixtures / locale / (case + '.json'); events = fixtures / locale / (case + '.events.json')
            model = recipe.parent / json.loads(recipe.read_text())['knowledge_model_package_id']
            model_hash = json.loads((fixtures / 'knowledge-model-sha256.json').read_text())[model.name] if compacted else digest(model)
            for profile in ['review', 'submission']:
                stem = case + '-' + profile + '-' + language; paths = [r / 'renders' / stem for r in [before, after]]
                for fmt in ['html', 'pdf', 'docx']:
                    receipts = [json.loads(p.with_suffix('.' + fmt + '.fixture.json').read_text()) for p in paths]
                    for key in ['recipe_sha256', 'events_sha256', 'km_sha256', 'output_profile', 'format_uuid', 'runner_sha256']:
                        assert receipts[0][key] == receipts[1][key], (stem, fmt, key)
                    for receipt, root in zip(receipts, [before, after]):
                        assert receipt['recipe_sha256'] == digest(recipe) and receipt['events_sha256'] == digest(events)
                        assert receipt['km_sha256'] == model_hash and receipt['output_profile'] == profile
                        assert receipt['package_sha256'] == manifests[root]['sha256'][language + '.zip']
                old_receipt = json.loads(paths[0].with_suffix('.html.compact.json').read_text())
                assert digest(paths[0].with_suffix('.html')) == old_receipt['compact_html_sha256']
                if compacted:
                    receipt = json.loads(paths[1].with_suffix('.html.compact.json').read_text())
                    assert digest(paths[1].with_suffix('.html')) == receipt['compact_html_sha256']
                    raw = paths[1].with_suffix('.html').read_bytes(); fonts = receipt['fonts']; html_sha = receipt['original_html_sha256']
                else:
                    raw, fonts = compact_source(paths[1].with_suffix('.html').read_bytes()); html_sha = digest(paths[1].with_suffix('.html'))
                assert html_sha == old_receipt['original_html_sha256'] and fonts == old_receipt['fonts']
                assert raw == paths[0].with_suffix('.html').read_bytes()
                assert compare_docx(*[p.with_suffix('.docx') for p in paths])
                soup = BeautifulSoup(raw, 'html.parser'); docs = [Document(p.with_suffix('.docx')) for p in paths]
                inventories = [word_html_inventory(d, soup) for d in docs]; assert inventories[0] == inventories[1]
                previous = next(r for r in prior['rows'] if (r['case'], r['language'], r['profile']) == (case, language, profile))
                rendered = {}
                for engine, pdfs in [('native_pdf', [p.with_suffix('.pdf') for p in paths]),
                                     ('word_preview', [r / 'word-preview' / (stem + '.pdf') for r in [before, after]])]:
                    assert geometry(pdfs[0]) == geometry(pdfs[1]) and raster_digest(pdfs[0]) == raster_digest(pdfs[1]), (stem, engine)
                    visible = check_visible(pdfs[1], soup, word=engine == 'word_preview')
                    assert visible == previous['rendered'][engine]['after']
                    rendered[engine] = dict(pixels_and_geometry_identical=True, pages=visible['pages'],
                        before_sha256=digest(pdfs[0]), after_sha256=digest(pdfs[1]))
                place = table_placement(after / 'word-preview' / (stem + '.pdf'), soup, docs[1]) if case == 'ethics-long' else None
                if place: assert place == previous['rendered']['word_preview']['table_placement']
                preview = verify_preview_paragraphs(docs[1], after / 'word-preview' / (stem + '.pdf'), soup)
                artifacts = {fmt: digest(paths[1].with_suffix('.' + fmt)) for fmt in ['html', 'pdf', 'docx']}; artifacts['html'] = html_sha
                rows.append(dict(case=case, language=language, profile=profile, html_bytes_identical=True,
                    word_components_identical_except_timestamps=True, word_html_paragraph_inventory=inventories,
                    rendered=rendered, table_placement=place, preview_paragraphs=preview, artifacts=artifacts))
    return rows


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['after', 'fixtures', 'output']: p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args(); assert not a.output.exists()
    report = dict(passed=False, prototype_only=True, source_integrated=False, full_source_translation_checked=False,
        release_acceptance=False, microsoft_word_acceptance=False, checker_sha256=digest(Path(__file__)),
        recipe_sha256=digest(HERE / 'asset_recipe.py'))
    try:
        report['rows'] = run(a.after, a.fixtures)
        report.update(passed=True, native_asset_pipeline_checked=True, exact_parent_output_parity=True)
    except Exception as error: report['failure'] = repr(error); raise
    finally: a.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(passed=True, pairs=len(report['rows']))))
