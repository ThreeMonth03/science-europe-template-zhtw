import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'reviews/2026-09-21-entity-labels'
sys.path[:0] = [str(ROOT / 'experiments/entity-labels'), str(ROOT / 'scripts')]
from entity_recipe import baseline, patch
from entity_native import run


def english_root():
    return next(p for p in [ROOT.parent / 'english', ROOT.parent / 'science-europe-template']
                if (p / 'scripts/output_profile_contract.py').is_file())


class EntityNativeTests(unittest.TestCase):
    def test_sealed_complete_evidence_and_no_release_claim(self):
        seal = ARCHIVE / 'checksums.json'
        self.assertEqual(hashlib.sha256(seal.read_bytes()).hexdigest(),
                         '567daf5949fea60ca22887a06b8a16fd138bb0bbc4bbd1a150efae9d544aff7b')
        files = json.loads(seal.read_text()); self.assertEqual(len(files), 103)
        self.assertEqual(set(files), {str(p.relative_to(ARCHIVE)) for p in ARCHIVE.rglob('*')
                                     if p.is_file() and p != seal})
        for name, digest in files.items():
            self.assertEqual(hashlib.sha256((ARCHIVE / name).read_bytes()).hexdigest(), digest, name)
        inventory = json.loads((ARCHIVE / 'inventory.json').read_text())
        for key in ['source_integrated', 'translation_tree_modified', 'production_touched',
                    'global_switch_complete', 'release_acceptance', 'microsoft_word_acceptance']:
            self.assertFalse(inventory[key])
        self.assertEqual((inventory['structural_checks'], inventory['native_pairs'],
                          inventory['native_artifacts'], inventory['word_previews']), (1056, 4, 24, 8))

    def test_all_native_pairs_recomputed_against_exact_frozen_proof(self):
        rows = run(ARCHIVE / 'before', ARCHIVE / 'after', ARCHIVE / 'fixtures', english_root(), compacted=True)
        expected = json.loads((ARCHIVE / 'provenance/native.json').read_text())
        self.assertTrue(expected['passed'])
        self.assertEqual(json.loads(json.dumps(rows)), expected['rows'])
        for row in rows:
            self.assertEqual(len(row['changes']), 10 if row['profile'] == 'submission' else 0)

    def test_original_assets_and_exact_five_file_recipe(self):
        members = json.loads((ARCHIVE / 'provenance/package-members.json').read_text())
        prototype = json.loads((ARCHIVE / 'provenance/prototype.json').read_text())
        for language in ['english', 'chinese']:
            before, after = [json.loads((ARCHIVE / phase / (language + '.json')).read_text())
                             for phase in ['before', 'after']]
            self.assertEqual(before, baseline(language))
            changed, operations = patch(before, language)
            self.assertEqual(after, changed)
            self.assertEqual(operations, prototype['packages'][language + '.zip']['operations'])
            old, new = [members[phase][language] for phase in ['before', 'after']]
            self.assertEqual(old.keys(), new.keys())
            self.assertEqual({n for n in old if old[n] != new[n]}, {'template/template.json'})
            for name in old:
                self.assertEqual(dict(before=old[name], after=new[name]),
                                 prototype['packages'][language + '.zip']['members'][name])

    def test_quota_failure_retained_and_all_owned_state_restored(self):
        quota = json.loads((ARCHIVE / 'provenance/storage-allowance.json').read_text())
        self.assertTrue(quota['restored']); self.assertEqual(quota['before'], quota['after'])
        self.assertEqual(quota['before']['storage'], -1500000000)
        self.assertEqual(quota['during'], dict(quota['before'], storage=-1750000000))
        self.assertFalse(quota['data_deleted']); self.assertFalse(quota['production_touched'])
        failed = json.loads((ARCHIVE / 'provenance/failed-missing-info-render-report.json').read_text())
        self.assertFalse(failed['all_renders_succeeded'])
        self.assertEqual(len(failed['renders']), 1); self.assertFalse(failed['renders'][0]['rendered'])
        self.assertIn('No space left for this document', (ARCHIVE / 'provenance/failed-render.log').read_text())
        for name, count in [('before/owned-test-template-cleanup.json', 2),
                            ('after/owned-test-template-cleanup.json', 2),
                            ('provenance/failed-owned-test-template-cleanup.json', 1)]:
            cleanup = json.loads((ARCHIVE / name).read_text())
            self.assertEqual(len(cleanup['deleted']), count)
            self.assertEqual((cleanup['project_references'], cleanup['document_references']), (0, 0))
        life = json.loads((ARCHIVE / 'provenance/worker-lifecycle.json').read_text())
        self.assertTrue(life['stock_worker_restored']); self.assertEqual(len(life['after']), 4)
        self.assertTrue(all(r['status'] == 'exited' for r in life['after']))


if __name__ == '__main__': unittest.main()
