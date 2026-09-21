"""Native bilingual controls for the unreleased mixed-header package prototype.

Use real exported PDFs, not reconstructed HTML-to-PDF inputs. Each assertion is
bounded to these five public fixtures; no claim of arbitrary-project acceptance.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import subprocess
import zipfile
from bs4 import BeautifulSoup
from docx import Document
from lxml import etree as E
from artifact_utils import sha
from prepare_header_controls import CASES
from check_budget_outputs import body, xml
from check_short_resources_outputs import fonts
from check_short_resource_rows_outputs import row_pages
from check_budget_spacing_outputs import line_box_overlaps
from check_word_short_budget_outputs import verify_preview_paragraphs
from check_output_profiles import checklist
from check_native_mixed_header import page_bounds
from rehearse_profile_pdf import snapshot, prefix_geometry
from rehearse_profile_pagination import geometry

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'experiments/mixed-budget-header'))
from compact import compact_source
from prototype import TAIL, BASELINE_SHA

MARKERS = {'•', '◦', '\uf0b7', '\uf0a1'}
compact = lambda value: ''.join(value.split())


def raster_digest(pdf):
    """Pixel comparison within one installed Poppler, excluding PDF metadata.

    Do not compare these digests across Poppler/platform versions. Frozen tests
    recompute the equality relation, not a platform-specific golden image hash.
    """
    pixels = subprocess.check_output(['pdftoppm', '-r', '72', str(pdf)])
    assert pixels.startswith(b'P6\n')
    return hashlib.sha256(pixels).hexdigest()


def long_content(pages, soup):
    """Verify all 60 authored paragraphs and exact repeated context, without
    silently removing user prose or normalizing arbitrary table cell ordering.
    """
    rows = soup.select('#q-required-resources .resource-table tbody > tr')
    assert len(rows) in [1, 2]
    first = rows[0]; cells = first.find_all('td', recursive=False)
    title = compact(cells[0].find('p', recursive=False).get_text())
    identity = title + compact(cells[1].get_text() + cells[2].get_text())
    heading = compact(first.find_parent('table').thead.get_text())
    full_header = heading + identity
    assert full_header and not MARKERS.intersection(soup.get_text())
    assert all(full_header not in compact(n.get_text()) for n in soup.select('.answer-detail'))
    values = [''.join(c for c in page if c not in MARKERS) for page in pages]
    initial = [i for i, page in enumerate(values) if full_header in page]
    assert initial, 'Initial long resource identity missing'
    repeated = []
    for i in range(initial[0] + 1, len(values)):
        if values[i].startswith(full_header):
            values[i] = values[i][len(full_header):]
            repeated.append(i + 1)
    whole = ''.join(values)
    character_pages = [number for number, value in enumerate(values, 1) for _ in value]
    purposes = [compact(p.get_text()) for p in first.select('.answer-detail p') if 'BUDGET-PARA-' in p.get_text()]
    assert len(purposes) == 60
    locations = []
    for n, text in enumerate(purposes, 1):
        marker = f'BUDGET-PARA-{n:02d}:'
        assert text.startswith(marker) and whole.count(marker) == whole.count(text) == 1
        hits = [i for i, page in enumerate(pages, 1) if text in page]
        assert len(hits) == 1, ('Paragraph lost, changed, duplicated or split', marker, hits)
        locations.extend(hits)
    assert [whole.index(text) for text in purposes] == sorted(whole.index(text) for text in purposes)
    long_pages = sorted(set(locations))
    missing = [i for i in long_pages if full_header not in pages[i - 1]]
    allocation = compact(cells[0].find_all('p', recursive=False)[-1].get_text())
    assert whole.count(title) == 1
    start = whole.index(title)
    end = whole.index(compact(rows[1].td.p.get_text()), start) if len(rows) == 2 else len(whole)
    assert whole[start:end].count(allocation) == 1, 'Long-row allocation missing or ambiguous'
    position = whole.index(allocation, start, end)
    allocation_pages = sorted(set(character_pages[position:position + len(allocation)]))
    tail_page = [i for i, page in enumerate(pages, 1) if purposes[-1] in page][0]
    # Match only inside the first row's content, not the trailing short row.
    tail_together = allocation_pages == [tail_page]
    tail_rows = []
    if len(rows) == 2:
        tail = rows[1]
        name = compact(tail.td.p.get_text())
        hits = [i for i, page in enumerate(pages, 1) if name in page]
        assert len(hits) == 1 and '0TWD' in pages[hits[0] - 1]
        tail_rows = hits
    return {'canonical': whole, 'purpose_paragraphs': 60, 'long_pages': long_pages,
            'repeated_headers': repeated, 'missing_header_pages': missing,
            'tail_together': tail_together, 'tail_page': tail_page,
            'allocation_pages': allocation_pages, 'short_tail_pages': tail_rows}


def blank_space(bbox):
    """Actual text occupancy, not ink/table-border bounds or a layout score."""
    pages = E.fromstring(bbox).findall('.//{*}page'); page = pages[-1]
    body = []
    for line in page.findall('.//{*}line'):
        if compact(''.join(line.itertext())) == f'{len(pages)}/{len(pages)}' and float(line.get('yMin')) > float(page.get('height')) * .9:
            continue
        body.extend(line.findall('{*}word'))
    assert body
    bottom = max(float(w.get('yMax')) for w in body)
    return {'last_body_word_bottom_pt': round(bottom, 3),
            'space_to_bottom_content_margin_pt': round(float(page.get('height')) - 22 * 72 / 25.4 - bottom, 3)}


def compare_pair(before, after, stem, case, profile, language, package_hashes=None, compacted_html=False):
    paths = [root / 'renders' / stem for root in [before, after]]
    for fmt in ['html', 'pdf', 'docx']:
        receipts = [json.loads(p.with_suffix('.' + fmt + '.fixture.json').read_text()) for p in paths]
        for key in ['recipe_sha256', 'events_sha256', 'km_sha256', 'output_profile', 'format_uuid']:
            assert receipts[0][key] == receipts[1][key], (stem, fmt, key)
        for index, (root, receipt) in enumerate(zip([before, after], receipts)):
            expected = package_hashes[index][language + '.zip'] if package_hashes else sha(root / (language + '.zip'))
            assert receipt['package_sha256'] == expected
    raw_html = [p.with_suffix('.html').read_bytes() for p in paths]
    html = [value.decode() if compacted_html else compact_source(value)[0].decode() for value in raw_html]
    assert html[1].count(TAIL) == 1 and html[1].replace(TAIL, '', 1) == html[0], 'Unowned HTML change'
    soup = BeautifulSoup(html[1], 'html.parser')
    assert len(soup.select('.question')) == 15
    documents = [Document(p.with_suffix('.docx')) for p in paths]
    assert [xml(n) for n in body(documents[0])] == [xml(n) for n in body(documents[1])]
    links = [sorted(r.target_ref for r in d.part.rels.values() if r.is_external) for d in documents]
    assert links[0] == links[1]
    with zipfile.ZipFile(paths[0].with_suffix('.docx')) as x, zipfile.ZipFile(paths[1].with_suffix('.docx')) as y:
        for part in ['word/styles.xml', 'word/fontTable.xml', 'word/numbering.xml']:
            assert x.read(part) == y.read(part)
    pdfs = [p.with_suffix('.pdf') for p in paths]; snapshots = [snapshot(p) for p in pdfs]
    assert prefix_geometry(snapshots[0][1]) == prefix_geometry(snapshots[1][1]), 'Outside Q15 moved'
    assert fonts(pdfs[0]) == fonts(pdfs[1])
    bounds = [page_bounds(v[1]) for v in snapshots]; assert bounds == [[], []]
    overlaps = [line_box_overlaps(v[1]) for v in snapshots]; assert overlaps[0] == overlaps[1]
    assert Counter(c for c in ''.join(snapshots[0][0]) if c in MARKERS) == Counter(c for c in ''.join(snapshots[1][0]) if c in MARKERS)
    long = case in ['budget-single-long', 'budget-long-no-currency']
    details = {}
    exact_geometry = geometry(pdfs[0]) == geometry(pdfs[1])
    pdf_pixels_equal = raster_digest(pdfs[0]) == raster_digest(pdfs[1])
    if exact_geometry:
        assert pdf_pixels_equal, 'Same text boxes but different visible PDF page content'
    if long:
        content = [long_content(v[0], soup) for v in snapshots]
        assert content[0]['canonical'] == content[1]['canonical'], 'Native PDF content changed'
        assert not content[1]['missing_header_pages'] and content[1]['tail_together']
        details = {'long': [{k: v for k, v in row.items() if k != 'canonical'} for row in content]}
    else:
        assert exact_geometry and snapshots[0][0] == snapshots[1][0], 'Unaffected control layout changed'
        if case == 'budget-many':
            details['short_rows'] = row_pages(snapshots[1][0], soup)
            assert all(len(row['pages']) == 1 for row in details['short_rows'])
    previews = [root / 'word-preview' / (stem + '.pdf') for root in [before, after]]
    assert geometry(previews[0]) == geometry(previews[1])
    assert fonts(previews[0]) == fonts(previews[1])
    assert raster_digest(previews[0]) == raster_digest(previews[1]), 'Word page appearance changed'
    paragraphs = verify_preview_paragraphs(documents[1], previews[1], soup)
    if case == 'profile-partial':
        assert len(checklist(soup)) == (10 if profile == 'review' else 0)
        if profile == 'submission':
            authored = 'Information not provided: this is authored method text' if language == 'english' else '尚待補充：這是使用者填寫的方法說明'
            assert compact(authored) in ''.join(snapshots[1][0])
    return dict(stem=stem, case=case, language=language, profile=profile,
        pages=[len(v[0]) for v in snapshots], pdf_geometry_unchanged=exact_geometry,
        pdf_page_pixels_identical=pdf_pixels_equal, word_page_pixels_identical=True,
        word_geometry_unchanged=True, word_paragraphs_checked=paragraphs,
        all_15_questions_retained=True, remaining_system_gap_nodes=len(soup.select('.data-gap')),
        last_page_text_occupancy=[blank_space(v[1]) for v in snapshots],
        bounds_findings=bounds, line_box_overlaps=overlaps,
        pdf_sha256=[sha(p) for p in pdfs], word_preview_sha256=[sha(p) for p in previews], **details)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['before', 'after', 'output']: p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args(); assert not a.output.exists()
    for name, digest in BASELINE_SHA.items(): assert sha(a.before / name) == digest
    report = dict(native_export=True, native_pdf_entry_captured=False, prototype_only=True,
        release_acceptance=False, microsoft_word_acceptance=False, full_control_matrix_complete=False,
        selected_checks_passed=False, cases=CASES, checker_sha256=sha(Path(__file__)),
        raster_comparison_dpi=72,
        poppler=subprocess.run(['pdftoppm', '-v'], capture_output=True, text=True, check=True).stderr.splitlines()[0], rows=[])
    try:
        for case in CASES:
            for profile in ['review', 'submission']:
                for language in ['english', 'chinese']:
                    stem = '-'.join([case, profile, language])
                    row = compare_pair(a.before, a.after, stem, case, profile, language)
                    report['rows'].append(row)
                    print(json.dumps({k: row[k] for k in ['stem', 'pages', 'pdf_geometry_unchanged']}), flush=True)
        report['selected_checks_passed'] = len(report['rows']) == 20
    except Exception as error:
        report['failure'] = repr(error); raise
    finally:
        a.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__': main()
