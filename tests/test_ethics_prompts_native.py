import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch as mock_patch

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'reviews/2026-09-21-ethics-prompts'
sys.path[:0] = [str(ROOT / 'experiments/ethics-prompts'), str(ROOT / 'scripts')]
from ethics_recipe import baseline, patch
from ethics_native import run, visual_gate, lead_placement


def english_root():
    return next(p for p in [ROOT.parent / 'english', ROOT.parent / 'science-europe-template']
                if (p / 'scripts/output_profile_contract.py').is_file())


class EthicsNativeTests(unittest.TestCase):
    def test_sealed_inventory_and_explicit_nonacceptance(self):
        seal = ARCHIVE / 'checksums.json'
        self.assertEqual(hashlib.sha256(seal.read_bytes()).hexdigest(),
                         '7bbe9c7eb8bc9dffbfa818271e796e528af3f5ef8241063216761eb68f1b6a34')
        files = json.loads(seal.read_text()); self.assertEqual(len(files), 168)
        self.assertEqual(set(files), {str(p.relative_to(ARCHIVE)) for p in ARCHIVE.rglob('*') if p.is_file() and p != seal})
        for name, digest in files.items(): self.assertEqual(hashlib.sha256((ARCHIVE / name).read_bytes()).hexdigest(), digest)
        inventory = json.loads((ARCHIVE / 'inventory.json').read_text())
        for key in ['source_integrated', 'source_integration_allowed', 'translation_tree_modified', 'visual_gate_passed',
                    'production_touched', 'global_switch_complete', 'release_acceptance', 'microsoft_word_acceptance']:
            self.assertFalse(inventory[key])
        self.assertEqual((inventory['structural_checks'], inventory['native_pairs'], inventory['native_artifacts'],
                          inventory['word_previews']), (536, 8, 48, 16))

    def test_all_native_content_and_the_visual_failure_reproduce(self):
        rows = run(ARCHIVE / 'before', ARCHIVE / 'after', ARCHIVE / 'fixtures', english_root(), compacted=True)
        proof = json.loads((ARCHIVE / 'provenance/native.json').read_text())
        self.assertEqual(json.loads(json.dumps(rows)), proof['rows'])
        self.assertTrue(proof['passed']); self.assertTrue(proof['content_contract_passed'])
        gate = visual_gate(rows)
        self.assertEqual(gate, {k: proof[k] for k in ['visual_gate_passed', 'visual_blockers']})
        self.assertFalse(gate['visual_gate_passed']); self.assertEqual(len(gate['visual_blockers']), 1)
        blocker = gate['visual_blockers'][0]
        self.assertEqual((blocker['case'], blocker['language'], blocker['profile'], blocker['engine']),
                         ('ethics-missing', 'chinese', 'submission', 'native_pdf'))
        self.assertTrue(blocker['new_regression'])
        self.assertEqual(blocker['before'], dict(lead_page=3, first_answer_page=3, together=True))
        self.assertEqual(blocker['after'], dict(lead_page=2, first_answer_page=3, together=False))

    def test_one_file_recipe_assets_and_metadata_are_bound(self):
        members = json.loads((ARCHIVE / 'provenance/package-members.json').read_text())
        prototype = json.loads((ARCHIVE / 'after/prototype.json').read_text())
        for language in ['english', 'chinese']:
            old, new = [json.loads((ARCHIVE / phase / (language + '.json')).read_text()) for phase in ['before', 'after']]
            self.assertEqual(old, baseline(language))
            expected, operations = patch(old, language)
            self.assertEqual(new, expected)
            self.assertEqual(operations, prototype['packages'][language + '.zip']['operations'])
            before, after = [members[phase][language] for phase in ['before', 'after']]
            self.assertEqual(before.keys(), after.keys())
            self.assertEqual({n for n in before if before[n] != after[n]}, {'template/template.json'})
            for name in before:
                self.assertEqual(dict(before=before[name], after=after[name]),
                                 prototype['packages'][language + '.zip']['members'][name])

    def test_only_owned_test_templates_removed_and_local_configuration_restored(self):
        for phase in ['before', 'after']:
            cleanup = json.loads((ARCHIVE / phase / 'owned-test-template-cleanup.json').read_text())
            self.assertTrue(cleanup['run_completed_successfully']); self.assertEqual(len(cleanup['deleted']), 2)
            self.assertEqual((cleanup['project_references'], cleanup['document_references']), (0, 0))
        allowance = json.loads((ARCHIVE / 'provenance/storage-allowance.json').read_text())
        self.assertTrue(allowance['restored']); self.assertEqual(allowance['before'], allowance['after'])
        self.assertEqual(allowance['before']['storage'], -1500000000)
        self.assertEqual(allowance['during'], dict(allowance['before'], storage=-1750000000))
        life = json.loads((ARCHIVE / 'provenance/worker-lifecycle.json').read_text())
        self.assertTrue(life['stock_worker_restored']); self.assertEqual(len(life['after']), 4)
        self.assertTrue(all(r['status'] == 'exited' for r in life['after']))

    def test_layout_anchors_cannot_ignore_missing_duplicate_or_changed_punctuation(self):
        lead = 'The purpose of processing the personal data can be described as follows:'
        authored = 'AUTHORED-PURPOSE: N/A / 0 / Original.csv.'
        with mock_patch('ethics_native.subprocess.check_output', return_value=lead + '\f' + authored):
            self.assertEqual(lead_placement(Path('synthetic.pdf'), 'english'),
                             dict(lead_page=1, first_answer_page=2, together=False))
        with mock_patch('ethics_native.subprocess.check_output', return_value=lead + '\n' + authored):
            self.assertTrue(lead_placement(Path('synthetic.pdf'), 'english')['together'])
        for raw in [authored, lead + authored + authored, lead + authored.replace('.csv.', '.csv!')]:
            with mock_patch('ethics_native.subprocess.check_output', return_value=raw):
                with self.assertRaises(AssertionError): lead_placement(Path('synthetic.pdf'), 'english')


if __name__ == '__main__': unittest.main()
