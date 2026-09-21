"""Native 0.3.44 integration: exact prototype parity, not global acceptance."""
import argparse
from collections import Counter
from datetime import datetime
import json
from pathlib import Path
import sys
import zipfile
from bs4 import BeautifulSoup
from docx import Document
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from lxml import etree
from artifact_utils import sha
from check_budget_outputs import body
from check_header_controls import raster_digest
from check_word_short_budget_outputs import paragraph_texts, verify_preview_paragraphs
from prepare_submission_preview_native import CASES, ARCHIVES, archive_for
from prepare_runtime_variant import require_tables_only_sources
from rehearse_profile_pagination import geometry

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'experiments/submission-notices'), str(ROOT / 'experiments/dataset-labels'),
               str(ROOT / 'experiments/mixed-budget-header')]
from notice_native import check_visible
from notice_probe import compact, owned_gaps
from label_probe import compare as compare_submission, replies_from
from compact import compact_source


def compare_docx(before, after):
    """Every component is identical except validated creation/modification times."""
    with zipfile.ZipFile(before) as left, zipfile.ZipFile(after) as right:
        assert len(left.namelist()) == len(right.namelist())
        assert set(left.namelist()) == set(right.namelist())
        for name in left.namelist():
            if name != 'docProps/core.xml':
                assert left.read(name) == right.read(name), ('DOCX component drift', name)
        core = [etree.fromstring(p.read('docProps/core.xml')) for p in [left, right]]
        fields = ['{http://purl.org/dc/terms/}created', '{http://purl.org/dc/terms/}modified']
        for tree in core:
            for field in fields:
                nodes = tree.findall(field); assert len(nodes) == 1
                value = datetime.fromisoformat(nodes[0].text.replace('Z', '+00:00'))
                assert value.tzinfo is not None
                nodes[0].text = 'VALIDATED-TIMESTAMP'
        assert etree.tostring(core[0]) == etree.tostring(core[1]), 'Other core metadata changed'
    return True


def word_html_inventory(document, soup):
    """Include the cover/overview and exact repeated table headers, not just Q1–15."""
    source = soup.body
    assert source is not None
    question_nodes = body(document)
    prefix = list(document.element.body)[:-len(question_nodes)]
    prefix_texts = [Paragraph(p, document).text for node in prefix for p in node.iter(qn('w:p'))]
    text = compact(''.join(prefix_texts + paragraph_texts(document, soup)))
    source_text = compact(source.get_text()); counts = Counter(text)
    for header in {compact(t.get_text()) for t in source.select('.resource-table thead')}:
        assert all(header not in compact(n.get_text()) for n in source.select('.answer-detail'))
        tables = [t for t in document.tables if compact(''.join(c.text for c in t.rows[0].cells)) == header]
        assert len(tables) == text.count(header)
        extra = len(tables) - source_text.count(header); assert extra >= 0
        counts.subtract({c: n * extra for c, n in Counter(header).items()})
    assert counts == Counter(source_text), 'Word lost/changed text, punctuation or visible fields'
    paragraphs = Counter(compact(p.get_text()) for p in source.select('p') if compact(p.get_text()))
    assert all(text.count(value) >= count for value, count in paragraphs.items())
    return sum(paragraphs.values())


def native_pair(run, fixtures, case, language, profile, hashes, compacted=False):
    from output_profile_contract import expected as partial_projection
    archive, seal = archive_for(case)
    stem = '-'.join([case, profile, language])
    old = archive / 'after/renders' / stem
    new = run / 'renders' / stem
    locale = 'en' if language == 'english' else 'zh-Hant'
    recipe = fixtures / locale / (case + '.json')
    events = fixtures / locale / (case + '.events.json')
    for fmt in ['html', 'pdf', 'docx']:
        receipts = [json.loads(p.with_suffix('.' + fmt + '.fixture.json').read_text()) for p in [old, new]]
        for key in ['recipe_sha256', 'events_sha256', 'km_sha256', 'output_profile', 'format_uuid', 'runner_sha256']:
            assert receipts[0][key] == receipts[1][key], (stem, fmt, key)
        previous_manifest = json.loads((archive / 'provenance/after-manifest.json').read_text())
        assert receipts[0]['package_sha256'] == previous_manifest['sha256'][language + '.zip']
        assert receipts[1]['package_sha256'] == hashes[language + '.zip']
        assert receipts[1]['recipe_sha256'] == sha(recipe) and receipts[1]['events_sha256'] == sha(events)
        assert receipts[1]['output_profile'] == profile
        if not compacted:
            model = recipe.parent / json.loads(recipe.read_text())['knowledge_model_package_id']
            assert sha(model) == receipts[1]['km_sha256']
    original_compact = json.loads(old.with_suffix('.html.compact.json').read_text())
    if compacted:
        receipt = json.loads(new.with_suffix('.html.compact.json').read_text())
        assert sha(new.with_suffix('.html')) == receipt['compact_html_sha256']
        assert receipt['original_html_sha256'] == original_compact['original_html_sha256']
        current_html = new.with_suffix('.html').read_bytes()
        assert receipt['fonts'] == original_compact['fonts']
    else:
        assert sha(new.with_suffix('.html')) == original_compact['original_html_sha256'], (stem, 'Native HTML byte drift')
        current_html, fonts = compact_source(new.with_suffix('.html').read_bytes())
        assert fonts == original_compact['fonts']
    assert current_html == old.with_suffix('.html').read_bytes()
    soup = BeautifulSoup(current_html, 'html.parser')
    labels = 0
    if profile == 'submission':
        original_review = archive / 'before/renders' / (case + '-' + language + '.html')
        review = BeautifulSoup(original_review.read_text(), 'html.parser')
        labels = compare_submission(partial_projection(review, language), soup, language, replies_from(events))
        assert not owned_gaps(soup)
    assert len(soup.select('.question')) == 15 and len(soup.select('.dmp-section')) == 6
    compare_docx(old.with_suffix('.docx'), new.with_suffix('.docx'))
    document = Document(new.with_suffix('.docx'))
    word_paragraphs = word_html_inventory(document, soup)
    output = {}
    for kind, before, after in [
        ('native_pdf', old.with_suffix('.pdf'), new.with_suffix('.pdf')),
        ('word_preview', archive / 'after/word-preview' / (stem + '.pdf'), run / 'word-preview' / (stem + '.pdf')),
    ]:
        assert geometry(before) == geometry(after), (stem, kind, 'Text or coordinates changed')
        assert raster_digest(before) == raster_digest(after), (stem, kind, 'Page pixels changed')
        visible = check_visible(after, soup, word=kind == 'word_preview')
        assert not visible['bounds_issues'], (stem, kind, 'Text outside page')
        output[kind] = dict(**visible, prototype_geometry_identical=True, prototype_pixels_identical=True,
                            prototype_sha256=sha(before), sha256=sha(after))
    preview_paragraphs = verify_preview_paragraphs(document, run / 'word-preview' / (stem + '.pdf'), soup)
    return dict(stem=stem, case=case, language=language, profile=profile,
        prototype_archive=str(archive.relative_to(ROOT)), prototype_seal_sha256=seal,
        html_bytes_identical=True, docx_components_identical=True, labels_checked=labels,
        word_html_paragraphs_checked=word_paragraphs, word_preview_paragraphs_checked=preview_paragraphs,
        remaining_owned_notices=len(owned_gaps(soup)), rendered=output,
        artifacts={fmt: sha(new.with_suffix('.' + fmt)) for fmt in ['html', 'pdf', 'docx']})


def run_checks(run, fixtures, english, compacted=False):
    sys.path[:0] = [str(english / 'scripts'), str(english / 'tests')]
    for name, seal in ARCHIVES.values():
        archive = ROOT / 'reviews' / name
        assert sha(archive / 'checksums.json') == seal
        for filename, digest in json.loads((archive / 'checksums.json').read_text()).items():
            assert sha(archive / filename) == digest
    manifest = json.loads((run / 'manifest.json').read_text())
    assert manifest['status'] == 'runtime-experiment'
    assert manifest['source']['version'] == manifest['translation']['version'] == '0.3.44'
    assert manifest['runtime_variant']['name'] == 'python-markdown-tables'
    require_tables_only_sources(manifest['runtime_variant']['reviewed_source_sha256'])
    hashes = manifest['identical_package_sha256']
    assert set(hashes) == {'english.zip', 'chinese.zip'}
    for name, digest in hashes.items():
        assert digest == manifest['sha256'][name]
        if not compacted: assert sha(run / name) == digest
    renders = json.loads((run / 'missing-info-render-report.json').read_text())
    expected = {(case, profile, language, fmt) for case in CASES for profile in ['review', 'submission']
                for language in ['english', 'chinese'] for fmt in ['html', 'pdf', 'docx']}
    actual = {(r['fixture_case'], r['profile'], r['language'], r['format']) for r in renders['renders'] if r['rendered']}
    assert renders['all_renders_succeeded'] and actual == expected and len(renders['renders']) == 48
    assert renders['package_sha256'] == hashes
    previews = {}
    for filename in run.glob('word-preview-*.json'):
        report = json.loads(filename.read_text()); assert report['completed']
        for row in report['rows']:
            assert row['name'] not in previews
            assert sha(run / 'renders' / (row['name'] + '.docx')) == row['docx_sha256']
            assert sha(run / 'word-preview' / (row['name'] + '.pdf')) == row['preview_sha256']
            previews[row['name']] = row
    assert set(previews) == {'-'.join([c, p, l]) for c, p, l, f in expected}
    rows = []
    for case in CASES:
        for profile in ['review', 'submission']:
            for language in ['english', 'chinese']:
                row = native_pair(run, fixtures, case, language, profile, hashes, compacted)
                rows.append(row)
                print(json.dumps(dict(stem=row['stem'], pages={k: v['pages'] for k, v in row['rendered'].items()})), flush=True)
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['build', 'fixtures', 'english', 'output']: p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args(); assert not a.output.exists()
    result = dict(passed=False, source_version='0.3.44', source_integrated=True, native_integrated_render_checked=True,
        global_switch_complete=False, release_acceptance=False, microsoft_word_acceptance=False,
        checker_sha256=sha(Path(__file__)), shared_visible_checker_sha256=sha(ROOT / 'experiments/submission-notices/notice_native.py'))
    try:
        result['rows'] = run_checks(a.build.resolve(), a.fixtures.resolve(), a.english.resolve())
        result['passed'] = True
    except Exception as error:
        result['failure'] = repr(error); raise
    finally: a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__': main()
