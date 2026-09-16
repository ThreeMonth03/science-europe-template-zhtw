"""Bounded 0.3.30 PDF-panel delta; identical HTML answers and editable Word."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import zipfile
from bs4 import BeautifulSoup
from docx import Document
from lxml import etree
from artifact_utils import sha
from check_archive_basis_outputs import without_continuation_headers
from check_budget_outputs import body, xml
from check_budget_spacing_outputs import pdf_raw_page_texts, line_box_overlaps
from check_identifier_concise_outputs import verified_list_suffixes
from check_narrative_outputs import compact
from check_pdf_budget_reading_outputs import complete_marker_lines, positioned_budget_lists, external_pdf_links
from check_short_budget_outputs import question_pages
from check_word_rhythm_outputs import assert_styles, inspect_preview
from check_word_short_budget_outputs import verify_preview_paragraphs
from compare_runtime_outputs import markers

CASES = ['preservation-partial', 'archive-migration-gaps', 'archive-single-gap',
         'budget-long-archive-gaps', 'personal-transfer-complete', 'preservation-custom', 'empty', 'negative']
EXTRA = {'archive-migration-gaps', 'archive-single-gap', 'budget-long-archive-gaps'}
EXPECTED = {'preservation-partial': [0, 1], 'archive-migration-gaps': [2], 'budget-long-archive-gaps': [0, 1]}


def word_unchanged(before, after):
    assert [xml(n) for n in body(before)] == [xml(n) for n in body(after)], 'Word body/style/answer changed'
    links = lambda d: sorted(r.target_ref for r in d.part.rels.values() if r.is_external)
    assert links(before) == links(after), 'Word external targets changed'
    assert xml(before.part.numbering_part.element) == xml(after.part.numbering_part.element)


def body_geometry(bbox, soup):
    """Exclude cover pages only, not arbitrary dated text in authored answers."""
    pages = etree.fromstring(bbox).findall('.//{*}page')
    heading = compact(soup.select_one('.question h3').get_text())
    texts = [compact(''.join(w.text or '' for w in p.findall('.//{*}word'))) for p in pages]
    assert sum(t.count(heading) for t in texts) == 1, 'Ambiguous first question'
    index = next(i for i, text in enumerate(texts) if heading in text)
    return [etree.tostring(p) for p in pages[index:]]


def prompt_geometry(bbox, text):
    target = compact(text); found = []
    for number, page in enumerate(etree.fromstring(bbox).findall('.//{*}page'), 1):
        lines = sorted([(float(n.get('yMin')), float(n.get('xMin')), float(n.get('yMax')),
                         float(n.get('xMax')), compact(''.join(n.itertext()))) for n in page.findall('.//{*}line')])
        for y, x, _, _, value in lines:
            if not value or not target.startswith(value): continue
            column = [line for line in lines if line[0] >= y and abs(line[1]-x) < .75]
            joined = ''; previous = y; signature = []
            for yy, xx, bottom, right, value in column[:6]:
                if yy-previous > 22.5: break
                joined += value; previous = yy
                signature.append([value, round(xx, 3), round(right-xx, 3), round(bottom-yy, 3), round(yy-y, 3)])
                if joined == target:
                    found.append({'page': number, 'top': y, 'bottom': bottom, 'lines': signature}); break
                if not target.startswith(joined): break
    assert len(found) == 1, ('Missing/ambiguous complete prompt', text, found)
    return found[0]


def pair_delta(old_bbox, new_bbox, soup, pairs):
    result = []
    for first, last in pairs:
        texts = [soup.select_one('.post-project-archive p[data-fact-id="'+f+'"]').get_text() for f in [first, last]]
        before = [prompt_geometry(old_bbox, text) for text in texts]
        after = [prompt_geometry(new_bbox, text) for text in texts]
        assert after[0]['page'] == after[1]['page'], 'Bounded pair split across pages'
        assert [g['lines'] for g in before] == [g['lines'] for g in after], 'Prompt font metrics/width/wrapping changed'
        assert before[1]['page'] in [before[0]['page'], before[0]['page']+1]
        split = before[0]['page'] != before[1]['page']
        old_span = None if split else before[1]['bottom']-before[0]['top']
        new_span = after[1]['bottom']-after[0]['top']
        assert new_span > 0
        if not split: assert new_span < old_span, 'Pair did not become less fragmented'
        result.append({'facts': [first, last], 'before_page': before[0]['page'], 'after_page': after[0]['page'],
                       'before_pages': [g['page'] for g in before], 'baseline_pair_split': split,
                       'before_span_pt': old_span, 'after_span_pt': new_span,
                       'reduced_span_pt': None if split else old_span-new_span, 'unchanged_line_metrics': True})
    return result


def pdf_delta(old, new, before, after, pairs):
    pages = [pdf_raw_page_texts(f) for f in [old, new]]
    boxes = [subprocess.check_output(['pdftotext', '-bbox-layout', str(f), '-']) for f in [old, new]]
    cleaned = []; bullets = []; continuations = []
    for texts, bbox, soup in zip(pages, boxes, [before, after]):
        # Earlier questions can contain inline custom list markers. They do
        # not move in this Q11-only delta; leave them untouched, and bind only
        # generated suffix markers from the first potentially moving page.
        heading = compact(soup.select_one('#q-data-preservation h3').get_text())
        start = next(i for i, text in enumerate(texts) if heading in text)
        text, bound = verified_list_suffixes(texts, bbox, soup, start)
        text, repeats = without_continuation_headers(text, soup)
        cleaned.append(''.join(question_pages(text, soup))); bullets.append(bound); continuations.append(repeats)
    assert cleaned[0] == cleaned[1], 'PDF answer/order/punctuation changed'
    assert bullets[0] == bullets[1], 'Generated list marker/text/indent changed'
    assert line_box_overlaps(boxes[0]) == line_box_overlaps(boxes[1]), 'New PDF metric-box overlap'
    assert external_pdf_links(old) == external_pdf_links(new), 'PDF link target/text changed'
    if not pairs:
        assert body_geometry(boxes[0], before) == body_geometry(boxes[1], after), 'Control body geometry changed'
    result = {'unchanged_body_text': True, 'bound_list_markers': sum(bullets[1].values()),
              'verified_continuation_headers_before_after': continuations,
              'unchanged_control_geometry': not pairs, 'panels': pair_delta(*boxes, after, pairs)}
    if 'BUDGET-PARA-' in after.get_text():
        purposes = [compact(p.get_text()) for p in after.select('.resource-table .answer-detail p') if 'BUDGET-PARA-' in p.get_text()]
        assert len(purposes) == 60
        assert all(sum(t.count(p) for t in pages[1]) == 1 for p in purposes), 'Long paragraph split/lost/duplicated'
        result['long_budget'] = {'complete_purpose_paragraphs': 60,
                                'complete_marker_lines': complete_marker_lines(boxes[1], after),
                                'positioned_list_items': positioned_budget_lists(boxes[1], after)}
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['build', 'prior', 'prior-extra', 'english']: p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--cases', nargs='+', default=CASES); p.add_argument('--output', type=Path)
    a = p.parse_args(); sys.path.insert(0, str(a.english.resolve()/'scripts'))
    from probe_archive_gap_panels import FIRST, LAST, PAIRS
    import check_missing_info_outputs as missing
    missing.HERE = a.english.resolve()
    target = a.output or a.build/'archive-gap-report.json'; assert not target.exists(), 'Never overwrite evidence'
    helpers = ['artifact_utils.py', 'check_archive_basis_outputs.py', 'check_budget_outputs.py',
               'check_budget_spacing_outputs.py', 'check_identifier_concise_outputs.py', 'check_narrative_outputs.py',
               'check_pdf_budget_reading_outputs.py', 'check_short_budget_outputs.py', 'check_missing_info_outputs.py',
               'check_word_rhythm_outputs.py', 'check_word_short_budget_outputs.py', 'compare_runtime_outputs.py']
    report = {'selected_checks_passed': False, 'release_acceptance': False, 'rows': [],
              'checker_sha256': sha(Path(__file__)), 'selector_sha256': sha(a.english/'scripts/probe_archive_gap_panels.py'),
              'helper_sha256': {n: sha(Path(__file__).with_name(n)) for n in helpers},
              'package_sha256': {n: sha(a.build/n) for n in ['english.zip', 'chinese.zip']},
              'limits': ['Eight synthetic cases per language, not all questionnaires',
                         'Only named adjacent plain missing pairs in Q11; not whole-DMP acceptance',
                         'PDF text comparison normalizes whitespace; HTML and Word retain exact body content/formatting',
                         'Cover date/version may differ; all Word/control-PDF body page geometry remains exact',
                         'LibreOffice previews are not Microsoft Word acceptance; local reviewed tables-only worker']}
    try:
        for case in a.cases:
            assert case in CASES
            prior = a.prior_extra if case in EXTRA else a.prior
            for language in ['english', 'chinese']:
                stem = case+'-'+language; old = prior/'renders'/stem; new = a.build/'renders'/stem
                before = BeautifulSoup(old.with_suffix('.html').read_text(), 'html.parser')
                row, after = missing.inspect(a.build, case, language)
                assert str(before.select_one('#dmp-content')) == str(after.select_one('#dmp-content')), 'HTML body changed'
                assert markers(before) == markers(after)
                eligible = [i for i, (first, last) in enumerate(zip(FIRST, LAST)) if after.select(first) and after.select(last)]
                assert eligible == EXPECTED.get(case, []), ('Unexpected eligible pairs', case, eligible)
                pairs = [PAIRS[i] for i in eligible]
                for fmt in ['html', 'pdf', 'docx']:
                    x, y = [json.loads(n.with_suffix('.'+fmt+'.fixture.json').read_text()) for n in [old, new]]
                    for key in ['recipe_sha256', 'events_sha256', 'km_sha256']: assert x[key] == y[key]
                    assert x['package_sha256'] == sha(prior/(language+'.zip'))
                    assert y['package_sha256'] == report['package_sha256'][language+'.zip']
                left, right = [Document(n.with_suffix('.docx')) for n in [old, new]]
                assert_styles(right); word_unchanged(left, right)
                with zipfile.ZipFile(old.with_suffix('.docx')) as x, zipfile.ZipFile(new.with_suffix('.docx')) as y:
                    for part in ['word/styles.xml', 'word/fontTable.xml', 'word/numbering.xml']: assert x.read(part) == y.read(part)
                row['pdf_delta'] = pdf_delta(old.with_suffix('.pdf'), new.with_suffix('.pdf'), before, after, pairs)
                row['prior_pages'] = len(pdf_raw_page_texts(old.with_suffix('.pdf')))
                assert row['pages'] <= row['prior_pages'], 'PDF page count increased'
                preview = a.build/'word-preview'/(stem+'.pdf'); old_preview = prior/'word-preview'/(stem+'.pdf')
                row['word_pages'] = inspect_preview(preview); row['prior_word_pages'] = inspect_preview(old_preview)
                assert row['word_pages'] == row['prior_word_pages'], 'Word page count changed'
                geometry = [body_geometry(subprocess.check_output(['pdftotext', '-bbox-layout', str(f), '-']), s)
                            for f, s in [(old_preview, before), (preview, after)]]
                assert geometry[0] == geometry[1], 'Word body geometry changed'
                row['unchanged_word_body_and_geometry'] = True
                row['preview_paragraphs_checked'] = verify_preview_paragraphs(right, preview, after)
                assert not row['errors'] and not row['reading_issues'], row
                for f in [new.with_suffix('.docx'), new.with_suffix('.docx.fixture.json'), preview]: row['artifact_sha256'][str(f.relative_to(a.build))] = sha(f)
                row['prior_root'] = str(prior)
                row['prior_artifact_sha256'] = {str(f.relative_to(prior)): sha(f) for f in [old.with_suffix('.'+fmt+extra) for fmt in ['html', 'pdf', 'docx'] for extra in ['', '.fixture.json']]+[old_preview]}
                row['passed'] = True; report['rows'].append(row)
                print(json.dumps({'case': case, 'language': language, 'pages': row['pages'], 'word_pages': row['word_pages'], 'panels': len(pairs)}), flush=True)
        report['selected_checks_passed'] = True
    except Exception as error:
        report['failure'] = repr(error); raise
    finally: target.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')


if __name__ == '__main__': main()
