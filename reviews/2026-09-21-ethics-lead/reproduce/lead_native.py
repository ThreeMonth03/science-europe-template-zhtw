"""Native first-lead placement and long-answer freedom, with unchanged review controls."""
import argparse
import copy
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
from lead_recipe import ROOT, baseline, patch
from lead_probe import compare, templates, replies_from
from lead_trial import CASES, AUTHORED_END

sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'experiments/ethics-prompts')]
from artifact_utils import sha
from ethics_native import lead_placement, visual_gate as lead_visual_gate
from check_submission_preview_native import compare_docx, word_html_inventory
from check_header_controls import raster_digest
from rehearse_profile_pagination import geometry
from notice_native import check_visible
from notice_probe import compact
from check_word_short_budget_outputs import verify_preview_paragraphs
from prepare_runtime_variant import require_tables_only_sources
from preview_word_short_budget import report_name


def visual_gate(rows):
    gate = lead_visual_gate(rows)
    for row in rows:
        for engine, value in row['rendered'].items():
            if value['after']['pages'] > value['before']['pages']:
                gate['visual_blockers'].append(dict(case=row['case'], language=row['language'], profile=row['profile'],
                    engine=engine, issue='page-count-increase', before_pages=value['before']['pages'], after_pages=value['after']['pages']))
    gate['visual_gate_passed'] = not gate['visual_blockers']
    return gate


def inputs(root, cases, after, compacted):
    manifest = json.loads((root / 'manifest.json').read_text())
    assert manifest['status'] == 'runtime-experiment'
    require_tables_only_sources(manifest['prototype']['observed_worker_sources'])
    expected = {(c + '-' + p, l, f) for c in cases for p in ['review', 'submission']
                for l in ['english', 'chinese'] for f in ['html', 'pdf', 'docx']}
    report = json.loads((root / 'missing-info-render-report.json').read_text())
    assert report['all_renders_succeeded'] and len(report['renders']) == len(expected)
    assert {(r['case'], r['language'], r['format']) for r in report['renders'] if r['rendered']} == expected
    previews = json.loads((root / report_name([c + '-' + p for c in cases for p in ['review', 'submission']])).read_text())
    assert previews['completed'] and len(previews['rows']) == len(cases) * 4
    assert {r['name'] for r in previews['rows']} == {c + '-' + l for c, l, f in expected}
    for row in previews['rows']:
        assert sha(root / 'renders' / (row['name'] + '.docx')) == row['docx_sha256']
        assert sha(root / 'word-preview' / (row['name'] + '.pdf')) == row['preview_sha256']
    for language in ['english', 'chinese']:
        if compacted: package = json.loads((root / (language + '.json')).read_text())
        else:
            with zipfile.ZipFile(root / (language + '.zip')) as archive: package = json.loads(archive.read('template/template.json'))
            assert sha(root / (language + '.zip')) == manifest['sha256'][language + '.zip']
        assert package == (patch(baseline(language), language)[0] if after else baseline(language))
        assert report['package_sha256'][language + '.zip'] == manifest['sha256'][language + '.zip']
    return manifest


def long_paragraph(pdf, language):
    placement = lead_placement(pdf, language)
    pages = subprocess.check_output(['pdftotext', '-layout', str(pdf), '-'], text=True).split('\f')
    end = [i for i, page in enumerate(pages, 1) for _ in range(compact(page).count(compact(AUTHORED_END)))]
    assert len(end) == 1, 'Long paragraph end missing or duplicated'
    assert end[0] > placement['first_answer_page'], 'Stress first paragraph must actually span pages'
    return dict(first_page=placement['first_answer_page'], last_page=end[0], freely_spans_pages=True)


def word_lead_delta(before, after, owned_text):
    """One exact paragraph style change; every authored run/other component stays."""
    with zipfile.ZipFile(before) as a, zipfile.ZipFile(after) as b:
        assert set(a.namelist()) == set(b.namelist()) and len(a.namelist()) == len(b.namelist())
        for name in a.namelist():
            if name not in ['word/document.xml', 'docProps/core.xml']:
                assert a.read(name) == b.read(name), ('Unexpected Word component change', name)
        style_tree = etree.fromstring(b.read('word/styles.xml'))
        leads = [s for s in style_tree.findall(qn('w:style')) if s.get(qn('w:styleId')) == 'PilotLead']
        assert len(leads) == 1
        keep = leads[0].find(qn('w:pPr') + '/' + qn('w:keepNext'))
        assert keep is not None and keep.get(qn('w:val')) in [None, '1', 'true', 'on']
        bodies = [etree.fromstring(z.read('word/document.xml')) for z in [a, b]]
        matches = [[p for p in tree.iter(qn('w:p')) if compact(''.join(p.itertext())) == compact(owned_text)] for tree in bodies]
        assert all(len(p) == 1 for p in matches), 'Owned Word lead must be unique in the public fixture'
        styles = [p[0].find(qn('w:pPr') + '/' + qn('w:pStyle')) for p in matches]
        assert [p.get(qn('w:val')) for p in styles] == ['FirstParagraph', 'PilotLead']
        styles[1].set(qn('w:val'), 'FirstParagraph')
        assert etree.tostring(bodies[0]) == etree.tostring(bodies[1]), 'Word changed outside the owned lead style'
        cores = [etree.fromstring(z.read('docProps/core.xml')) for z in [a, b]]
        for tree in cores:
            for name in ['created', 'modified']:
                nodes = tree.findall('{http://purl.org/dc/terms/}' + name); assert len(nodes) == 1
                value = datetime.fromisoformat(nodes[0].text.replace('Z', '+00:00')); assert value.tzinfo is not None
                nodes[0].text = 'VALIDATED-TIMESTAMP'
        assert etree.tostring(cores[0]) == etree.tostring(cores[1]), 'Other Word core metadata changed'
    return dict(changed_paragraphs=1, old_style='FirstParagraph', new_style='PilotLead', all_other_components_identical=True)


def visible_with_table_header(pdf, soup, document, word, case, profile):
    """Account for one *verified generated* Word table header, not arbitrary text.

    The long review fixture produces two header instances from one tblHeader.
    Chinese has an already-existing header-only continuation: retain that visual
    defect explicitly, even though the full authored inventory is intact.
    No file or rendered input is changed; this is the expected-count oracle.
    """
    if not (word and case == 'ethics-long' and profile == 'review'):
        return check_visible(pdf, soup, word=word)
    tables = soup.select('#q-ethical-issues > .answer > .answer-detail > table')
    assert len(tables) == 1
    source_rows = [[c.get_text() for c in r.find_all(['th', 'td'], recursive=False)] for r in tables[0].select('tr')]
    assert source_rows == [['Item', 'Value'], ['Original.csv', '0'], ['N/A', 'Retained.']]
    tables = [t for t in document.tables if [[c.text for c in r.cells] for r in t.rows] == source_rows]
    assert len(tables) == 1
    header = tables[0].rows[0]._tr.find(qn('w:trPr') + '/' + qn('w:tblHeader'))
    assert header is not None and header.get(qn('w:val')) == 'on'
    bbox = etree.fromstring(subprocess.check_output(['pdftotext', '-bbox-layout', str(pdf), '-']))
    headers = []; endings = []
    for page_index, page in enumerate(bbox.findall('.//{*}page'), 1):
        words = page.findall('.//{*}word')
        items = [w for w in words if w.text == 'Item']; values = [w for w in words if w.text == 'Value']
        if items or values:
            assert len(items) == len(values) == 1
            a, b = items[0], values[0]
            assert abs(float(a.get('yMin')) - float(b.get('yMin'))) < .1 and float(a.get('xMax')) < float(b.get('xMin'))
            headers.append(dict(page=page_index, y=float(a.get('yMin')), x=[float(a.get('xMin')), float(b.get('xMin'))]))
        for w in words:
            if w.text == 'Retained.': endings.append(dict(page=page_index, y=float(w.get('yMin'))))
    assert len(headers) == 2 and headers[1]['page'] == headers[0]['page'] + 1
    assert all(abs(a - b) < .1 for a, b in zip(headers[0]['x'], headers[1]['x']))
    assert len(endings) == 1 and endings[0]['page'] in [h['page'] for h in headers]
    assert endings[0]['y'] > next(h['y'] for h in headers if h['page'] == endings[0]['page'])
    expected = copy.deepcopy(soup)
    generated = expected.new_tag('span'); generated.string = 'ItemValue'; expected.body.append(generated)
    result = check_visible(pdf, expected, word=True)
    result['verified_generated_table_header'] = dict(extra_instances=1, columns=['Item', 'Value'], positions=headers,
        authored_last_cell=endings[0], header_only_continuation=endings[0]['page'] < headers[-1]['page'])
    return result


def run(before, long_before, after, fixtures, english, compacted=False):
    sys.path[:0] = [str(english / 'scripts'), str(english / 'tests')]
    manifests = {root: inputs(root, cases, root == after, compacted) for root, cases in
                 [(before, CASES[:2]), (long_before, CASES[2:]), (after, CASES)]}
    pairs = {language: templates(english, language) for language in ['english', 'chinese']}
    rows = []
    for case in CASES:
        roots = [long_before if case == 'ethics-long' else before, after]
        for language, locale in [('english', 'en'), ('chinese', 'zh-Hant')]:
            recipe = fixtures / locale / (case + '.json'); events = fixtures / locale / (case + '.events.json')
            model = recipe.parent / json.loads(recipe.read_text())['knowledge_model_package_id']
            model_hash = json.loads((fixtures / 'knowledge-model-sha256.json').read_text())[model.name] if compacted else sha(model)
            replies = replies_from(events)
            for profile in ['review', 'submission']:
                stem = case + '-' + profile + '-' + language; paths = [root / 'renders' / stem for root in roots]
                for fmt in ['html', 'pdf', 'docx']:
                    receipts = [json.loads(p.with_suffix('.' + fmt + '.fixture.json').read_text()) for p in paths]
                    for key in ['recipe_sha256', 'events_sha256', 'km_sha256', 'output_profile', 'format_uuid', 'runner_sha256']:
                        assert receipts[0][key] == receipts[1][key], (stem, fmt, key)
                    for receipt, root in zip(receipts, roots):
                        assert receipt['recipe_sha256'] == sha(recipe) and receipt['events_sha256'] == sha(events)
                        assert receipt['km_sha256'] == model_hash and receipt['output_profile'] == profile
                        assert receipt['package_sha256'] == manifests[root]['sha256'][language + '.zip']
                if compacted:
                    fonts = [json.loads(p.with_suffix('.html.compact.json').read_text()) for p in paths]
                    for p, receipt in zip(paths, fonts): assert sha(p.with_suffix('.html')) == receipt['compact_html_sha256']
                    assert fonts[0]['fonts'] == fonts[1]['fonts']
                    if profile == 'review': assert fonts[0]['original_html_sha256'] == fonts[1]['original_html_sha256']
                old, new = [BeautifulSoup(p.with_suffix('.html').read_text(), 'html.parser') for p in paths]
                changes = compare(old, new, pairs[language][0], replies, language) if profile == 'submission' else []
                assert len(changes) == ((1 if case == 'ethics-answered' else 2) if profile == 'submission' else 0)
                if profile == 'review':
                    assert paths[0].with_suffix('.html').read_bytes() == paths[1].with_suffix('.html').read_bytes()
                    compare_docx(*[p.with_suffix('.docx') for p in paths])
                word_delta = (word_lead_delta(*[p.with_suffix('.docx') for p in paths], changes[-1]['owned_text'])
                              if profile == 'submission' else None)
                docs = [Document(p.with_suffix('.docx')) for p in paths]
                paragraphs = [word_html_inventory(d, s) for d, s in zip(docs, [old, new])]
                assert [sorted(r.target_ref for r in d.part.rels.values() if r.is_external) for d in docs][0] == [
                    sorted(r.target_ref for r in d.part.rels.values() if r.is_external) for d in docs][1]
                with zipfile.ZipFile(paths[0].with_suffix('.docx')) as a, zipfile.ZipFile(paths[1].with_suffix('.docx')) as b:
                    for name in ['word/styles.xml', 'word/fontTable.xml', 'word/numbering.xml']: assert a.read(name) == b.read(name)
                rendered = {}
                for engine, pdfs in [('native_pdf', [p.with_suffix('.pdf') for p in paths]),
                                     ('word_preview', [root / 'word-preview' / (stem + '.pdf') for root in roots])]:
                    values = [visible_with_table_header(pdf, soup, document, engine == 'word_preview', case, profile)
                              for pdf, soup, document in zip(pdfs, [old, new], docs)]
                    assert not any(v['bounds_issues'] for v in values), (stem, engine, 'Text outside page')
                    # Retain every pair, but an increase still blocks the gate.
                    # This is not permission to waive a long-answer regression.
                    assert len(values[1]['line_box_overlaps']) <= len(values[0]['line_box_overlaps']), (stem, engine, 'More metric overlaps')
                    if profile == 'review': assert geometry(pdfs[0]) == geometry(pdfs[1]) and raster_digest(pdfs[0]) == raster_digest(pdfs[1])
                    rendered[engine] = dict(before=values[0], after=values[1], before_sha256=sha(pdfs[0]), after_sha256=sha(pdfs[1]),
                        lead_placement={phase: lead_placement(pdf, language) for phase, pdf in zip(['before', 'after'], pdfs)})
                    if case == 'ethics-long': rendered[engine]['long_first_paragraph'] = {
                        phase: long_paragraph(pdf, language) for phase, pdf in zip(['before', 'after'], pdfs)}
                preview = verify_preview_paragraphs(docs[1], after / 'word-preview' / (stem + '.pdf'), new)
                artifacts = {fmt: sha(paths[1].with_suffix('.' + fmt)) for fmt in ['html', 'pdf', 'docx']}
                if compacted: artifacts['html'] = fonts[1]['original_html_sha256']
                rows.append(dict(case=case, language=language, profile=profile, changes=changes, unchanged_control=profile == 'review',
                    rendered=rendered, word_lead_style_delta=word_delta,
                    word_html_paragraph_inventory=paragraphs, preview_paragraphs=preview, artifacts=artifacts))
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['before', 'long-before', 'after', 'fixtures', 'english', 'output']: p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args(); assert not a.output.exists()
    report = dict(passed=False, prototype_only=True, source_integrated=False, release_acceptance=False,
        global_switch_complete=False, microsoft_word_acceptance=False, checker_sha256=sha(Path(__file__)),
        recipe_sha256=sha(Path(__file__).with_name('lead_recipe.py')))
    try:
        report['rows'] = run(a.before, a.long_before, a.after, a.fixtures, a.english.resolve())
        gate = visual_gate(report['rows'])
        report.update(content_contract_passed=True, **gate)
        report['known_preexisting_visual_issues'] = [dict(case=row['case'], language=row['language'], profile=row['profile'],
            engine=engine, issue='header-only-table-continuation', before=value['before']['verified_generated_table_header'],
            after=value['after']['verified_generated_table_header']) for row in report['rows']
            for engine, value in row['rendered'].items()
            if value['after'].get('verified_generated_table_header', {}).get('header_only_continuation')]
        report['passed'] = gate['visual_gate_passed']
    except Exception as error: report['failure'] = repr(error); raise
    finally: a.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(passed=report['passed'], pairs=len(report['rows']), visual_gate_passed=report['visual_gate_passed'],
                          blockers=report['visual_blockers'])))


if __name__ == '__main__': main()
