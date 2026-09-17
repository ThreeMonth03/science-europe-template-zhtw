"""Native bilingual 0.3.36 PDF grouping; exact content and unchanged Word controls."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import zipfile
from bs4 import BeautifulSoup
from docx import Document
from artifact_utils import sha
from check_archive_gap_outputs import body_geometry, prompt_geometry, word_unchanged
from check_budget_spacing_outputs import pdf_raw_page_texts, line_box_overlaps
from check_storage_context_outputs import check_pdf, locations
from check_q5_word_join_outputs import text_and_geometry
from check_word_rhythm_outputs import assert_styles, compare_questions, inspect_preview
from check_word_short_budget_outputs import verify_preview_paragraphs
from check_pdf_budget_reading_outputs import external_pdf_links
from reduce_word_layout_case import prefix_geometry

CASES = ['metadata-partial', 'metadata-complete', 'metadata-private-text', 'empty', 'negative']
FACTS = ['metadata-access-instructions', 'metadata-harvestable']


def pair_geometry(before, after, soup):
    texts = [soup.select_one('#q-docs-metadata [data-fact-id="' + fact + '"]').get_text() for fact in FACTS]
    pairs = [[prompt_geometry(bbox, text) for text in texts] for bbox in (before, after)]
    left, right = pairs
    assert right[0]['page'] == right[1]['page'], 'Two missing prompts split'
    assert [p['lines'] for p in left] == [p['lines'] for p in right], 'Prompt font/wrapping changed'
    assert left[0]['page'] == left[1]['page'], 'Baseline is not the reviewed adjacent pair'
    old_span = left[1]['bottom'] - left[0]['top']
    new_span = right[1]['bottom'] - right[0]['top']
    assert 0 < new_span < old_span, 'Missing-prompt spacing did not improve'
    return dict(before=left, after=right, before_span_pt=old_span, after_span_pt=new_span)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('build', 'prior', 'english'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    sys.path[:0] = [str(args.english.resolve() / name) for name in ('scripts', 'tests')]
    from metadata_gap_panel_contract import SELECTOR
    import check_missing_info_outputs as missing
    missing.HERE = args.english.resolve()
    report = dict(selected_checks_passed=False, release_acceptance=False, rows=[], checker_sha256=sha(Path(__file__)),
        package_sha256={n: sha(args.build / n) for n in ('english.zip', 'chinese.zip')},
        prior_package_sha256={n: sha(args.prior / n) for n in ('english.zip', 'chinese.zip')},
        limits=['Five synthetic cases per language, not all questionnaire branches',
                'PDF visual grouping only; prose, bindings and editable Word unchanged',
                'LibreOffice previews, not Microsoft Word execution', 'Local tables-only worker, no production deployment'])
    target = args.build / 'metadata-gap-panel-report.json'
    assert not target.exists()
    try:
        for case in CASES:
            for language in ('english', 'chinese'):
                stem = case + '-' + language
                old, new = [root / 'renders' / stem for root in (args.prior, args.build)]
                before = BeautifulSoup(old.with_suffix('.html').read_text(), 'html.parser')
                row, after = missing.inspect(args.build, case, language)
                compare_questions(before, after)
                selected = bool(after.select(SELECTOR))
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
                word_unchanged(left, right)
                with zipfile.ZipFile(old.with_suffix('.docx')) as x, zipfile.ZipFile(new.with_suffix('.docx')) as y:
                    for part in ('word/styles.xml', 'word/fontTable.xml', 'word/numbering.xml'):
                        assert x.read(part) == y.read(part), part
                pdfs = [path.with_suffix('.pdf') for path in (old, new)]
                check_pdf(*pdfs, before, after, selected)
                assert external_pdf_links(pdfs[0]) == external_pdf_links(pdfs[1])
                bboxes = [subprocess.check_output(['pdftotext', '-bbox-layout', str(path), '-']) for path in pdfs]
                assert line_box_overlaps(bboxes[0]) == line_box_overlaps(bboxes[1]), 'New PDF line-box overlap'
                row['prior_pages'] = len(pdf_raw_page_texts(pdfs[0]))
                assert row['pages'] <= row['prior_pages'], 'Native PDF pages increased'
                if selected:
                    row['pair_geometry'] = pair_geometry(*bboxes, after)
                    heading = before.select_one('#q-docs-metadata h3').get_text()
                    assert prefix_geometry(pdfs[0], heading) == prefix_geometry(pdfs[1], heading), 'Pre-Q3 body moved'
                previews = [root / 'word-preview' / (stem + '.pdf') for root in (args.prior, args.build)]
                row['prior_word_pages'], row['word_pages'] = [inspect_preview(path) for path in previews]
                assert row['prior_word_pages'] == row['word_pages']
                row['preview_paragraphs_checked'] = verify_preview_paragraphs(right, previews[1], after)
                snapshots = [text_and_geometry(path, soup) for path, soup in zip(previews, (before, after))]
                assert snapshots[0][0] == snapshots[1][0], 'Word preview text changed'
                assert body_geometry(snapshots[0][1], before) == body_geometry(snapshots[1][1], after), 'Word preview geometry changed'
                if after.select_one('#q-store-backup > .q5-short-context'):
                    row['q5_word_locations'] = locations(previews[1], after)
                    assert len(set(row['q5_word_locations'])) == 1, 'Reviewed Q5 Word fix regressed'
                for key, root, base, preview in [('before_sha256', args.prior, old, previews[0]), ('after_sha256', args.build, new, previews[1])]:
                    row[key] = {str(path.relative_to(root)): sha(path) for path in
                        [base.with_suffix('.' + fmt + extra) for fmt in ('html', 'pdf', 'docx') for extra in ('', '.fixture.json')] + [preview]}
                row.update(selected=selected, unchanged_word=True, passed=True)
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
