import json
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from probe_personal_data_translation import archived_pairs, verify_latest_translation_chain
from probe_pdf_budget_translation import pair


class StorageGapDeltaTests(unittest.TestCase):
    def test_current_tree_exact_reviewed_chain(self):
        values = [pair(f.read_text()) for f in (ROOT/'translation/tree').rglob('translation.md')]
        personal, following = verify_latest_translation_chain(values)
        self.assertEqual(personal['retained_units'], 718)
        self.assertEqual(following['storage_gap']['retained_units'], 733)
        for index in [0, -1, -2]:
            mutated = values.copy(); source, target = mutated[index]; mutated[index] = (source, target+'。')
            with self.assertRaises(AssertionError): verify_latest_translation_chain(mutated)
        with self.assertRaises(AssertionError): verify_latest_translation_chain(values[:-1])

    def test_placeholder_and_gap_cannot_be_lost(self):
        delta = json.loads((ROOT/'docs/storage-gap-translation-delta.json').read_text())
        values = archived_pairs(delta['baseline'])
        for old in delta['removed']: values.remove(tuple(old))
        values.extend(map(tuple, delta['added']))
        for index in [-1, -2]:
            mutated = values.copy(); source, target = mutated[index]; mutated[index] = (source, target.replace('{size}', '0')+'!')
            with self.assertRaises(AssertionError): verify_latest_translation_chain(mutated)
