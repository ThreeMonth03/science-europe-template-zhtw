"""Real native position/count controls for the unchanged local header prototype."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import zipfile
from bs4 import BeautifulSoup
from docx import Document
from jinja2 import ChoiceLoader, DictLoader, Environment, FileSystemLoader
from markupsafe import Markup
from artifact_utils import sha
from prepare_mixed_boundary_controls import CASES
from mixed_row_content import content, MARKERS
from mixed_budget_trial import TABLE, fragments
from check_header_controls import raster_digest, blank_space
from check_native_mixed_header import page_bounds
from check_budget_outputs import body, xml
from check_short_resources_outputs import fonts
from check_budget_spacing_outputs import line_box_overlaps
from check_word_short_budget_outputs import verify_preview_paragraphs
from check_word_boundary_content import inspect as inspect_word_boundary
from rehearse_profile_pdf import snapshot, prefix_geometry
from rehearse_profile_pagination import geometry

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'experiments/mixed-budget-header'))
from compact import compact_source
from prototype import BASELINE_SHA, TAIL, patch_budget


def scope(source, english):
    """Structural selection only; this fragment is NOT a captured PDF input."""
    matches = list(TABLE.finditer(source)); assert len(matches) == 1
    original = matches[0][0]; header, rows = fragments(original)
    patched = patch_budget((english / 'src/budget-reading.html.j2').read_text())
    env = Environment(loader=ChoiceLoader([DictLoader({'src/budget-reading.html.j2': patched}), FileSystemLoader(english)]),
                      extensions=['jinja2.ext.do'], autoescape=True)
    value = str(env.get_template('src/budget-reading.html.j2').module.render(Markup(original), header, rows))
    soup = BeautifulSoup(value, 'html.parser')
    return dict(resource_count=len(rows), selected_short_ids=[r['data-item-id'] for r in soup.select('.pdf-short-resource-row')],
                expanded_long_ids=[r['data-item-id'] for r in soup.select('.pdf-resource-reading')], native_pdf_entry_input=False)


def compare_pair(before, after, stem, case, english, package_hashes=None, compacted_html=False):
    language = stem.rsplit('-', 1)[-1]
    paths = [root / 'renders' / stem for root in [before, after]]
    for fmt in ['html', 'pdf', 'docx']:
        receipts = [json.loads(p.with_suffix('.' + fmt + '.fixture.json').read_text()) for p in paths]
        for key in ['recipe_sha256', 'events_sha256', 'km_sha256', 'output_profile', 'format_uuid']:
            assert receipts[0][key] == receipts[1][key]
        for index, (root, receipt) in enumerate(zip([before, after], receipts)):
            expected = package_hashes[index][language + '.zip'] if package_hashes else sha(root / (language + '.zip'))
            assert receipt['package_sha256'] == expected
    raw = [p.with_suffix('.html').read_bytes() for p in paths]
    html = [v.decode() if compacted_html else compact_source(v)[0].decode() for v in raw]
    assert html[1].count(TAIL) == 1 and html[1].replace(TAIL, '', 1) == html[0]
    soup = BeautifulSoup(html[0], 'html.parser'); assert len(soup.select('.question')) == 15
    selection = scope(html[0], english)
    expected_counts = dict(zip(CASES, [(9, 8, 1), (9, 8, 1), (7, 0, 1), (32, 31, 1), (33, 0, 0)]))
    assert (selection['resource_count'], len(selection['selected_short_ids']), len(selection['expanded_long_ids'])) == expected_counts[case]
    pdfs = [p.with_suffix('.pdf') for p in paths]; snapshots = [snapshot(p) for p in pdfs]
    parsed = [content(v[0], html[0], expanded=bool(selection['expanded_long_ids'])) for v in snapshots]
    assert parsed[0]['canonical'] == parsed[1]['canonical'], 'Original PDF cell content changed'
    assert Counter(c for c in ''.join(snapshots[0][0]) if c in MARKERS) == Counter(c for c in ''.join(snapshots[1][0]) if c in MARKERS)
    assert prefix_geometry(snapshots[0][1]) == prefix_geometry(snapshots[1][1])
    assert fonts(pdfs[0]) == fonts(pdfs[1])
    bounds = [page_bounds(v[1]) for v in snapshots]; assert bounds[0] == bounds[1], 'New clipping or margin intrusion'
    overlaps = [line_box_overlaps(v[1]) for v in snapshots]; assert overlaps[0] == overlaps[1]
    selected = set(selection['selected_short_ids'])
    assert all(len(r['pages']) == 1 for r in parsed[1]['rows'] if r['identity'] in selected), 'Selected short row split'
    if selection['expanded_long_ids']:
        assert not bounds[1]
        assert not parsed[1]['long']['missing_identity_header_pages'], 'Candidate continuation header missing'
        assert not parsed[1]['long']['split_purpose_paragraphs']
        assert parsed[1]['long']['tail_together'], 'Candidate long allocation isolated'
    exact_geometry = geometry(pdfs[0]) == geometry(pdfs[1])
    pixels_equal = raster_digest(pdfs[0]) == raster_digest(pdfs[1])
    if exact_geometry: assert pixels_equal
    if case == 'mixed-bound-33-last':
        assert exact_geometry and pixels_equal, 'Outside-limit fallback changed'
    documents = [Document(p.with_suffix('.docx')) for p in paths]
    assert [xml(n) for n in body(documents[0])] == [xml(n) for n in body(documents[1])]
    links = [sorted(r.target_ref for r in d.part.rels.values() if r.is_external) for d in documents]
    assert links[0] == links[1]
    with zipfile.ZipFile(paths[0].with_suffix('.docx')) as x, zipfile.ZipFile(paths[1].with_suffix('.docx')) as y:
        for part in ['word/styles.xml', 'word/fontTable.xml', 'word/numbering.xml']: assert x.read(part) == y.read(part)
    previews = [root / 'word-preview' / (stem + '.pdf') for root in [before, after]]
    assert geometry(previews[0]) == geometry(previews[1]) and fonts(previews[0]) == fonts(previews[1])
    assert raster_digest(previews[0]) == raster_digest(previews[1])
    word_boundary = inspect_word_boundary(documents[1], previews[1], soup) if case.startswith('mixed-bound-') else None
    paragraphs = None if word_boundary else verify_preview_paragraphs(documents[1], previews[1], soup)
    pages = [len(v[0]) for v in snapshots]
    return dict(stem=stem, case=case, scope=selection, pages=pages, page_count_nonincreasing=pages[1] <= pages[0],
        all_15_questions_retained=True, pdf_geometry_unchanged=exact_geometry, pdf_page_pixels_identical=pixels_equal,
        row_content=[{k: v for k, v in r.items() if k != 'canonical'} for r in parsed],
        bounds_findings=bounds, line_box_overlaps=overlaps,
        last_page_text_occupancy=[blank_space(v[1]) for v in snapshots],
        word_unchanged=True, word_page_pixels_identical=True, word_paragraphs_checked=paragraphs,
        word_boundary_content=word_boundary,
        pdf_sha256=[sha(p) for p in pdfs], word_preview_sha256=[sha(p) for p in previews])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['before', 'after', 'english', 'output']: p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args(); assert not a.output.exists()
    for name, digest in BASELINE_SHA.items(): assert sha(a.before / name) == digest
    report = dict(native_export=True, native_pdf_entry_captured=False, prototype_only=True,
        release_acceptance=False, microsoft_word_acceptance=False, full_control_matrix_complete=False,
        complete_word_content_acceptance=False,
        selected_checks_scope='Native PDF content, bounded pagination and exact Word regression; unresolved Word paragraph checks remain diagnostics',
        planned_position_controls_complete=False, selected_checks_passed=False, cases=CASES,
        checker_sha256=sha(Path(__file__)), content_oracle_sha256=sha(Path(__file__).with_name('mixed_row_content.py')), rows=[])
    try:
        for case in CASES:
            for profile in ['review', 'submission']:
                for language in ['english', 'chinese']:
                    stem = '-'.join([case, profile, language])
                    row = compare_pair(a.before, a.after, stem, case, a.english)
                    report['rows'].append(row)
                    print(json.dumps({k: row[k] for k in ['stem', 'pages', 'pdf_geometry_unchanged']}), flush=True)
        report['planned_position_controls_complete'] = report['selected_checks_passed'] = len(report['rows']) == 20
    except Exception as error:
        report['failure'] = repr(error); raise
    finally:
        a.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__': main()
