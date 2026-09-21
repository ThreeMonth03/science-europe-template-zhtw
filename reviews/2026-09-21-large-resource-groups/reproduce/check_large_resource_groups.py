"""Native 32-row control and 33-row improvement against the frozen header trial."""
import argparse
import copy
import json
from pathlib import Path
import subprocess
import sys
import zipfile
from bs4 import BeautifulSoup
from docx import Document
from docx.oxml.ns import qn
from artifact_utils import sha
from check_budget_outputs import body, xml
from check_long_budget_outputs import paragraphs, empty_table_separator
from check_native_mixed_header import page_bounds
from check_header_controls import raster_digest, blank_space
from check_short_resources_outputs import fonts
from check_budget_spacing_outputs import line_box_overlaps
from rehearse_profile_pdf import snapshot, prefix_geometry
from rehearse_profile_pagination import geometry
from mixed_row_content import content
from word_budget_geometry import inspect as word_content

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'experiments/mixed-budget-header'))
from compact import compact_source


def compare_word(before, after, changed):
    left, right = body(before), body(after)
    if not changed:
        assert [xml(n) for n in left] == [xml(n) for n in right]
        return 0
    i = max(i for i, n in enumerate(left) if n.tag == qn('w:tbl'))
    assert len(right) == len(left) + 2
    assert [xml(n) for n in left[:i]] == [xml(n) for n in right[:i]]
    assert [xml(n) for n in left[i + 1:]] == [xml(n) for n in right[i + 3:]]
    old, short, long = left[i], right[i], right[i + 2]
    empty_table_separator(right[i + 1])
    rows = old.findall(qn('w:tr')); short_rows = short.findall(qn('w:tr')); long_rows = long.findall(qn('w:tr'))
    assert len(rows) == 34 and len(short_rows) == 33 and len(long_rows) == 65
    assert [xml(n) for n in rows[:-1]] == [xml(n) for n in short_rows]
    assert xml(rows[0]) == xml(long_rows[0])
    for table in [short, long]:
        assert xml(table.find(qn('w:tblGrid'))) == xml(old.find(qn('w:tblGrid')))
        properties = copy.deepcopy(table.find(qn('w:tblPr')))
        if table is long:
            style = properties.find(qn('w:tblStyle')); assert style.get(qn('w:val')) == 'PilotLongBudget'
            style.set(qn('w:val'), 'Table')
        assert xml(properties) == xml(old.find(qn('w:tblPr')))
    cells = rows[-1].findall(qn('w:tc')); identity = long_rows[1].findall(qn('w:tc'))
    assert len(cells) == len(identity) == 3
    assert paragraphs(cells[0])[:1] == paragraphs(identity[0])
    for c in [1, 2]: assert paragraphs(cells[c]) == paragraphs(identity[c])
    assert all(row.find(qn('w:trPr') + '/' + qn('w:tblHeader')) is not None for row in long_rows[:2])
    kept = []
    for row in long_rows[2:]:
        assert row.find(qn('w:trPr') + '/' + qn('w:tblHeader')) is None
        detail = row.findall(qn('w:tc')); assert len(detail) == 1
        assert detail[0].find(qn('w:tcPr') + '/' + qn('w:gridSpan')).get(qn('w:val')) == '3'
        kept.extend(paragraphs(detail[0]))
    assert kept == paragraphs(cells[0])[1:], 'Original purpose paragraph/run/list XML changed'
    return len(kept)


def pair(before, after, stem, compacted=False, package_hashes=None):
    paths = [p / 'renders' / stem for p in [before, after]]
    is33 = stem.startswith('mixed-bound-33-last-')
    if package_hashes is None:
        package_hashes = [json.loads((root / 'manifest.json').read_text())['sha256'] for root in [before, after]]
    for fmt in ['html', 'pdf', 'docx']:
        receipts = [json.loads(p.with_suffix('.' + fmt + '.fixture.json').read_text()) for p in paths]
        for key in ['recipe_sha256', 'events_sha256', 'km_sha256', 'output_profile', 'format_uuid']:
            assert receipts[0][key] == receipts[1][key]
        for receipt, hashes in zip(receipts, package_hashes):
            assert receipt['package_sha256'] == hashes[stem.rsplit('-', 1)[-1] + '.zip']
    html = [p.with_suffix('.html').read_bytes() for p in paths]
    if not compacted: html = [compact_source(v)[0] for v in html]
    assert html[0] == html[1], 'Native HTML answer output changed'
    source = html[0].decode(); assert len(BeautifulSoup(source, 'html.parser').select('.question')) == 15
    pdfs = [p.with_suffix('.pdf') for p in paths]
    snaps = [snapshot(p) for p in pdfs]
    parsed = [content(s[0], source, expanded=(i == 1 or not is33)) for i, s in enumerate(snaps)]
    assert parsed[0]['canonical'] == parsed[1]['canonical']
    assert prefix_geometry(snaps[0][1]) == prefix_geometry(snaps[1][1])
    assert fonts(pdfs[0]) == fonts(pdfs[1])
    assert not page_bounds(snaps[1][1])
    pdf_overlaps = [line_box_overlaps(s[1]) for s in snaps]
    assert pdf_overlaps[1] == pdf_overlaps[0], 'New PDF line-box overlap'
    assert all(len(r['pages']) == 1 for r in parsed[1]['rows'] if not r['long'])
    assert not parsed[1]['long']['missing_identity_header_pages']
    assert not parsed[1]['long']['split_purpose_paragraphs']
    assert parsed[1]['long']['tail_together']
    native_pages = [len(s[0]) for s in snaps]
    assert native_pages[1] <= native_pages[0]
    if not is33:
        assert geometry(pdfs[0]) == geometry(pdfs[1]) and raster_digest(pdfs[0]) == raster_digest(pdfs[1])
    docs = [Document(p.with_suffix('.docx')) for p in paths]
    kept = compare_word(*docs, changed=is33)
    assert [sorted(r.target_ref for r in d.part.rels.values() if r.is_external) for d in docs][0] == [sorted(r.target_ref for r in d.part.rels.values() if r.is_external) for d in docs][1]
    with zipfile.ZipFile(paths[0].with_suffix('.docx')) as a, zipfile.ZipFile(paths[1].with_suffix('.docx')) as b:
        for name in ['word/styles.xml', 'word/fontTable.xml', 'word/numbering.xml']: assert a.read(name) == b.read(name)
    previews = [p / 'word-preview' / (stem + '.pdf') for p in [before, after]]
    word = [word_content(p.with_suffix('.docx'), preview, source) for p, preview in zip(paths, previews)]
    assert word[0]['q15_prefix_geometry_sha256'] == word[1]['q15_prefix_geometry_sha256']
    assert fonts(previews[0]) == fonts(previews[1])
    word_pages = [len(geometry(p)) for p in previews]
    # Native Word page-count is in the geometry helper's page sequence.
    assert word_pages[1] <= word_pages[0]
    if not is33:
        assert geometry(previews[0]) == geometry(previews[1]) and raster_digest(previews[0]) == raster_digest(previews[1])
    long_row = next(r for r in parsed[1]['rows'] if r['long'])['index']
    actual_long = word[1]['rows'][long_row - 1]
    assert not actual_long['split_paragraphs'], 'Candidate Word long paragraph split'
    tail = actual_long['last_two_first_cell_paragraph_pages']
    assert len(tail) == 2 and tail[0] == tail[1] and len(tail[0]) == 1, 'Word allocation separated from final purpose'
    identity_pages = {r['page'] for r in word[1]['repeated_identity_headers'] if r['resource'] == long_row}
    assert set(actual_long['pages'][1:]) <= identity_pages
    return dict(stem=stem, native_pdf_pages=native_pages, word_pages=word_pages,
        pdf_rows=[{k: v for k, v in p.items() if k != 'canonical'} for p in parsed], word_cells=word,
        control_unchanged=not is33, word_purpose_xml_paragraphs_preserved=kept,
        pdf_line_box_overlaps=pdf_overlaps,
        last_page_text_occupancy=[blank_space(s[1]) for s in snaps],
        pdf_sha256=[sha(p) for p in pdfs], word_preview_sha256=[sha(p) for p in previews])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for n in ['before', 'after', 'output']: p.add_argument('--' + n, type=Path, required=True)
    a = p.parse_args(); assert not a.output.exists()
    result = dict(native_export=True, prototype_only=True, release_acceptance=False,
                  microsoft_word_acceptance=False, full_control_matrix_complete=False,
                  selected_checks_passed=False, checker_sha256=sha(Path(__file__)),
                  word_oracle_sha256=sha(ROOT / 'scripts/word_budget_geometry.py'), rows=[])
    try:
        for case in ['mixed-bound-32-first', 'mixed-bound-33-last']:
            for profile in ['review', 'submission']:
                for language in ['english', 'chinese']:
                    stem = '-'.join([case, profile, language])
                    row = pair(a.before, a.after, stem)
                    result['rows'].append(row)
                    print(json.dumps({k: row[k] for k in ['stem', 'native_pdf_pages', 'word_pages']}), flush=True)
        result['selected_checks_passed'] = len(result['rows']) == 8
    except Exception as error:
        result['failure'] = repr(error); raise
    finally: a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__': main()
