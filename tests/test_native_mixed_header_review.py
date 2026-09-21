"""Recheck actual native artifacts; keep this prototype separate from a release."""
import hashlib
from importlib.resources import files
import json
from pathlib import Path
import sys
import unittest
import zipfile
from bs4 import BeautifulSoup
from docx import Document

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'reviews/2026-09-21-native-mixed-header'
FROZEN = ROOT / 'reviews/2026-09-18-short-resource-rows/reproduce/english'
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'experiments/mixed-budget-header'), str(FROZEN / 'scripts')]
previous = sys.dont_write_bytecode
try:
    sys.dont_write_bytecode = True
    from short_resource_rows_contract import project_hints
finally:
    sys.dont_write_bytecode = previous
from artifact_utils import sha
from compact import restore_source
from prototype import TAIL
from check_native_mixed_header import page_bounds, long_tail_together
from rehearse_mixed_budget import content
from rehearse_profile_pdf import snapshot, prefix_geometry
from rehearse_profile_pagination import geometry
from check_short_resources_outputs import fonts
from check_budget_outputs import body, xml
from check_word_short_budget_outputs import verify_preview_paragraphs


class NativeMixedHeaderReviewTests(unittest.TestCase):
    def report(self):
        return json.loads((ARCHIVE / 'provenance/native-comparison.json').read_text())

    def test_frozen_artifacts_and_explicit_prototype_boundary(self):
        expected = json.loads((ARCHIVE / 'checksums.json').read_text())
        self.assertEqual(expected, {str(p.relative_to(ARCHIVE)): sha(p) for p in ARCHIVE.rglob('*') if p.is_file() and p.name != 'checksums.json'})
        report = self.report()
        self.assertTrue(report['native_export'] and report['selected_checks_passed'] and report['prototype_only'])
        for key in ['release_acceptance', 'microsoft_word_acceptance', 'full_control_matrix_complete']:
            self.assertFalse(report[key])
        self.assertEqual(len(report['rows']), 8)
        self.assertEqual(report['checker_sha256'], sha(ARCHIVE / 'reproduce/check_native_mixed_header.py'))
        proof = json.loads((ARCHIVE / 'provenance/prototype.json').read_text())
        self.assertTrue(proof['prototype_only'])
        self.assertFalse(proof['source_repo_modified'] or proof['version_modified'])
        self.assertEqual(proof['recipe_sha256'], sha(ARCHIVE / 'reproduce/experiment/prototype.py'))
        life = json.loads((ARCHIVE / 'provenance/worker-lifecycle.json').read_text())
        self.assertTrue(life['stock_worker_restored'])
        self.assertEqual(life['deleted_owned_templates'], 4)
        self.assertTrue(all(r['status'] == 'exited' for r in life['after']))
        self.assertFalse(json.loads((ARCHIVE / 'provenance/quota-failed-render-report.json').read_text())['all_renders_succeeded'])

    def test_compact_native_inputs_restore_every_original_byte(self):
        font = files('dsw_document_template_tool').joinpath('resources/fonts/NotoSansTC-Variable.ttf').read_bytes()
        digest = hashlib.sha256(font).hexdigest()
        for phase in ['before', 'after']:
            for path in (ARCHIVE / phase / 'pdf-input').glob('*.html'):
                receipt = json.loads(path.with_suffix('.json').read_text())
                with self.subTest(path=path.name, phase=phase):
                    self.assertEqual(set(receipt['fonts']), {digest})
                    self.assertEqual(sha(path), receipt['compact_input_sha256'])
                    original = restore_source(path.read_bytes(), {digest: font})
                    self.assertEqual(hashlib.sha256(original).hexdigest(), receipt['full_input_sha256'])
                    copies = 4 if path.stem.endswith('review-chinese') else 1
                    self.assertEqual(receipt['fonts'][digest]['occurrences'], copies)
                    trace = json.loads((ARCHIVE / phase / 'trace' / (path.stem + '.json')).read_text())
                    self.assertEqual(trace['input_sha256'], receipt['full_input_sha256'])
                    self.assertEqual(trace['output_sha256'], sha(ARCHIVE / phase / 'native' / (path.stem + '.pdf')))
                    self.assertEqual(trace['observer_sha256'], sha(ARCHIVE / 'reproduce/experiment/capture.py'))
                    for key in ['input_modified', 'options_modified', 'layout_engine_modified']:
                        self.assertFalse(trace[key])

    def test_native_pdf_content_geometry_headers_tail_and_exact_input_delta(self):
        for row in self.report()['rows']:
            stem = row['stem']
            sources = [(ARCHIVE / phase / 'pdf-input' / (stem + '.html')).read_text() for phase in ['before', 'after']]
            projected = sources[1].replace(TAIL, '', 1).replace('<tbody style="break-inside: avoid">', '<tbody>', 1)
            self.assertEqual(project_hints(projected), sources[0])
            paths = [ARCHIVE / phase / 'native' / (stem + '.pdf') for phase in ['before', 'after']]
            values = [snapshot(path) for path in paths]
            parsed = [content(v[0], sources[0]) for v in values]
            with self.subTest(stem=stem):
                self.assertEqual(parsed[0]['canonical'], parsed[1]['canonical'])
                self.assertEqual([len(v[0]) for v in values], row['pages'])
                self.assertEqual(row['pages'][1] - row['pages'][0], 1 if stem == 'mixed-long-last-review-chinese' else 0)
                self.assertEqual(prefix_geometry(values[0][1]), prefix_geometry(values[1][1]))
                self.assertEqual(fonts(paths[0]), fonts(paths[1]))
                self.assertTrue(all(len(r['pages']) == 1 for r in parsed[1]['rows']))
                repeated = {r['page'] for r in parsed[1]['repeated_headers'] if r['kind'] == 'long-identity'}
                self.assertFalse(set(parsed[1]['long_pages'][1:]) - repeated)
                self.assertTrue(long_tail_together(values[1][0], sources[1]))
                self.assertEqual(page_bounds(values[0][1]), [])
                self.assertEqual(page_bounds(values[1][1]), [])

    def test_native_word_is_unchanged_and_all_paragraphs_are_visible(self):
        for row in self.report()['rows']:
            stem = row['stem']
            paths = [ARCHIVE / phase / 'native' / (stem + '.docx') for phase in ['before', 'after']]
            docs = [Document(path) for path in paths]
            self.assertEqual([xml(n) for n in body(docs[0])], [xml(n) for n in body(docs[1])])
            with zipfile.ZipFile(paths[0]) as a, zipfile.ZipFile(paths[1]) as b:
                for part in ['word/styles.xml', 'word/fontTable.xml', 'word/numbering.xml']:
                    self.assertEqual(a.read(part), b.read(part))
            previews = [ARCHIVE / phase / 'word-preview' / (stem + '.pdf') for phase in ['before', 'after']]
            self.assertEqual(geometry(previews[0]), geometry(previews[1]))
            html = (ARCHIVE / 'after/html-input' / (stem + '.html')).read_text()
            self.assertEqual(verify_preview_paragraphs(docs[1], previews[1], BeautifulSoup(html, 'html.parser')), row['word_paragraphs_checked'])
            pages = snapshot(previews[1])[0]
            whole = ''.join(pages)
            markers = [f'MIX-LONG-09-PARA-{i:02d}:' for i in range(1, 61)]
            self.assertTrue(all(whole.count(m) == 1 for m in markers))
            self.assertEqual([whole.index(m) for m in markers], sorted(whole.index(m) for m in markers))

    def test_observed_drop_and_captured_replay_explain_the_old_mismatch(self):
        stem = 'mixed-long-last-review-chinese'
        trace = json.loads((ARCHIVE / 'before/trace' / (stem + '.json')).read_text())
        drops = [r for r in trace['trace'] if r['line'] == 529]
        self.assertEqual([r['page'] for r in drops], [9])
        self.assertTrue(drops[0]['header_present'])
        self.assertFalse(drops[0]['new_table_children_present'])
        after = json.loads((ARCHIVE / 'after/trace' / (stem + '.json')).read_text())
        self.assertFalse([r for r in after['trace'] if r['line'] == 529])
        self.assertEqual(geometry(ARCHIVE / 'replay/captured.pdf'), geometry(ARCHIVE / 'replay/baseline.pdf'))
        self.assertEqual(fonts(ARCHIVE / 'replay/captured.pdf'), fonts(ARCHIVE / 'replay/baseline.pdf'))
        self.assertEqual(geometry(ARCHIVE / 'replay/body-short-tail.pdf'), geometry(ARCHIVE / 'after/native' / (stem + '.pdf')))
        difference = json.loads((ARCHIVE / 'provenance/input-difference.json').read_text())
        self.assertTrue(difference['cause_confirmed_for_baseline_mismatch'])
        self.assertFalse(difference['worker_font_lifetime_cause_claimed'])
        self.assertEqual(difference['localization_sha256'], sha(ARCHIVE / 'reproduce/tooling-localization.py'))


if __name__ == '__main__':
    unittest.main()
