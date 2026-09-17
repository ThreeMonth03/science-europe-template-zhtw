import json
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from probe_personal_data_translation import archived_pairs, verify_metadata_translation_chain


class MetadataDeltaTests(unittest.TestCase):
    def test_exact_nine_additions_and_negation_are_required(self):
        delta = json.loads((ROOT/'docs/metadata-followup-translation-delta.json').read_text())
        self.assertEqual(delta['removed'], [])
        self.assertEqual((delta['baseline_units'], delta['current_units'], delta['retained_units']), (735,744,735))
        values = archived_pairs(delta['baseline'])+list(map(tuple, delta['added']))
        verify_metadata_translation_chain(values)
        for index in range(735, 744):
            mutated = values.copy(); source, target = mutated[index]
            mutated[index] = (source, target.replace('不會','將會')+'。')
            with self.assertRaises(AssertionError): verify_metadata_translation_chain(mutated)
        with self.assertRaises(AssertionError): verify_metadata_translation_chain(values[:-1])
