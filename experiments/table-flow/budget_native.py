"""Exact native budget omission proof; inherited visual defects remain blockers."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile
from bs4 import BeautifulSoup
from docx import Document
from docx.oxml.ns import qn
from lxml import etree
from budget_recipe import ROOT, ARCHIVE, baseline, patch
from budget_probe import compare, replies_from
from budget_trial import CASES

sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'experiments/ethics-lead'),
               str(ROOT / 'experiments/mixed-budget-header')]
from artifact_utils import sha
from lead_native import inputs as lead_inputs, visible_with_table_header, long_paragraph, lead_placement
from check_submission_preview_native import compare_docx, word_html_inventory
from check_header_controls import raster_digest
from rehearse_profile_pagination import geometry
from check_word_short_budget_outputs import verify_preview_paragraphs
from notice_probe import compact
from compact import compact_source
from prepare_runtime_variant import require_tables_only_sources

PREVIEW_REPORT = 'word-preview-table-flow-resumed.json'


def previews(root):
    """Resume only hash-bound earlier previews, retaining the incomplete receipt."""
    render = json.loads((root / 'missing-info-render-report.json').read_text())
    assert render['all_renders_succeeded']
    target = root / PREVIEW_REPORT; assert not target.exists()
    earlier = list(root.glob('word-preview-*.json')); assert len(earlier) == 1
    prior = json.loads(earlier[0].read_text()); assert not prior.get('completed')
    names = [c + '-' + p + '-' + l for c in CASES for p in ['review', 'submission'] for l in ['english', 'chinese']]
    reused = {r['name']: r for r in prior['rows']}; assert len(reused) == len(prior['rows'])
    assert set(reused) <= set(names)
    assert {f.stem for f in (root / 'word-preview').glob('*.pdf')} == set(reused)
    report = dict(completed=False, release_acceptance=False, microsoft_word_acceptance=False,
                  resumed_from=earlier[0].name, resumed_receipt_sha256=sha(earlier[0]),
                  checker_sha256=sha(Path(__file__)), rows=[])
    for name in names:
        source = root / 'renders' / (name + '.docx'); dest = root / 'word-preview' / (name + '.pdf')
        if name in reused:
            assert sha(source) == reused[name]['docx_sha256'] and sha(dest) == reused[name]['preview_sha256']
        else:
            assert source.is_file() and not dest.exists()
            with tempfile.TemporaryDirectory(prefix='empty-budget-lo-') as folder:
                subprocess.run(['libreoffice', '-env:UserInstallation=' + Path(folder).as_uri(), '--headless',
                                '--convert-to', 'pdf', '--outdir', str(dest.parent), str(source)],
                               capture_output=True, check=True, timeout=90)
        report['rows'].append(dict(name=name, docx_sha256=sha(source), preview_sha256=sha(dest), reused=name in reused))
        target.write_text(json.dumps(report, indent=2) + '\n'); print(name, flush=True)
    report['completed'] = True; target.write_text(json.dumps(report, indent=2) + '\n')


def inputs(root, compacted):
    manifest = json.loads((root / 'manifest.json').read_text()); assert manifest['status'] == 'runtime-experiment'
    require_tables_only_sources(manifest['prototype']['observed_worker_sources'])
    report = json.loads((root / 'missing-info-render-report.json').read_text())
    expected = {(c + '-' + p, l, f) for c in CASES for p in ['review', 'submission']
                for l in ['english', 'chinese'] for f in ['html', 'pdf', 'docx']}
    assert report['all_renders_succeeded'] and len(report['renders']) == len(expected)
    assert {(r['case'], r['language'], r['format']) for r in report['renders'] if r['rendered']} == expected
    preview = json.loads((root / PREVIEW_REPORT).read_text()); assert preview['completed'] and len(preview['rows']) == 12
    assert {r['name'] for r in preview['rows']} == {n + '-' + l for n, l, _ in expected}
    assert sha(root / preview['resumed_from']) == preview['resumed_receipt_sha256']
    for row in preview['rows']:
        assert sha(root / 'renders' / (row['name'] + '.docx')) == row['docx_sha256']
        assert sha(root / 'word-preview' / (row['name'] + '.pdf')) == row['preview_sha256']
    for language in ['english', 'chinese']:
        if compacted: package = json.loads((root / (language + '.json')).read_text())
        else:
            with zipfile.ZipFile(root / (language + '.zip')) as z: package = json.loads(z.read('template/template.json'))
            assert sha(root / (language + '.zip')) == manifest['sha256'][language + '.zip']
        expected, operations = patch(baseline(language), language)
        assert package == expected
        assert manifest['prototype']['packages'][language + '.zip']['operations'] == operations
        assert report['package_sha256'][language + '.zip'] == manifest['sha256'][language + '.zip']
    return manifest


def word_delta(before, after, changes):
    """Remove only unique, direct Q15 name/heading paragraphs from the old XML."""
    with zipfile.ZipFile(before) as a, zipfile.ZipFile(after) as b:
        assert len(a.namelist()) == len(b.namelist()) and set(a.namelist()) == set(b.namelist())
        for name in a.namelist():
            if name not in ['word/document.xml', 'docProps/core.xml']:
                assert a.read(name) == b.read(name), ('Unexpected Word component', name)
        trees = [etree.fromstring(z.read('word/document.xml')) for z in [a, b]]
        body = trees[0].find(qn('w:body')); nodes = list(body)
        heading = [i for i, n in enumerate(nodes) if n.tag == qn('w:p') and
                   n.find(qn('w:pPr') + '/' + qn('w:pStyle')) is not None and
                   n.find(qn('w:pPr') + '/' + qn('w:pStyle')).get(qn('w:val')) == 'Heading3' and
                   compact(''.join(n.itertext())).startswith('15.')]
        assert len(heading) == 1
        for change in changes:
            value = compact(change['label'])
            if not value: continue
            candidates = [n for n in nodes[heading[0]+1:] if n.tag == qn('w:p') and compact(''.join(n.itertext())) == value]
            assert len(candidates) == 1, 'Only an unambiguous direct owned Q15 label can be omitted'
            body.remove(candidates[0])
        assert etree.tostring(trees[0]) == etree.tostring(trees[1]), 'Unexpected Word XML delta'
        cores = [etree.fromstring(z.read('docProps/core.xml')) for z in [a, b]]
        for tree in cores:
            for name in ['created', 'modified']:
                nodes = tree.findall('{http://purl.org/dc/terms/}' + name); assert len(nodes) == 1
                assert datetime.fromisoformat(nodes[0].text.replace('Z', '+00:00')).tzinfo is not None
                nodes[0].text = 'VALIDATED-TIMESTAMP'
        assert etree.tostring(cores[0]) == etree.tostring(cores[1])
    return dict(omitted_direct_q15_paragraphs=sum(bool(compact(c['label'])) for c in changes),
                all_other_components_identical=True)


def run(after, fixtures, english, compacted=False):
    sys.path[:0] = [str(english / 'scripts'), str(english / 'tests')]
    before = ARCHIVE / 'after'
    manifests = {before: lead_inputs(before, CASES, True, True), after: inputs(after, compacted)}
    history = json.loads((ARCHIVE / 'provenance/native.json').read_text()); rows = []
    for case in CASES:
        for language, locale in [('english', 'en'), ('chinese', 'zh-Hant')]:
            recipe = fixtures / locale / (case + '.json'); events = fixtures / locale / (case + '.events.json')
            model = recipe.parent / json.loads(recipe.read_text())['knowledge_model_package_id']
            model_hash = json.loads((fixtures / 'knowledge-model-sha256.json').read_text())[model.name] if compacted else sha(model)
            replies = replies_from(events)
            for profile in ['review', 'submission']:
                stem = case + '-' + profile + '-' + language
                paths = [r / 'renders' / stem for r in [before, after]]
                for fmt in ['html', 'pdf', 'docx']:
                    receipts = [json.loads(p.with_suffix('.' + fmt + '.fixture.json').read_text()) for p in paths]
                    for key in ['recipe_sha256', 'events_sha256', 'km_sha256', 'output_profile', 'format_uuid', 'runner_sha256']:
                        assert receipts[0][key] == receipts[1][key], (stem, fmt, key)
                    for receipt, root in zip(receipts, [before, after]):
                        assert receipt['recipe_sha256'] == sha(recipe) and receipt['events_sha256'] == sha(events)
                        assert receipt['km_sha256'] == model_hash and receipt['output_profile'] == profile
                        assert receipt['package_sha256'] == manifests[root]['sha256'][language + '.zip']
                old_receipt = json.loads(paths[0].with_suffix('.html.compact.json').read_text())
                assert sha(paths[0].with_suffix('.html')) == old_receipt['compact_html_sha256']
                if compacted:
                    new_receipt = json.loads(paths[1].with_suffix('.html.compact.json').read_text())
                    assert sha(paths[1].with_suffix('.html')) == new_receipt['compact_html_sha256']
                    fonts = new_receipt['fonts']; raw = paths[1].with_suffix('.html').read_bytes()
                    html_sha = new_receipt['original_html_sha256']
                else:
                    raw, fonts = compact_source(paths[1].with_suffix('.html').read_bytes())
                    html_sha = sha(paths[1].with_suffix('.html'))
                assert fonts == old_receipt['fonts']
                old = BeautifulSoup(paths[0].with_suffix('.html').read_text(), 'html.parser')
                new = BeautifulSoup(raw, 'html.parser')
                changes = compare(old, new, replies) if profile == 'submission' else []
                assert len(changes) == (1 if profile == 'submission' else 0)
                if profile == 'review':
                    assert html_sha == old_receipt['original_html_sha256'] and raw == paths[0].with_suffix('.html').read_bytes()
                    compare_docx(*[p.with_suffix('.docx') for p in paths])
                delta = word_delta(*[p.with_suffix('.docx') for p in paths], changes)
                docs = [Document(p.with_suffix('.docx')) for p in paths]
                paragraphs = [word_html_inventory(d, s) for d, s in zip(docs, [old, new])]
                assert [sorted(r.target_ref for r in d.part.rels.values() if r.is_external) for d in docs][0] == [
                    sorted(r.target_ref for r in d.part.rels.values() if r.is_external) for d in docs][1]
                original = next(r for r in history['rows'] if (r['case'], r['language'], r['profile']) == (case, language, profile))
                rendered = {}
                for engine, pdfs in [('native_pdf', [p.with_suffix('.pdf') for p in paths]),
                                     ('word_preview', [r / 'word-preview' / (stem + '.pdf') for r in [before, after]])]:
                    values = [visible_with_table_header(pdf, soup, doc, engine == 'word_preview', case, profile)
                              for pdf, soup, doc in zip(pdfs, [old, new], docs)]
                    assert not any(v['bounds_issues'] for v in values)
                    assert len(values[1]['line_box_overlaps']) <= len(values[0]['line_box_overlaps'])
                    if profile == 'review': assert geometry(pdfs[0]) == geometry(pdfs[1]) and raster_digest(pdfs[0]) == raster_digest(pdfs[1])
                    rendered[engine] = dict(before=values[0], after=values[1], before_sha256=sha(pdfs[0]), after_sha256=sha(pdfs[1]),
                        historical_page_limit=original['rendered'][engine]['before']['pages'],
                        lead_placement={phase: lead_placement(pdf, language) for phase, pdf in zip(['before', 'after'], pdfs)})
                    if case == 'ethics-long': rendered[engine]['long_first_paragraph'] = {
                        phase: long_paragraph(pdf, language) for phase, pdf in zip(['before', 'after'], pdfs)}
                preview = verify_preview_paragraphs(docs[1], after / 'word-preview' / (stem + '.pdf'), new)
                artifacts = {fmt: sha(paths[1].with_suffix('.' + fmt)) for fmt in ['html', 'pdf', 'docx']}; artifacts['html'] = html_sha
                rows.append(dict(case=case, language=language, profile=profile, changes=changes,
                    unchanged_control=profile == 'review', rendered=rendered, word_delta=delta,
                    word_html_paragraph_inventory=paragraphs, preview_paragraphs=preview, artifacts=artifacts))
    return rows


def gate(rows):
    blockers = []
    for row in rows:
        for engine, value in row['rendered'].items():
            info = dict(case=row['case'], language=row['language'], profile=row['profile'], engine=engine)
            limit = min(value['before']['pages'], value['historical_page_limit'])
            if value['after']['pages'] > limit:
                blockers.append(dict(**info, issue='page-count-increase', limit=limit, after_pages=value['after']['pages']))
            if row['profile'] == 'submission' and not value['lead_placement']['after']['together']:
                blockers.append(dict(**info, issue='separated-owned-lead'))
            if value['after'].get('verified_generated_table_header', {}).get('header_only_continuation'):
                blockers.append(dict(**info, issue='header-only-table-continuation', preexisting=True))
    return dict(visual_gate_passed=not blockers, visual_blockers=blockers)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('action', choices=['preview', 'check'])
    p.add_argument('--after', type=Path, required=True)
    for name in ['fixtures', 'english', 'output']: p.add_argument('--' + name, type=Path)
    a = p.parse_args()
    if a.action == 'preview': previews(a.after)
    else:
        assert not a.output.exists()
        report = dict(passed=False, prototype_only=True, source_integrated=False, source_integration_allowed=False,
            release_acceptance=False, global_switch_complete=False, microsoft_word_acceptance=False,
            checker_sha256=sha(Path(__file__)), recipe_sha256=sha(Path(__file__).with_name('budget_recipe.py')))
        try:
            report['rows'] = run(a.after, a.fixtures, a.english.resolve())
            report.update(content_contract_passed=True, **gate(report['rows']))
            report['passed'] = report['visual_gate_passed']
        except Exception as error: report['failure'] = repr(error); raise
        finally: a.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps(dict(passed=report['passed'], pairs=len(report['rows']), visual_blockers=report['visual_blockers'])))
