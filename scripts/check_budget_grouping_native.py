"""Native integrated 0.3.43 parity with the frozen, locally rendered prototype."""
import argparse
import json
from pathlib import Path
import sys
import zipfile
from docx import Document
from artifact_utils import sha
from check_budget_grouping_integration import ARCHIVE, SEAL
from check_header_controls import raster_digest
from check_large_resource_groups import compare_word
from rehearse_profile_pagination import geometry
from rehearse_profile_pdf import snapshot
from mixed_row_content import content
from word_budget_geometry import inspect as word_content

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'experiments/mixed-budget-header'))
from compact import compact_source


def pair(after, stem, hashes, compacted=False):
    before = ARCHIVE / 'after'
    paths = [root / 'renders' / stem for root in [before, after]]
    frozen = json.loads((ARCHIVE / 'provenance/package-projection.json').read_text())
    language = stem.rsplit('-', 1)[-1]
    for fmt in ['html', 'pdf', 'docx']:
        receipts = [json.loads(p.with_suffix('.' + fmt + '.fixture.json').read_text()) for p in paths]
        for key in ['recipe_sha256', 'events_sha256', 'km_sha256', 'output_profile', 'format_uuid']:
            assert receipts[0][key] == receipts[1][key], (stem, fmt, key)
        assert receipts[0]['package_sha256'] == frozen[language]['zip_sha256'][1]
        assert receipts[1]['package_sha256'] == hashes[language + '.zip']
    old = paths[0].with_suffix('.html').read_bytes()
    new = paths[1].with_suffix('.html').read_bytes()
    if not compacted: new = compact_source(new)[0]
    assert old == new, 'Native HTML drift'
    source = new.decode()
    pdfs = [p.with_suffix('.pdf') for p in paths]
    previews = [root / 'word-preview' / (stem + '.pdf') for root in [before, after]]
    pages = {}
    for kind, files in [('pdf', pdfs), ('word', previews)]:
        coordinates = [geometry(p) for p in files]
        assert coordinates[0] == coordinates[1], (stem, kind, 'geometry')
        assert raster_digest(files[0]) == raster_digest(files[1]), (stem, kind, 'pixels')
        pages[kind] = len(coordinates[1])
    parsed = content(snapshot(pdfs[1])[0], source, expanded=True)
    assert all(len(r['pages']) == 1 for r in parsed['rows'] if not r['long'])
    assert not parsed['long']['missing_identity_header_pages']
    assert not parsed['long']['split_purpose_paragraphs'] and parsed['long']['tail_together']
    compare_word(*[Document(p.with_suffix('.docx')) for p in paths], changed=False)
    with zipfile.ZipFile(paths[0].with_suffix('.docx')) as left, zipfile.ZipFile(paths[1].with_suffix('.docx')) as right:
        assert set(left.namelist()) == set(right.namelist())
        for name in left.namelist():
            # Timestamp-only core metadata is not an authored document component.
            if name != 'docProps/core.xml': assert left.read(name) == right.read(name), name
        from lxml import etree
        core = [etree.fromstring(p.read('docProps/core.xml')) for p in [left, right]]
        for tree in core:
            for node in tree:
                if node.tag in ['{http://purl.org/dc/terms/}created', '{http://purl.org/dc/terms/}modified']:
                    from datetime import datetime
                    datetime.fromisoformat(node.text.replace('Z', '+00:00'))
                    node.text = 'TIMESTAMP'
        assert etree.tostring(core[0]) == etree.tostring(core[1])
    word = word_content(paths[1].with_suffix('.docx'), previews[1], source)
    return dict(stem=stem, pages=pages, html_identical=True, document_components_identical=True,
                geometry_identical=True, pixels_identical=True,
                pdf_rows={k: v for k, v in parsed.items() if k != 'canonical'}, word_cells=word,
                artifacts={fmt: sha(paths[1].with_suffix('.' + fmt)) for fmt in ['html', 'pdf', 'docx']},
                word_preview_sha256=sha(previews[1]))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); assert not a.output.exists()
    assert sha(ARCHIVE / 'checksums.json') == SEAL
    for name, digest in json.loads((ARCHIVE / 'checksums.json').read_text()).items():
        assert sha(ARCHIVE / name) == digest, name
    manifest = json.loads((a.build / 'manifest.json').read_text())
    assert manifest['status'] == 'runtime-experiment'
    assert manifest['source']['version'] == manifest['translation']['version'] == '0.3.43'
    hashes = {name: sha(a.build / name) for name in ['english.zip', 'chinese.zip']}
    assert hashes == manifest['identical_package_sha256']
    for name in hashes: assert hashes[name] == manifest['sha256'][name]
    result = dict(selected_checks_passed=False, release_acceptance=False, microsoft_word_acceptance=False,
                  native_export=True, frozen_seal=SEAL, checker_sha256=sha(Path(__file__)), package_sha256=hashes, rows=[])
    try:
        for case in ['mixed-bound-32-first', 'mixed-bound-33-last']:
            for profile in ['review', 'submission']:
                for language in ['english', 'chinese']:
                    row = pair(a.build, '-'.join([case, profile, language]), hashes)
                    result['rows'].append(row)
                    print(json.dumps(dict(stem=row['stem'], pages=row['pages'])), flush=True)
        result['selected_checks_passed'] = len(result['rows']) == 8
    except Exception as error:
        result['failure'] = repr(error); raise
    finally: a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__': main()
