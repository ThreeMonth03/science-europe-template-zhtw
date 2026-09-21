import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch as mock_patch
import subprocess
from bs4 import BeautifulSoup
from docx import Document
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'reviews/2026-09-21-word-short-tables'
sys.path[:0] = [str(ROOT / 'experiments/word-short-tables'), str(ROOT / 'scripts')]
from table_recipe import ARCHIVE as PARENT, SEAL as PARENT_SEAL, HERE, LUA, sha, baseline, patch
from table_native import run, table_placement

SEAL = 'ef2fad262a2615ab5eeb35a40a6e8513adb68678171c0ae5753de4e8b75a8fb9'


class WordShortTableNativeTests(unittest.TestCase):
    def test_frozen_inventory_and_explicit_acceptance_limits(self):
        seal = ARCHIVE / 'checksums.json'; self.assertEqual(sha(seal.read_bytes()), SEAL)
        files = json.loads(seal.read_text())
        self.assertEqual(len(files), 192)
        self.assertEqual(set(files), {str(p.relative_to(ARCHIVE)) for p in ARCHIVE.rglob('*') if p.is_file() and p != seal})
        for name, digest in files.items(): self.assertEqual(sha((ARCHIVE / name).read_bytes()), digest)
        inventory = json.loads((ARCHIVE / 'inventory.json').read_text())
        for key in ['source_integrated', 'translation_tree_modified', 'production_touched', 'release_acceptance',
                    'full_visual_acceptance', 'global_switch_complete', 'microsoft_word_acceptance',
                    'source_integration_allowed', 'native_asset_pipeline_checked']:
            self.assertFalse(inventory[key])
        for key in ['bounded_word_fix_verified', 'scoped_visual_gate_passed', 'inherited_pdf_tail_page_fix_preserved',
                    'source_integration_pending', 'existing_assets_unchanged']: self.assertTrue(inventory[key])
        self.assertEqual(inventory['parent_seal_sha256'], PARENT_SEAL)
        self.assertEqual(inventory['integration_blocker'], 'machine-xml-misclassified-as-translatable-prose')
        self.assertEqual(inventory['unexpected_machine_translation_units'], 7)
        self.assertTrue(inventory['asset_translation_rehearsal_passed'])
        self.assertEqual((inventory['native_pairs'], inventory['new_native_artifacts'], inventory['new_word_previews'],
                          inventory['changed_native_word_tables'], inventory['unchanged_native_word_controls']), (12, 36, 12, 4, 8))

    def test_all_twelve_native_pairs_reproduce_and_long_short_tables_are_intact(self):
        rows = run(ARCHIVE / 'after', ARCHIVE / 'fixtures', compacted=True)
        proof = json.loads((ARCHIVE / 'provenance/native.json').read_text()); self.assertTrue(proof['passed'])
        self.assertEqual(json.loads(json.dumps(rows)), proof['rows'])
        for row in rows:
            self.assertTrue(row['html_bytes_identical']); self.assertTrue(row['rendered']['native_pdf']['pixels_and_geometry_identical'])
            self.assertEqual(row['word_delta']['changed_tables'], int(row['case'] == 'ethics-long'))
            if row['case'] == 'ethics-long':
                place = row['rendered']['word_preview']['table_placement']; self.assertTrue(place['complete_short_table'])
                expected = {('chinese', 'review'): 8, ('english', 'review'): 6, ('chinese', 'submission'): 6, ('english', 'submission'): 5}
                self.assertEqual(place['page'], expected[row['language'], row['profile']])
        target = next(r for r in rows if (r['case'], r['language'], r['profile']) == ('ethics-long', 'chinese', 'submission'))
        self.assertEqual(target['rendered']['native_pdf']['after']['pages'], 7)

    def test_package_changes_are_bounded_and_common_to_both_languages(self):
        members = json.loads((ARCHIVE / 'provenance/package-members.json').read_text())
        prior = json.loads((PARENT / 'provenance/package-members.json').read_text())
        for language in ['english', 'chinese']:
            actual = json.loads((ARCHIVE / 'after' / (language + '.json')).read_text())
            self.assertEqual(actual, patch(baseline(language), language))
            self.assertEqual(set(members[language]) - set(prior[language]), {'template/assets/' + LUA})
            self.assertEqual({n for n in prior[language] if members[language][n] != prior[language][n]}, {'template/template.json'})
            self.assertEqual(members[language]['template/assets/' + LUA], sha((HERE / 'short-tables.lua').read_bytes()))

    def test_table_placement_rejects_missing_header_and_disabled_repetition(self):
        stem = ARCHIVE / 'after/renders/ethics-long-review-chinese'
        soup = BeautifulSoup(stem.with_suffix('.html').read_text(), 'html.parser'); doc = Document(stem.with_suffix('.docx'))
        pdf = ARCHIVE / 'after/word-preview/ethics-long-review-chinese.pdf'
        bbox = subprocess.check_output(['pdftotext', '-bbox-layout', str(pdf), '-'])
        with mock_patch('table_native.subprocess.check_output', return_value=bbox.replace(b'>Value<', b'>VALUE<', 1)):
            with self.assertRaises(AssertionError): table_placement(pdf, soup, doc)
        target = next(t for t in doc.tables if any(c.text == 'Retained.' for r in t.rows for c in r.cells))
        target.rows[0]._tr.find(qn('w:trPr') + '/' + qn('w:tblHeader')).set(qn('w:val'), 'off')
        with self.assertRaises(AssertionError): table_placement(pdf, soup, doc)

    def test_owned_cleanup_and_capacity_restore(self):
        for folder in ['after', 'initial-guard']:
            cleanup = json.loads((ARCHIVE / folder / 'owned-test-template-cleanup.json').read_text())
            self.assertTrue(cleanup['run_completed_successfully']); self.assertEqual(len(cleanup['deleted']), 2)
            self.assertEqual((cleanup['project_references'], cleanup['document_references']), (0, 0))
        for name in ['provenance/storage-allowance.json', 'initial-guard/storage-allowance.json']:
            allowance = json.loads((ARCHIVE / name).read_text())
            self.assertTrue(allowance['restored']); self.assertEqual(allowance['before'], allowance['after'])
        life = json.loads((ARCHIVE / 'provenance/worker-lifecycle.json').read_text())
        self.assertTrue(life['stock_worker_restored']); self.assertEqual(len(life['after']), 4)
        self.assertTrue(all(r['status'] == 'exited' for r in life['after']))


if __name__ == '__main__': unittest.main()
