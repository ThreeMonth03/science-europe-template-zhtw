"""Actual Q9 PDF/DOCX and Word preview checks; never treat prompt hiding as compliance."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import zipfile
from bs4 import BeautifulSoup
from docx import Document

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'scripts'), str(Path(__file__).parent)]
from artifact_utils import sha
from ethics_recipe import baseline, patch
from ethics_probe import compare, replies_from
from ethics_trial import CASES
from check_submission_preview_native import compare_docx, word_html_inventory
from check_header_controls import raster_digest
from rehearse_profile_pagination import geometry
from notice_native import check_visible
from check_word_short_budget_outputs import verify_preview_paragraphs
from prepare_runtime_variant import require_tables_only_sources
from preview_word_short_budget import report_name
from notice_probe import compact


def lead_placement(pdf, language):
    """Fixture-specific reading gate: the purpose lead must reach its first answer.

    Exact literal anchors are unique in these two public controls. This is not
    a general PDF semantic parser and does not normalize away punctuation.
    """
    lead = ('The purpose of processing the personal data can be described as follows:' if language == 'english'
            else '處理個人資料的目的可描述如下：')
    authored = 'AUTHORED-PURPOSE: N/A / 0 / Original.csv.'
    pages = subprocess.check_output(['pdftotext', '-layout', str(pdf), '-'], text=True).split('\f')
    positions = []
    for anchor in [lead, authored]:
        found = [i for i, page in enumerate(pages, 1) for _ in range(compact(page).count(compact(anchor)))]
        assert len(found) == 1, ('Missing or ambiguous reading anchor', str(pdf), anchor, found)
        positions.append(found[0])
    return dict(lead_page=positions[0], first_answer_page=positions[1], together=positions[0] == positions[1])


def visual_gate(rows):
    blockers = []
    for row in rows:
        for engine, result in row['rendered'].items():
            layout = result['lead_placement']
            if not layout['after']['together']:
                blockers.append(dict(case=row['case'], language=row['language'], profile=row['profile'], engine=engine,
                    new_regression=layout['before']['together'], **layout))
    return dict(visual_gate_passed=not blockers, visual_blockers=blockers)


def run(before, after, fixtures, english, compacted=False):
    sys.path[:0] = [str(english / 'scripts'), str(english / 'tests')]
    roots = [before, after]
    manifests = [json.loads((root / 'manifest.json').read_text()) for root in roots]
    for root, manifest in zip(roots, manifests):
        assert manifest['status'] == 'runtime-experiment'
        require_tables_only_sources(manifest['prototype']['observed_worker_sources'])
        report = json.loads((root / 'missing-info-render-report.json').read_text())
        expected = {(c + '-' + p, lang, fmt) for c in CASES for p in ['review', 'submission']
                    for lang in ['english', 'chinese'] for fmt in ['html', 'pdf', 'docx']}
        assert report['all_renders_succeeded'] and len(report['renders']) == len(expected)
        assert {(r['case'], r['language'], r['format']) for r in report['renders'] if r['rendered']} == expected
        previews = json.loads((root / report_name([c + '-' + p for c in CASES for p in ['review', 'submission']])).read_text())
        assert previews['completed'] and len(previews['rows']) == 8
        for row in previews['rows']:
            assert sha(root / 'renders' / (row['name'] + '.docx')) == row['docx_sha256']
            assert sha(root / 'word-preview' / (row['name'] + '.pdf')) == row['preview_sha256']
        for language in ['english', 'chinese']:
            if compacted: package = json.loads((root / (language + '.json')).read_text())
            else:
                with zipfile.ZipFile(root / (language + '.zip')) as zip_file:
                    package = json.loads(zip_file.read('template/template.json'))
                assert sha(root / (language + '.zip')) == manifest['sha256'][language + '.zip']
            assert package == (baseline(language) if root == before else patch(baseline(language), language)[0])
            assert report['package_sha256'][language + '.zip'] == manifest['sha256'][language + '.zip']
    rows = []
    for case in CASES:
        for language, locale in [('english', 'en'), ('chinese', 'zh-Hant')]:
            recipe = fixtures / locale / (case + '.json'); events = fixtures / locale / (case + '.events.json')
            model = recipe.parent / json.loads(recipe.read_text())['knowledge_model_package_id']
            model_hash = json.loads((fixtures / 'knowledge-model-sha256.json').read_text())[model.name] if compacted else sha(model)
            replies = replies_from(events)
            for profile in ['review', 'submission']:
                stem = case + '-' + profile + '-' + language
                paths = [r / 'renders' / stem for r in roots]
                for fmt in ['html', 'pdf', 'docx']:
                    receipts = [json.loads(p.with_suffix('.' + fmt + '.fixture.json').read_text()) for p in paths]
                    for key in ['recipe_sha256', 'events_sha256', 'km_sha256', 'output_profile', 'format_uuid', 'runner_sha256']:
                        assert receipts[0][key] == receipts[1][key], (stem, fmt, key)
                    for receipt, manifest in zip(receipts, manifests):
                        assert receipt['recipe_sha256'] == sha(recipe) and receipt['events_sha256'] == sha(events)
                        assert receipt['km_sha256'] == model_hash and receipt['output_profile'] == profile
                        assert receipt['package_sha256'] == manifest['sha256'][language + '.zip']
                same = profile == 'review' or case == 'ethics-answered'
                if compacted:
                    font_receipts = [json.loads(p.with_suffix('.html.compact.json').read_text()) for p in paths]
                    for p, receipt in zip(paths, font_receipts): assert sha(p.with_suffix('.html')) == receipt['compact_html_sha256']
                    assert font_receipts[0]['fonts'] == font_receipts[1]['fonts']
                    if same: assert font_receipts[0]['original_html_sha256'] == font_receipts[1]['original_html_sha256']
                old, new = [BeautifulSoup(p.with_suffix('.html').read_text(), 'html.parser') for p in paths]
                changes = compare(old, new, language, replies) if profile == 'submission' else []
                assert len(changes) == (3 if case == 'ethics-missing' and profile == 'submission' else 0)
                if same:
                    assert paths[0].with_suffix('.html').read_bytes() == paths[1].with_suffix('.html').read_bytes()
                    compare_docx(*[p.with_suffix('.docx') for p in paths])
                docs = [Document(p.with_suffix('.docx')) for p in paths]
                word_inventory = [word_html_inventory(d, s) for d, s in zip(docs, [old, new])]
                assert [sorted(r.target_ref for r in d.part.rels.values() if r.is_external) for d in docs][0] == [
                    sorted(r.target_ref for r in d.part.rels.values() if r.is_external) for d in docs][1]
                with zipfile.ZipFile(paths[0].with_suffix('.docx')) as a, zipfile.ZipFile(paths[1].with_suffix('.docx')) as b:
                    for name in ['word/styles.xml', 'word/fontTable.xml', 'word/numbering.xml']: assert a.read(name) == b.read(name)
                rendered = {}
                for kind, pdfs in [('native_pdf', [p.with_suffix('.pdf') for p in paths]),
                                   ('word_preview', [r / 'word-preview' / (stem + '.pdf') for r in roots])]:
                    values = [check_visible(p, soup, word=kind == 'word_preview') for p, soup in zip(pdfs, [old, new])]
                    assert not any(v['bounds_issues'] for v in values), (stem, kind, 'Text outside page')
                    assert values[1]['pages'] <= values[0]['pages'], (stem, kind, 'More pages')
                    assert len(values[1]['line_box_overlaps']) <= len(values[0]['line_box_overlaps'])
                    if same:
                        assert geometry(pdfs[0]) == geometry(pdfs[1]) and raster_digest(pdfs[0]) == raster_digest(pdfs[1])
                    rendered[kind] = dict(before=values[0], after=values[1], before_sha256=sha(pdfs[0]), after_sha256=sha(pdfs[1]),
                        lead_placement={phase: lead_placement(pdf, language) for phase, pdf in zip(['before', 'after'], pdfs)})
                visible = verify_preview_paragraphs(docs[1], after / 'word-preview' / (stem + '.pdf'), new)
                artifacts = {fmt: sha(paths[1].with_suffix('.' + fmt)) for fmt in ['html', 'pdf', 'docx']}
                if compacted: artifacts['html'] = font_receipts[1]['original_html_sha256']
                rows.append(dict(case=case, language=language, profile=profile, changes=changes, unchanged_control=same,
                    rendered=rendered, word_html_paragraph_inventory=word_inventory, preview_paragraphs=visible, artifacts=artifacts))
    return rows


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['before', 'after', 'fixtures', 'english', 'output']: p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args(); assert not a.output.exists()
    report = dict(passed=False, prototype_only=True, source_integrated=False, release_acceptance=False,
        global_switch_complete=False, microsoft_word_acceptance=False, checker_sha256=sha(Path(__file__)),
        recipe_sha256=sha(Path(__file__).with_name('ethics_recipe.py')))
    try:
        report['rows'] = run(a.before, a.after, a.fixtures, a.english.resolve())
        report.update(passed=True, content_contract_passed=True, **visual_gate(report['rows']))
    except Exception as error: report['failure'] = repr(error); raise
    finally: a.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(content_contract_passed=True, pairs=len(report['rows']),
                          visual_gate_passed=report['visual_gate_passed'], blockers=len(report['visual_blockers']))))
