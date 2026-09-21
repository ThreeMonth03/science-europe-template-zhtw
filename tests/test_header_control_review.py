"""Native control artifacts remain evidence, not a whole-template release gate."""
import hashlib
from importlib.resources import files
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'reviews/2026-09-21-header-controls'
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'experiments/mixed-budget-header')]
from artifact_utils import sha
from check_header_controls import compare_pair
from compact import restore_source


class HeaderControlReviewTests(unittest.TestCase):
    def report(self):
        return json.loads((ARCHIVE / 'provenance/comparison.json').read_text())

    def test_sealed_evidence_keeps_unfinished_release_and_submission_scope_explicit(self):
        hashes = json.loads((ARCHIVE / 'checksums.json').read_text())
        self.assertEqual(hashes, {str(p.relative_to(ARCHIVE)): sha(p) for p in ARCHIVE.rglob('*')
                                 if p.is_file() and p.name != 'checksums.json'})
        report = self.report()
        self.assertTrue(report['selected_checks_passed'] and report['native_export'] and report['prototype_only'])
        for key in ['release_acceptance', 'microsoft_word_acceptance', 'full_control_matrix_complete', 'native_pdf_entry_captured']:
            self.assertFalse(report[key])
        self.assertEqual(report['checker_sha256'], sha(ARCHIVE / 'reproduce/check_header_controls.py'))
        self.assertEqual(len(report['rows']), 20)
        for row in report['rows']:
            if row['case'] == 'empty':
                self.assertEqual(row['remaining_system_gap_nodes'], 22 if row['profile'] == 'review' else 20)
            if row['case'] == 'profile-partial' and row['profile'] == 'submission':
                self.assertEqual(row['remaining_system_gap_nodes'], 0)
        life = json.loads((ARCHIVE / 'provenance/worker-lifecycle.json').read_text())
        self.assertTrue(life['stock_worker_restored'])
        self.assertEqual(life['deleted_owned_templates'], 4)
        self.assertFalse(life['capture_observer_attached'] or life['production_touched'])
        self.assertTrue(all(r['status'] == 'exited' for r in life['after']))

    def test_every_native_pair_is_recomputed_including_word_and_actual_page_boxes(self):
        packages = [json.loads((ARCHIVE / 'provenance' / (phase + '-manifest.json')).read_text())['sha256']
                    for phase in ['before', 'after']]
        for row in self.report()['rows']:
            with self.subTest(stem=row['stem']):
                actual = compare_pair(ARCHIVE / 'before', ARCHIVE / 'after',
                    row['stem'], row['case'], row['profile'], row['language'],
                    package_hashes=packages, compacted_html=True)
                # Match the JSON representation of tuples in metric records.
                self.assertEqual(json.loads(json.dumps(actual)), row)

    def test_all_archived_html_restores_exact_export_bytes_not_pdf_entry_claims(self):
        font = files('dsw_document_template_tool').joinpath('resources/fonts/NotoSansTC-Variable.ttf').read_bytes()
        digest = hashlib.sha256(font).hexdigest()
        count = 0
        for phase in ['before', 'after']:
            for path in (ARCHIVE / phase / 'renders').glob('*.html'):
                proof = json.loads(path.with_suffix('.html.compact.json').read_text())
                self.assertFalse(proof['native_pdf_entry_input'])
                self.assertEqual(sha(path), proof['compact_html_sha256'])
                self.assertEqual(set(proof['fonts']), {digest})
                actual = restore_source(path.read_bytes(), {digest: font})
                self.assertEqual(hashlib.sha256(actual).hexdigest(), proof['original_html_sha256'])
                count += 1
        self.assertEqual(count, 40)

    def test_fixtures_native_receipts_and_previous_prototype_are_bound(self):
        previous = json.loads((ROOT / 'reviews/2026-09-21-native-mixed-header/provenance/prototype.json').read_text())
        prototype = json.loads((ARCHIVE / 'provenance/prototype.json').read_text())
        self.assertEqual(prototype['packages'], previous['packages'])
        self.assertEqual(prototype['recipe_sha256'], sha(ARCHIVE / 'reproduce/experiment/prototype.py'))
        fixtures = json.loads((ARCHIVE / 'fixtures/provenance.json').read_text())
        self.assertEqual(fixtures['generator_sha256'], sha(ARCHIVE / 'reproduce/prepare_header_controls.py'))
        for row in fixtures['cases']:
            stem = row['case']; folder = ARCHIVE / 'fixtures' / row['locale']
            self.assertEqual(sha(folder / (stem + '.json')), row['recipe_sha256'])
            self.assertEqual(sha(folder / (stem + '.events.json')), row['events_sha256'])
            language = 'english' if row['locale'] == 'en' else 'chinese'
            for phase in ['before', 'after']:
                for profile in ['review', 'submission']:
                    for fmt in ['html', 'pdf', 'docx']:
                        name = '-'.join([stem, profile, language]) + '.' + fmt + '.fixture.json'
                        receipt = json.loads((ARCHIVE / phase / 'renders' / name).read_text())
                        for key in ['recipe_sha256', 'events_sha256', 'km_sha256']:
                            self.assertEqual(receipt[key], row[key])


if __name__ == '__main__': unittest.main()
