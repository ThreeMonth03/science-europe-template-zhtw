"""Native 0.3.37: one Q3 prose join; exact other content and fallback geometry."""
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
from check_archive_gap_outputs import body_geometry, prompt_geometry, word_unchanged
from check_budget_spacing_outputs import pdf_raw_page_texts, line_box_overlaps
from check_storage_context_outputs import check_pdf, locations
from check_q5_word_join_outputs import text_and_geometry
from check_word_rhythm_outputs import assert_styles, compare_questions, inspect_preview
from check_word_short_budget_outputs import verify_preview_paragraphs
from check_pdf_budget_reading_outputs import external_pdf_links
from check_narrative_outputs import compact

CASES = ['metadata-partial', 'metadata-complete', 'metadata-private-text', 'empty', 'negative']
FACTS = ['metadata-access-instructions', 'metadata-harvestable']


def prefix_before_q3(bbox, soup):
    # Locate complete headings, including wrapped English titles; do not assume
    # one line or blindly discard a fixed number of cover pages.
    start = prompt_geometry(bbox, soup.select_one('.question h3').get_text())
    end = prompt_geometry(bbox, soup.select_one('#q-docs-metadata h3').get_text())
    pages = etree.fromstring(bbox).findall('.//{*}page')
    result = []
    for number, page in enumerate(pages, 1):
        if not start['page'] <= number <= end['page']:
            continue
        lines = sorted(page.findall('.//{*}line'), key=lambda line: (float(line.get('yMin')), float(line.get('xMin'))))
        for line in lines:
            top = float(line.get('yMin'))
            if number == start['page'] and top < start['top']:
                continue
            if number == end['page'] and top > end['bottom']:
                continue
            value = compact(''.join(line.itertext()))
            if value == f'{number}/{len(pages)}' and top > float(page.get('height')) * .9:
                continue
            result.append(dict(page=number, text=value, **dict(line.attrib)))
    assert result
    return result


def expected_text(before, after, language, selected):
    from metadata_gap_prose_contract import OLD, joined
    if selected:
        first, last = [compact(t) for t in OLD[language]]
        assert before.count(first + last) == 1, 'Original complete prompt pair not unique'
        before = before.replace(first + last, compact(joined(language).get_text()))
    assert before == after, 'Unexpected PDF words, punctuation or order change'


def prose_geometry(before_bbox, after_bbox, before, after):
    old = [prompt_geometry(before_bbox, before.select_one('#q-docs-metadata [data-fact-id="' + fact + '"]').get_text()) for fact in FACTS]
    new = prompt_geometry(after_bbox, after.select_one('.metadata-publication-gap').get_text())
    assert old[0]['page'] == old[1]['page']
    old_span = old[1]['bottom'] - old[0]['top']
    new_span = new['bottom'] - new['top']
    assert 0 < new_span < old_span, 'Joined prose did not reduce the warning text span'
    return dict(before=old, after=new, before_span_pt=old_span, after_span_pt=new_span)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('build', 'prior', 'english'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    sys.path[:0] = [str(args.english.resolve() / name) for name in ('scripts', 'tests')]
    from metadata_gap_prose_contract import compare
    from probe_metadata_gap_prose import check_word
    from check_budget_outputs import body
    from xml.etree import ElementTree as E
    import check_missing_info_outputs as missing
    missing.HERE = args.english.resolve()
    report = dict(selected_checks_passed=False, release_acceptance=False, rows=[], checker_sha256=sha(Path(__file__)),
        package_sha256={n: sha(args.build / n) for n in ('english.zip', 'chinese.zip')},
        prior_package_sha256={n: sha(args.prior / n) for n in ('english.zip', 'chinese.zip')},
        limits=['Five synthetic cases per language, not all questionnaire branches',
                'Only the exact two absent Q3 follow-ups become one paragraph; fact markers retained',
                'LibreOffice previews, not Microsoft Word execution', 'Local tables-only worker, no production deployment'])
    target = args.build / 'metadata-gap-prose-report.json'
    assert not target.exists()
    try:
        for case in CASES:
            for language in ('english', 'chinese'):
                stem = case + '-' + language
                old, new = [root / 'renders' / stem for root in (args.prior, args.build)]
                before = BeautifulSoup(old.with_suffix('.html').read_text(), 'html.parser')
                row, after = missing.inspect(args.build, case, language)
                compare(*[BeautifulSoup(str(soup.select_one('#dmp-content')), 'html.parser') for soup in (before, after)], language)
                selected = bool(after.select('.metadata-publication-gap'))
                assert selected == (case == 'metadata-partial')
                assert not row['errors'] and not row['reading_issues'], row
                for fmt in ('html', 'pdf', 'docx'):
                    x, y = [json.loads(path.with_suffix('.' + fmt + '.fixture.json').read_text()) for path in (old, new)]
                    for key in ('recipe_sha256', 'events_sha256', 'km_sha256'):
                        assert x[key] == y[key], key
                    assert x['package_sha256'] == report['prior_package_sha256'][language + '.zip']
                    assert y['package_sha256'] == report['package_sha256'][language + '.zip']
                left, right = [Document(path.with_suffix('.docx')) for path in (old, new)]
                assert_styles(right)
                blocks = [[E.tostring(E.fromstring(etree.tostring(node)), encoding='unicode') for node in body(doc)] for doc in (left, right)]
                row['word_joins'] = check_word(*blocks, language)
                assert row['word_joins'] == int(selected)
                links = lambda doc: sorted(r.target_ref for r in doc.part.rels.values() if r.is_external)
                assert links(left) == links(right)
                with zipfile.ZipFile(old.with_suffix('.docx')) as x, zipfile.ZipFile(new.with_suffix('.docx')) as y:
                    for part in ('word/styles.xml', 'word/fontTable.xml', 'word/numbering.xml'):
                        assert x.read(part) == y.read(part), part
                pdfs = [path.with_suffix('.pdf') for path in (old, new)]
                native_snapshots = [text_and_geometry(path, soup) for path, soup in zip(pdfs, (before, after))]
                expected_text(native_snapshots[0][0], native_snapshots[1][0], language, selected)
                if not selected:
                    assert body_geometry(native_snapshots[0][1], before) == body_geometry(native_snapshots[1][1], after)
                assert external_pdf_links(pdfs[0]) == external_pdf_links(pdfs[1])
                bboxes = [subprocess.check_output(['pdftotext', '-bbox-layout', str(path), '-']) for path in pdfs]
                assert line_box_overlaps(bboxes[0]) == line_box_overlaps(bboxes[1]), 'New PDF line-box overlap'
                row['prior_pages'] = len(pdf_raw_page_texts(pdfs[0]))
                assert row['pages'] <= row['prior_pages'], 'Native PDF pages increased'
                if selected:
                    row['prose_geometry'] = prose_geometry(*bboxes, before, after)
                    assert prefix_before_q3(bboxes[0], before) == prefix_before_q3(bboxes[1], after), 'Pre-Q3 body or heading moved'
                previews = [root / 'word-preview' / (stem + '.pdf') for root in (args.prior, args.build)]
                row['prior_word_pages'], row['word_pages'] = [inspect_preview(path) for path in previews]
                assert row['word_pages'] <= row['prior_word_pages']
                row['preview_paragraphs_checked'] = verify_preview_paragraphs(right, previews[1], after)
                snapshots = [text_and_geometry(path, soup) for path, soup in zip(previews, (before, after))]
                expected_text(snapshots[0][0], snapshots[1][0], language, selected)
                if not selected:
                    assert body_geometry(snapshots[0][1], before) == body_geometry(snapshots[1][1], after), 'Fallback Word preview geometry changed'
                else:
                    row['word_prose_geometry'] = prose_geometry(snapshots[0][1], snapshots[1][1], before, after)
                if after.select_one('#q-store-backup > .q5-short-context'):
                    row['q5_word_locations'] = locations(previews[1], after)
                    assert len(set(row['q5_word_locations'])) == 1, 'Reviewed Q5 Word fix regressed'
                for key, root, base, preview in [('before_sha256', args.prior, old, previews[0]), ('after_sha256', args.build, new, previews[1])]:
                    row[key] = {str(path.relative_to(root)): sha(path) for path in
                        [base.with_suffix('.' + fmt + extra) for fmt in ('html', 'pdf', 'docx') for extra in ('', '.fixture.json')] + [preview]}
                row.update(selected=selected, unchanged_word=not selected, passed=True)
                report['rows'].append(row)
                print(json.dumps({key: row[key] for key in ('case', 'language', 'selected', 'pages', 'word_pages')}), flush=True)
        report['selected_checks_passed'] = True
    except Exception as error:
        report['failure'] = repr(error)
        raise
    finally:
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
