"""Recompute native bounded improvements and preserve the unsupported fallback."""
import hashlib
from importlib.resources import files
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'reviews/2026-09-21-mixed-boundary-controls'
ENGLISH = ROOT / 'reviews/2026-09-18-short-resource-rows/reproduce/english'
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'experiments/mixed-budget-header')]
from artifact_utils import sha
from check_mixed_boundary_controls import compare_pair
from compact import restore_source


class MixedBoundaryReviewTests(unittest.TestCase):
    def report(self):
        return json.loads((ARCHIVE / 'provenance/comparison.json').read_text())

    def test_sealed_evidence_and_limited_acceptance_are_explicit(self):
        expected = json.loads((ARCHIVE / 'checksums.json').read_text())
        self.assertEqual(expected, {str(p.relative_to(ARCHIVE)): sha(p) for p in ARCHIVE.rglob('*')
                                   if p.is_file() and p.name != 'checksums.json'})
        report = self.report()
        for key in ['native_export', 'prototype_only', 'selected_checks_passed', 'planned_position_controls_complete']:
            self.assertTrue(report[key])
        for key in ['release_acceptance', 'full_control_matrix_complete', 'microsoft_word_acceptance', 'native_pdf_entry_captured', 'complete_word_content_acceptance']:
            self.assertFalse(report[key])
        self.assertEqual(len(report['rows']), 20)
        self.assertEqual(report['checker_sha256'], sha(ARCHIVE / 'reproduce/check_mixed_boundary_controls.py'))
        self.assertEqual(report['content_oracle_sha256'], sha(ARCHIVE / 'reproduce/mixed_row_content.py'))
        life = json.loads((ARCHIVE / 'provenance/worker-lifecycle.json').read_text())
        self.assertTrue(life['stock_worker_restored'])
        self.assertEqual(life['deleted_owned_templates'], 4)
        self.assertFalse(life['capture_observer_attached'] or life['production_touched'])
        self.assertTrue(all(r['status'] == 'exited' for r in life['after']))

    def test_all_native_pdf_word_and_cell_results_are_recomputed(self):
        packages = [json.loads((ARCHIVE / 'provenance' / (phase + '-manifest.json')).read_text())['sha256'] for phase in ['before', 'after']]
        for row in self.report()['rows']:
            with self.subTest(stem=row['stem']):
                actual = compare_pair(ARCHIVE / 'before', ARCHIVE / 'after', row['stem'], row['case'], ENGLISH,
                    package_hashes=packages, compacted_html=True)
                self.assertEqual(json.loads(json.dumps(actual)), row)

    def test_selected_rows_and_33_row_fallback_have_different_quality_outcomes(self):
        fallback = []
        for row in self.report()['rows']:
            selected = set(row['scope']['selected_short_ids'])
            after = row['row_content'][1]
            self.assertTrue(all(len(r['pages']) == 1 for r in after['rows'] if r['identity'] in selected))
            if row['case'] == 'mixed-bound-33-last':
                fallback.append(row)
                self.assertEqual(row['scope']['resource_count'], 33)
                self.assertFalse(selected or row['scope']['expanded_long_ids'])
                self.assertTrue(row['pdf_geometry_unchanged'] and row['pdf_page_pixels_identical'])
                self.assertTrue(after['long']['purpose_pages_without_name'])
                self.assertIsNone(after['long']['missing_identity_header_pages'])
            else:
                self.assertFalse(after['long']['missing_identity_header_pages'])
                self.assertFalse(after['long']['split_purpose_paragraphs'])
                self.assertTrue(after['long']['tail_together'])
        self.assertEqual(len(fallback), 4)

    def test_word_boundary_diagnostics_do_not_claim_full_content_acceptance(self):
        boundaries = [r for r in self.report()['rows'] if r['case'].startswith('mixed-bound-')]
        self.assertEqual(len(boundaries), 8)
        for row in boundaries:
            result = row['word_boundary_content']
            self.assertIsNone(row['word_paragraphs_checked'])
            self.assertFalse(result['complete_content_acceptance'] or result['layout_acceptance'])
            self.assertTrue(row['word_unchanged'] and row['word_page_pixels_identical'])
            self.assertEqual(result['all_paragraphs_verified'], not result['unresolved_paragraphs'])
        self.assertTrue(any(r['word_boundary_content']['unresolved_paragraphs'] for r in boundaries))

    def test_html_restores_exact_bytes_and_remains_an_html_export(self):
        font = files('dsw_document_template_tool').joinpath('resources/fonts/NotoSansTC-Variable.ttf').read_bytes()
        digest = hashlib.sha256(font).hexdigest(); count = 0
        for phase in ['before', 'after']:
            for path in (ARCHIVE / phase / 'renders').glob('*.html'):
                proof = json.loads(path.with_suffix('.html.compact.json').read_text())
                self.assertFalse(proof['native_pdf_entry_input'])
                self.assertEqual(sha(path), proof['compact_html_sha256'])
                self.assertEqual(set(proof['fonts']), {digest})
                restored = restore_source(path.read_bytes(), {digest: font})
                self.assertEqual(hashlib.sha256(restored).hexdigest(), proof['original_html_sha256'])
                count += 1
        self.assertEqual(count, 40)

    def test_native_fixtures_and_exact_previous_prototype_are_bound(self):
        original = json.loads((ROOT / 'reviews/2026-09-21-native-mixed-header/provenance/prototype.json').read_text())
        prototype = json.loads((ARCHIVE / 'provenance/prototype.json').read_text())
        self.assertEqual(prototype['packages'], original['packages'])
        self.assertEqual(prototype['recipe_sha256'], sha(ARCHIVE / 'reproduce/experiment/prototype.py'))
        fixtures = json.loads((ARCHIVE / 'fixtures/provenance.json').read_text())
        self.assertEqual(fixtures['generator_sha256'], sha(ARCHIVE / 'reproduce/prepare_mixed_boundary_controls.py'))
        self.assertEqual(fixtures['parent_generator_sha256'], sha(ARCHIVE / 'reproduce/generate_mixed_budget_fixtures.py'))
        self.assertEqual(len(fixtures['cases']), 10)
        for key, row in fixtures['cases'].items():
            locale, case = key.split('/')
            language = 'english' if locale == 'en' else 'chinese'
            self.assertEqual(sha(ARCHIVE / 'fixtures' / (key + '.json')), row['recipe_sha256'])
            self.assertEqual(sha(ARCHIVE / 'fixtures' / (key + '.events.json')), row['events_sha256'])
            for phase in ['before', 'after']:
                for profile in ['review', 'submission']:
                    for fmt in ['html', 'pdf', 'docx']:
                        name = '-'.join([case, profile, language]) + '.' + fmt + '.fixture.json'
                        receipt = json.loads((ARCHIVE / phase / 'renders' / name).read_text())
                        for field in ['recipe_sha256', 'events_sha256', 'km_sha256']:
                            self.assertEqual(receipt[field], row[field])


if __name__ == '__main__': unittest.main()
