"""Native 0.3.34 -> 0.3.35: exact owned Word join, unchanged PDF and all other content."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import zipfile
from bs4 import BeautifulSoup
from docx import Document
from artifact_utils import sha
from check_budget_outputs import xml
from check_archive_gap_outputs import body_geometry
from check_storage_context_outputs import CASES, word_parts, locations, check_pdf
from check_word_rhythm_outputs import assert_styles, compare_questions, inspect_preview
from check_word_short_budget_outputs import verify_preview_paragraphs
from check_budget_spacing_outputs import pdf_raw_page_texts, line_box_overlaps
from diagnose_word_import_layout import clean_pages, compact
from reduce_word_layout_case import prefix_geometry


def check_word(before, after, selected):
    from q5_word_join_contract import check_word as check_join
    left, right = word_parts(before), word_parts(after)
    for i in (0, 2):
        assert list(map(xml, left[i])) == list(map(xml, right[i])), 'Word changed outside Q5'
    count = check_join(left[1], right[1], selected)
    assert xml(before.part.numbering_part.element) == xml(after.part.numbering_part.element)
    links = lambda d: sorted(r.target_ref for r in d.part.rels.values() if r.is_external)
    assert links(before) == links(after)
    return count


def text_and_geometry(pdf, soup):
    raw = subprocess.check_output(['pdftotext', '-raw', str(pdf), '-'], text=True)
    bbox = subprocess.check_output(['pdftotext', '-bbox-layout', str(pdf), '-'])
    pages = clean_pages(raw, bbox)
    heading = compact(soup.select_one('.question h3').get_text())
    assert sum(page.count(heading) for page in pages) == 1
    start = next(i for i, page in enumerate(pages) if heading in page)
    # Exclude only verified cover pages (package version changes there).
    return ''.join(pages[start:]), bbox


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('build', 'prior', 'english'): p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args(); sys.path[:0] = [str(a.english.resolve() / name) for name in ('scripts', 'tests')]
    import check_missing_info_outputs as missing
    missing.HERE = a.english.resolve()
    report = dict(selected_checks_passed=False, release_acceptance=False, rows=[], checker_sha256=sha(Path(__file__)),
                  package_sha256={name: sha(a.build / name) for name in ('english.zip', 'chinese.zip')},
                  prior_package_sha256={name: sha(a.prior / name) for name in ('english.zip', 'chinese.zip')},
                  limits=['Ten cases per language, not all questionnaire branches or full-DMP acceptance',
                          'LibreOffice previews, not Microsoft Word execution', 'Tables-only local worker remains an experimental runtime dependency'])
    target = a.build / 'q5-word-join-report.json'; assert not target.exists()
    try:
        for case in CASES:
            for language in ('english', 'chinese'):
                stem = case + '-' + language
                old, new = [root / 'renders' / stem for root in (a.prior, a.build)]
                before = BeautifulSoup(old.with_suffix('.html').read_text(), 'html.parser')
                row, after = missing.inspect(a.build, case, language)
                compare_questions(before, after)
                selected = bool(after.select_one('#q-store-backup > .q5-short-context'))
                assert selected == bool(before.select_one('#q-store-backup > .q5-short-context'))
                for fmt in ('html', 'pdf', 'docx'):
                    x, y = [json.loads(path.with_suffix('.' + fmt + '.fixture.json').read_text()) for path in (old, new)]
                    for key in ('recipe_sha256', 'events_sha256', 'km_sha256'): assert x[key] == y[key]
                    assert x['package_sha256'] == report['prior_package_sha256'][language + '.zip']
                    assert y['package_sha256'] == report['package_sha256'][language + '.zip']
                left, right = [Document(path.with_suffix('.docx')) for path in (old, new)]
                assert_styles(right); row['joined_pairs'] = check_word(left, right, selected)
                with zipfile.ZipFile(old.with_suffix('.docx')) as x, zipfile.ZipFile(new.with_suffix('.docx')) as y:
                    for part in ('word/styles.xml', 'word/fontTable.xml', 'word/numbering.xml'):
                        assert x.read(part) == y.read(part), part
                # PDF is a strict unchanged control even when Word joins.
                check_pdf(old.with_suffix('.pdf'), new.with_suffix('.pdf'), before, after, False)
                row['prior_pages'] = len(pdf_raw_page_texts(old.with_suffix('.pdf')))
                assert row['pages'] == row['prior_pages'], 'Native PDF pages changed'
                previews = [root / 'word-preview' / (stem + '.pdf') for root in (a.prior, a.build)]
                row['prior_word_pages'], row['word_pages'] = [inspect_preview(path) for path in previews]
                assert row['word_pages'] <= row['prior_word_pages'], 'Word pages increased'
                row['preview_paragraphs_checked'] = verify_preview_paragraphs(right, previews[1], after)
                snapshots = [text_and_geometry(path, soup) for path, soup in zip(previews, (before, after))]
                assert snapshots[0][0] == snapshots[1][0], 'Preview words, punctuation or order changed'
                if not selected:
                    assert body_geometry(snapshots[0][1], before) == body_geometry(snapshots[1][1], after), 'Fallback Word geometry changed'
                else:
                    section = before.select_one('#q-store-backup').find_previous('h2').get_text()
                    assert prefix_geometry(previews[0], section) == prefix_geometry(previews[1], section), 'Pre-Q5 Word body geometry changed'
                    row['pre_q5_word_geometry_unchanged'] = True
                    row['q5_locations'] = {kind: dict(before=locations(paths[0], before), after=locations(paths[1], after))
                                          for kind, paths in [('pdf', [old.with_suffix('.pdf'), new.with_suffix('.pdf')]), ('word', previews)]}
                    for kind, value in row['q5_locations'].items(): assert len(set(value['after'])) == 1, (kind, value)
                row['font_box_overlaps'] = [line_box_overlaps(s[1]) for s in snapshots]
                assert not row['errors'] and not row['reading_issues'], row
                for key, root, base, preview in [('before_sha256', a.prior, old, previews[0]), ('after_sha256', a.build, new, previews[1])]:
                    row[key] = {str(path.relative_to(root)): sha(path) for path in
                                [base.with_suffix('.' + fmt + extra) for fmt in ('html', 'pdf', 'docx') for extra in ('', '.fixture.json')] + [preview]}
                row.update(selected=selected, passed=True)
                report['rows'].append(row)
                print(json.dumps({k: row[k] for k in ('case', 'language', 'joined_pairs', 'pages', 'word_pages')}), flush=True)
        report['selected_checks_passed'] = True
    except Exception as error:
        report['failure'] = repr(error); raise
    finally:
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__': main()
