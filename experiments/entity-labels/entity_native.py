"""Native same-profile comparisons, exact owned-name delta and visible content."""
import argparse
import json
from pathlib import Path
import sys
import zipfile
from bs4 import BeautifulSoup
from docx import Document

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'scripts'), str(Path(__file__).parent)]
from artifact_utils import sha
from entity_probe import compare, replies_from
from entity_recipe import patch, baseline
from check_submission_preview_native import compare_docx, word_html_inventory
from check_header_controls import raster_digest
from rehearse_profile_pagination import geometry
from notice_native import check_visible
from check_word_short_budget_outputs import verify_preview_paragraphs
from prepare_runtime_variant import require_tables_only_sources


def run(before, after, fixtures, english, compacted=False):
    sys.path[:0] = [str(english / 'scripts'), str(english / 'tests')]
    manifests = [json.loads((p / 'manifest.json').read_text()) for p in [before, after]]
    for root, manifest in zip([before, after], manifests):
        assert manifest['status'] == 'runtime-experiment'
        require_tables_only_sources(manifest['runtime_variant']['reviewed_source_sha256'])
        report = json.loads((root / 'missing-info-render-report.json').read_text())
        assert report['all_renders_succeeded'] and len(report['renders']) == 12
        assert len({(r['case'], r['language'], r['format']) for r in report['renders'] if r['rendered']}) == 12
        preview = json.loads((root / 'word-preview-entity-labels-review-entity-labels-submission.json').read_text())
        assert preview['completed'] and len(preview['rows']) == 4
        for row in preview['rows']:
            assert sha(root / 'renders' / (row['name'] + '.docx')) == row['docx_sha256']
            assert sha(root / 'word-preview' / (row['name'] + '.pdf')) == row['preview_sha256']
        for language in ['english', 'chinese']:
            if compacted:
                actual = json.loads((root / (language + '.json')).read_text())
            else:
                with zipfile.ZipFile(root / (language + '.zip')) as package:
                    actual = json.loads(package.read('template/template.json'))
                assert sha(root / (language + '.zip')) == manifest['sha256'][language + '.zip']
            assert actual == (baseline(language) if root == before else patch(baseline(language), language)[0])
        assert report['package_sha256'] == {lang + '.zip': manifest['sha256'][lang + '.zip'] for lang in ['english', 'chinese']}
    rows = []
    for language, locale in [('english', 'en'), ('chinese', 'zh-Hant')]:
        recipe = fixtures / locale / 'entity-labels.json'; events = fixtures / locale / 'entity-labels.events.json'
        model = recipe.parent / json.loads(recipe.read_text())['knowledge_model_package_id']
        replies = replies_from(events)
        for profile in ['review', 'submission']:
            stem = 'entity-labels-' + profile + '-' + language
            bases = [p / 'renders' / stem for p in [before, after]]
            for fmt in ['html', 'pdf', 'docx']:
                receipts = [json.loads(p.with_suffix('.' + fmt + '.fixture.json').read_text()) for p in bases]
                for key in ['recipe_sha256', 'events_sha256', 'km_sha256', 'output_profile', 'format_uuid', 'runner_sha256']:
                    assert receipts[0][key] == receipts[1][key], (stem, fmt, key)
                for receipt, manifest in zip(receipts, manifests):
                    assert receipt['package_sha256'] == manifest['sha256'][language + '.zip']
                    assert receipt['recipe_sha256'] == sha(recipe) and receipt['events_sha256'] == sha(events)
                    if compacted:
                        model_hashes = json.loads((fixtures / 'knowledge-model-sha256.json').read_text())
                        assert receipt['km_sha256'] == model_hashes[model.name]
                    else:
                        assert receipt['km_sha256'] == sha(model)
                    assert receipt['output_profile'] == profile
            if compacted:
                font_receipts = [json.loads(p.with_suffix('.html.compact.json').read_text()) for p in bases]
                for p, receipt in zip(bases, font_receipts):
                    assert sha(p.with_suffix('.html')) == receipt['compact_html_sha256']
                assert font_receipts[0]['fonts'] == font_receipts[1]['fonts']
                if profile == 'review':
                    assert font_receipts[0]['original_html_sha256'] == font_receipts[1]['original_html_sha256']
            old, new = [BeautifulSoup(p.with_suffix('.html').read_text(), 'html.parser') for p in bases]
            changes = []
            if profile == 'review':
                assert bases[0].with_suffix('.html').read_bytes() == bases[1].with_suffix('.html').read_bytes()
                compare_docx(*[p.with_suffix('.docx') for p in bases])
            else:
                changes = compare(old, new, language, replies)
            assert len(new.select('.question')) == 15 and len(new.select('.dmp-section')) == 6
            docs = [Document(p.with_suffix('.docx')) for p in bases]
            assert [sorted(r.target_ref for r in d.part.rels.values() if r.is_external) for d in docs][0] == [
                sorted(r.target_ref for r in d.part.rels.values() if r.is_external) for d in docs][1]
            with zipfile.ZipFile(bases[0].with_suffix('.docx')) as left, zipfile.ZipFile(bases[1].with_suffix('.docx')) as right:
                for name in ['word/styles.xml', 'word/fontTable.xml', 'word/numbering.xml']:
                    assert left.read(name) == right.read(name)
            inventory = [word_html_inventory(d, s) for d, s in zip(docs, [old, new])]
            rendered = {}
            for kind, pdfs in [('native_pdf', [p.with_suffix('.pdf') for p in bases]),
                               ('word_preview', [p / 'word-preview' / (stem + '.pdf') for p in [before, after]])]:
                evidence = [check_visible(p, s, word=kind == 'word_preview') for p, s in zip(pdfs, [old, new])]
                assert not any(r['bounds_issues'] for r in evidence), (stem, kind, 'Text outside page')
                if profile == 'review':
                    assert geometry(pdfs[0]) == geometry(pdfs[1])
                    assert raster_digest(pdfs[0]) == raster_digest(pdfs[1])
                # This fixture is a short-name substitution, not an excuse to
                # silently accept extra pages or new collision screening hits.
                assert evidence[1]['pages'] <= evidence[0]['pages'], (stem, kind, 'More pages')
                assert len(evidence[1]['line_box_overlaps']) <= len(evidence[0]['line_box_overlaps'])
                rendered[kind] = dict(before=evidence[0], after=evidence[1],
                    before_sha256=sha(pdfs[0]), after_sha256=sha(pdfs[1]))
            visible_paragraphs = verify_preview_paragraphs(docs[1], after / 'word-preview' / (stem + '.pdf'), new)
            rows.append(dict(language=language, profile=profile, changes=changes, rendered=rendered,
                word_html_paragraph_inventory=inventory, preview_paragraphs=visible_paragraphs,
                artifacts={f: sha(bases[1].with_suffix('.' + f)) for f in ['html', 'pdf', 'docx']}))
            if compacted:
                rows[-1]['artifacts']['html'] = font_receipts[1]['original_html_sha256']
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['before', 'after', 'fixtures', 'english', 'output']: p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args(); assert not a.output.exists()
    proof = dict(passed=False, prototype_only=True, source_integrated=False, release_acceptance=False,
                 microsoft_word_acceptance=False, global_switch_complete=False,
                 checker_sha256=sha(Path(__file__)), recipe_sha256=sha(Path(__file__).with_name('entity_recipe.py')))
    try: proof['rows'] = run(a.before, a.after, a.fixtures, a.english.resolve()); proof['passed'] = True
    except Exception as error: proof['failure'] = repr(error); raise
    finally: a.output.write_text(json.dumps(proof, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(passed=True, pairs=len(proof['rows']))))


if __name__ == '__main__': main()
