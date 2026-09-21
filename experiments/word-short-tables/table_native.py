"""Actual DSW Word pipeline verification; never replace native files by copies."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys
import zipfile
from bs4 import BeautifulSoup
from docx import Document
from docx.oxml.ns import qn
from lxml import etree
from table_recipe import ROOT, HERE, ARCHIVE, LUA, baseline, patch, sha
from table_trial import CASES
from table_probe import xml_delta

sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'experiments/table-flow'),
               str(ROOT / 'experiments/ethics-lead'), str(ROOT / 'experiments/mixed-budget-header')]
from budget_native import inputs as parent_inputs
from lead_native import visible_with_table_header, lead_placement, long_paragraph
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
        if compacted: package = json.loads((root / (language + '.json')).read_text())
        else:
            with zipfile.ZipFile(root / (language + '.zip')) as z:
                package = json.loads(z.read('template/template.json'))
                assert z.read('template/assets/' + LUA) == (HERE / 'short-tables.lua').read_bytes()
            assert digest(root / (language + '.zip')) == manifest['sha256'][language + '.zip']
        assert package == patch(baseline(language), language)
        assert report['package_sha256'][language + '.zip'] == manifest['sha256'][language + '.zip']
    return manifest


def word_delta(before, after, count):
    with zipfile.ZipFile(before) as a, zipfile.ZipFile(after) as b:
        assert len(a.namelist()) == len(b.namelist()) and set(a.namelist()) == set(b.namelist())
        for name in a.namelist():
            if name not in ['word/document.xml', 'docProps/core.xml']: assert a.read(name) == b.read(name), name
        xml_delta(*[etree.fromstring(z.read('word/document.xml')) for z in [a, b]], count)
        assert b'<!--DSW:SE:short-table:' not in b.read('word/document.xml')
        core = [etree.fromstring(z.read('docProps/core.xml')) for z in [a, b]]
        for tree in core:
            for name in ['created', 'modified']:
                nodes = tree.findall('{http://purl.org/dc/terms/}' + name); assert len(nodes) == 1
                assert datetime.fromisoformat(nodes[0].text.replace('Z', '+00:00')).tzinfo is not None
                nodes[0].text = 'VALIDATED-TIMESTAMP'
        assert etree.tostring(core[0]) == etree.tostring(core[1])
    return dict(changed_tables=count, other_components_identical=True, generated_markers_absent=True)


def table_placement(pdf, soup, document):
    tables = soup.select('#q-ethical-issues > .answer > .answer-detail > table'); assert len(tables) == 1
    cells = [[c.get_text() for c in row.find_all(['th', 'td'], recursive=False)] for row in tables[0].select('tr')]
    assert cells == [['Item', 'Value'], ['Original.csv', '0'], ['N/A', 'Retained.']]
    matches = [t for t in document.tables if [[c.text for c in r.cells] for r in t.rows] == cells]; assert len(matches) == 1
    assert matches[0].rows[0]._tr.find(qn('w:trPr') + '/' + qn('w:tblHeader')).get(qn('w:val')) == 'on'
    bbox = etree.fromstring(subprocess.check_output(['pdftotext', '-bbox-layout', str(pdf), '-']))
    headers = []; ends = []; locations = []
    for index, page in enumerate(bbox.findall('.//{*}page'), 1):
        words = page.findall('.//{*}word')
        item = [w for w in words if w.text == 'Item']; value = [w for w in words if w.text == 'Value']
        if item or value:
            assert len(item) == len(value) == 1
            a, b = item[0], value[0]
            assert abs(float(a.get('yMin')) - float(b.get('yMin'))) < .1
            assert float(a.get('xMax')) < float(b.get('xMin'))
            headers.append(index); locations.append((words, a, b))
        ends += [index for w in words if w.text == 'Retained.']
    assert len(headers) == 1 and ends == headers, 'Short table header and last row must share exactly one page'
    words, a, b = locations[0]
    ending = next(w for w in words if w.text == 'Retained.')
    first = [w for w in words if w.text == 'Original.csv' and abs(float(w.get('xMin')) - float(a.get('xMin'))) < .1
             and float(a.get('yMax')) < float(w.get('yMin')) < float(ending.get('yMin'))]
    assert len(first) == 1
    for label, left, top in [('0', b, first[0]), ('N/A', a, ending)]:
        assert len([w for w in words if w.text == label and abs(float(w.get('xMin'))-float(left.get('xMin'))) < .1
                    and abs(float(w.get('yMin'))-float(top.get('yMin'))) < .1]) == 1
    return dict(page=headers[0], rows=3, columns=2, complete_short_table=True, header_only_continuation=False)


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
                    new_receipt = json.loads(paths[1].with_suffix('.html.compact.json').read_text())
                    assert digest(paths[1].with_suffix('.html')) == new_receipt['compact_html_sha256']
                    fonts = new_receipt['fonts']; raw = paths[1].with_suffix('.html').read_bytes(); html_sha = new_receipt['original_html_sha256']
                else:
                    raw, fonts = compact_source(paths[1].with_suffix('.html').read_bytes()); html_sha = digest(paths[1].with_suffix('.html'))
                assert fonts == old_receipt['fonts'] and html_sha == old_receipt['original_html_sha256']
                assert raw == paths[0].with_suffix('.html').read_bytes()
                soup = BeautifulSoup(raw, 'html.parser'); assert len(soup.select('.question')) == 15 and len(soup.select('.dmp-section')) == 6
                changed = int(case == 'ethics-long')
                delta = word_delta(*[p.with_suffix('.docx') for p in paths], changed)
                if not changed: compare_docx(*[p.with_suffix('.docx') for p in paths])
                docs = [Document(p.with_suffix('.docx')) for p in paths]
                paragraphs = [word_html_inventory(d, soup) for d in docs]
                links = [sorted(r.target_ref for r in d.part.rels.values() if r.is_external) for d in docs]; assert links[0] == links[1]
                previous = next(r for r in prior['rows'] if (r['case'], r['language'], r['profile']) == (case, language, profile))
                rendered = {}
                for engine, pdfs in [('native_pdf', [p.with_suffix('.pdf') for p in paths]),
                                     ('word_preview', [r / 'word-preview' / (stem + '.pdf') for r in [before, after]])]:
                    word = engine == 'word_preview'
                    values = [visible_with_table_header(pdfs[0], soup, docs[0], word, case, profile), check_visible(pdfs[1], soup, word=word)]
                    assert not any(v['bounds_issues'] for v in values), stem
                    assert len(values[1]['line_box_overlaps']) <= len(values[0]['line_box_overlaps']), stem
                    limit = min(values[0]['pages'], previous['rendered'][engine]['historical_page_limit'])
                    assert values[1]['pages'] <= limit, (stem, engine, 'Page count increased')
                    identical = geometry(pdfs[0]) == geometry(pdfs[1]) and raster_digest(pdfs[0]) == raster_digest(pdfs[1])
                    if not word or not changed: assert identical, (stem, engine, 'Unrelated appearance changed')
                    rendered[engine] = dict(before=values[0], after=values[1], before_sha256=digest(pdfs[0]), after_sha256=digest(pdfs[1]),
                        historical_page_limit=limit, pixels_and_geometry_identical=identical,
                        lead_placement={phase: lead_placement(pdf, language) for phase, pdf in zip(['before', 'after'], pdfs)})
                    if profile == 'submission': assert rendered[engine]['lead_placement']['after']['together']
                    if changed:
                        rendered[engine]['long_first_paragraph'] = {phase: long_paragraph(pdf, language) for phase, pdf in zip(['before', 'after'], pdfs)}
                        if word: rendered[engine]['table_placement'] = table_placement(pdfs[1], soup, docs[1])
                artifacts = {fmt: digest(paths[1].with_suffix('.' + fmt)) for fmt in ['html', 'pdf', 'docx']}; artifacts['html'] = html_sha
                preview = verify_preview_paragraphs(docs[1], after / 'word-preview' / (stem + '.pdf'), soup)
                rows.append(dict(case=case, language=language, profile=profile, rendered=rendered, word_delta=delta,
                    html_bytes_identical=True, word_html_paragraph_inventory=paragraphs, preview_paragraphs=preview, artifacts=artifacts))
    return rows


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['after', 'fixtures', 'output']: p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args(); assert not a.output.exists()
    report = dict(passed=False, prototype_only=True, source_integrated=False, release_acceptance=False,
        full_visual_acceptance=False, global_switch_complete=False, microsoft_word_acceptance=False,
        checker_sha256=digest(Path(__file__)), recipe_sha256=digest(HERE / 'table_recipe.py'))
    try:
        report['rows'] = run(a.after, a.fixtures)
        report.update(passed=True, bounded_word_fix_verified=True, scoped_visual_gate_passed=True)
    except Exception as error: report['failure'] = repr(error); raise
    finally: a.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(passed=True, pairs=len(report['rows']))))
