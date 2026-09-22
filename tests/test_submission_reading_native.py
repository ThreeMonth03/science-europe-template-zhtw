import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'reviews/2026-09-22-submission-reading-integration'
sys.path.insert(0, str(ROOT / 'scripts'))
from artifact_utils import sha
from check_submission_reading_native import run
from submission_reading_integration import CONTRACT

SEAL = '4ba35be94dd77fb33357084e1df8ab05ab8ccc282267d0115197da233feb2f79'


class SubmissionReadingNativeTests(unittest.TestCase):
    def test_sealed_inventory_binds_real_paired_sources_and_same_day_control(self):
        seal = ARCHIVE / 'checksums.json'; self.assertEqual(sha(seal), SEAL)
        files = json.loads(seal.read_text())
        self.assertEqual(set(files), {str(p.relative_to(ARCHIVE)) for p in ARCHIVE.rglob('*') if p.is_file() and p != seal})
        for name, digest in files.items(): self.assertEqual(sha(ARCHIVE / name), digest, name)
        inventory = json.loads((ARCHIVE / 'inventory.json').read_text())
        self.assertEqual(inventory['prototype_seal_sha256'], CONTRACT['prototype_seal_sha256'])
        self.assertEqual(inventory['source_version'], '0.3.45')
        self.assertEqual((inventory['native_pairs'], inventory['native_artifacts'], inventory['word_previews']), (12, 36, 12))
        self.assertEqual((inventory['new_control_native_artifacts'], inventory['new_control_word_previews']), (36, 12))
        self.assertEqual((inventory['structural_checks'], inventory['retained_translation_pairs'], inventory['added_translation_pairs']), (3312, 762, 5))
        for key in ['source_integrated', 'native_rebuilt_source_checked', 'same_day_control', 'preview_ci_packages_identical_to_candidate']:
            self.assertTrue(inventory[key], key)
        for key in ['production_touched', 'full_visual_acceptance', 'release_acceptance', 'microsoft_word_acceptance', 'global_switch_complete']:
            self.assertFalse(inventory[key], key)
        manifest = json.loads((ARCHIVE / 'provenance/candidate-manifest.json').read_text())
        self.assertTrue(all(not value['dirty'] for value in manifest['checkouts'].values()))
        self.assertEqual(manifest['source']['commit'], inventory['source_commit'])
        self.assertEqual(manifest['checkouts']['translation']['commit'], inventory['translation_commit'])

    def test_all_12_native_pairs_recompute_without_date_or_pixel_exemptions(self):
        # All required source facts are sealed; no current build or DSW access.
        rows = run(ARCHIVE / 'native', ARCHIVE / 'fixtures', ROOT,
                   compacted=True, control=ARCHIVE / 'control')
        proof = json.loads((ARCHIVE / 'provenance/native.json').read_text())
        self.assertEqual(json.loads(json.dumps(rows)), proof['rows'])
        self.assertEqual(proof['checker_sha256'], sha(ROOT / 'scripts/check_submission_reading_native.py'))
        self.assertEqual(sum(bool(r['table_placement']) for r in rows), 4)
        for row in rows:
            self.assertTrue(row['html_bytes_identical'])
            self.assertTrue(row['word_components_identical_except_timestamps'])
            self.assertTrue(all(v['pixels_and_geometry_identical'] for v in row['rendered'].values()))
        long_zh = next(r for r in rows if (r['case'], r['language'], r['profile']) == ('ethics-long', 'chinese', 'submission'))
        self.assertEqual(long_zh['rendered']['native_pdf']['pages'], 7)
        diagnostics = json.loads((ARCHIVE / 'diagnostics/cross-day-date.json').read_text())
        self.assertEqual(len(diagnostics), 12)
        self.assertTrue(all(d['only_date_differs'] and not d['native_files_modified'] for d in diagnostics))

    def test_owned_cleanup_and_limits_restore_without_modifying_production(self):
        for phase in ['native', 'control']:
            cleanup = json.loads((ARCHIVE / phase / 'owned-test-template-cleanup.json').read_text())
            self.assertTrue(cleanup['run_completed_successfully']); self.assertEqual(len(cleanup['deleted']), 2)
            self.assertEqual((cleanup['project_references'], cleanup['document_references']), (0, 0))
        quota = json.loads((ARCHIVE / 'provenance/storage-allowance.json').read_text())
        self.assertTrue(quota['restored']); self.assertEqual(quota['before'], quota['after'])
        life = json.loads((ARCHIVE / 'provenance/worker-lifecycle.json').read_text())
        self.assertTrue(life['stock_worker_restored']); self.assertEqual(len(life['after']), 4)
        self.assertTrue(all(row['status'] == 'exited' for row in life['after']))


if __name__ == '__main__': unittest.main()
