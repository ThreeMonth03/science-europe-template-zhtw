"""Protect the truth and reproducibility of a frozen audit, not template acceptance."""
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / 'reviews/2026-09-18-whole-document'
sys.path.insert(0, str(ROOT / 'scripts'))
from artifact_utils import sha


def read(name):
    return json.loads((REVIEW / name).read_text())


class WholeDocumentReviewTests(unittest.TestCase):
    def test_frozen_evidence_hashes_and_tools(self):
        hashes = read('checksums.json')
        files = {str(p.relative_to(REVIEW)) for p in REVIEW.rglob('*') if p.is_file() and p.name != 'checksums.json'}
        self.assertEqual(set(hashes), files)
        for name, digest in hashes.items():
            self.assertEqual(sha(REVIEW / name), digest, name)
        inventory = read('inventory.json')
        observed = read('observations.json')
        self.assertEqual(inventory['collector_sha256'], sha(REVIEW / 'reproduce/collect_whole_document_review.py'))
        self.assertEqual(observed['checker_sha256'], sha(REVIEW / 'reproduce/review_whole_document_facts.py'))
        self.assertEqual(observed['inventory_sha256'], sha(REVIEW / 'inventory.json'))

    def test_reused_and_new_renders_have_exact_package_and_fixture_provenance(self):
        inventory = read('inventory.json')
        self.assertEqual((inventory['fresh_native_renders'], inventory['reused_native_renders'], inventory['word_previews']), (6, 12, 6))
        self.assertEqual(len(inventory['rows']), 6)
        for label in ('fresh', 'reused'):
            manifest = read('provenance/' + label + '/manifest.json')
            self.assertEqual({k: manifest['sha256'][k] for k in inventory['package_sha256']}, inventory['package_sha256'])
        rebuilt = read('provenance/rebuild-manifest.json')
        self.assertEqual({k: rebuilt['sha256'][k] for k in inventory['package_sha256']}, inventory['package_sha256'])
        km = read('provenance/question-inventory.json')['knowledge_models']
        for row in inventory['rows']:
            stem = row['case'] + '-' + row['language']
            locale = 'en' if row['language'] == 'english' else 'zh-Hant'
            self.assertEqual(row['render_origin'], 'fresh' if row['case'] == 'narrative-long' else 'reused-exact-0.3.37')
            self.assertEqual(row['docx_sha256'], sha(REVIEW / 'native' / (stem + '.docx')))
            for fmt in ('html', 'pdf', 'docx'):
                receipt = read('native/' + stem + '.' + fmt + '.fixture.json')
                self.assertEqual(receipt['package_sha256'], inventory['package_sha256'][row['language'] + '.zip'])
                self.assertEqual(receipt['recipe_sha256'], sha(REVIEW / 'fixtures' / locale / (row['case'] + '.json')))
                self.assertEqual(receipt['events_sha256'], sha(REVIEW / 'fixtures' / locale / (row['case'] + '.events.json')))
                self.assertEqual(receipt['km_sha256'], km[locale]['km_sha256'])
            for fmt, details in row['formats'].items():
                folder = 'native' if fmt == 'pdf' else 'word-preview'
                self.assertEqual(details['sha256'], sha(REVIEW / folder / (stem + '.pdf')))
                self.assertEqual(len(details['question_heading_pages']), 15)
            self.assertGreater(row['verified_word_preview_paragraphs'], 0)

    def test_all_83_pages_have_individual_review_notes(self):
        expected = {(r['case'], r['language'], fmt, page)
                    for r in read('inventory.json')['rows'] for fmt, info in r['formats'].items()
                    for page in range(1, info['pages'] + 1)}
        rows = read('page-ledger.json')['rows']
        actual = {(r['case'], r['language'], r['format'], r['page']) for r in rows}
        self.assertEqual(len(rows), 83)
        self.assertEqual(actual, expected)
        for row in rows:
            self.assertTrue(row['note'].strip())
            self.assertIn('overview', row['review_method'])

    def test_defects_are_recorded_as_defects_not_acceptance(self):
        inventory = read('inventory.json')
        report = read('observations.json')
        self.assertFalse(inventory['release_acceptance'])
        self.assertFalse(inventory['microsoft_word_acceptance'])
        self.assertFalse(report['release_acceptance'])
        orphans = []
        for row in report['rows']:
            self.assertTrue(row['q6_active_access_control_followup_missing'])
            self.assertTrue(row['q8_ownership_reply_missing'])
            self.assertEqual(row['q6_missing_or_review_marker_count'], 0)
            self.assertEqual(row['q8_missing_or_review_marker_count'], 0)
            for fmt, facts in row['formats'].items():
                for section in facts['sections']:
                    if section['separated_from_first_question']:
                        orphans.append((row['case'], row['language'], fmt, section['id'], section['heading_page'], section['first_question_page']))
        self.assertEqual(orphans, [('metadata-complete', 'english', 'word-preview', 'sec-ethics-legal', 3, 4)])

    def test_long_answer_markers_and_local_cleanup(self):
        for language in ('english', 'chinese'):
            for fmt in ('pdf', 'word-preview'):
                text = (REVIEW / 'page-text' / ('narrative-long-' + language + '-' + fmt + '.txt')).read_text()
                self.assertEqual(re.findall(r'\[(\d{2})\]', text), [f'{i:02d}' for i in range(1, 81)])
        lifecycle = read('provenance/fresh/worker-lifecycle.json')
        self.assertTrue(lifecycle['same_worker_before_and_after'])
        self.assertEqual(lifecycle['before'], lifecycle['after'])
        cleanup = read('provenance/fresh/owned-test-template-cleanup.json')
        self.assertEqual(len(cleanup['deleted']), 2)
        self.assertEqual(cleanup['project_references'], 0)
        self.assertEqual(cleanup['document_references'], 0)
        self.assertTrue(read('provenance/fresh/runtime-restoration.json')['restored_stock_and_stopped'])
