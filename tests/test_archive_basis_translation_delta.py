import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from probe_personal_data_translation import archived_pairs,verify_translation_chain


class ArchiveBasisTranslationDeltaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.delta=json.loads((ROOT/'docs/archive-basis-translation-delta.json').read_text())
        cls.current=archived_pairs(cls.delta['baseline'])
        for pair in cls.delta['removed']:cls.current.remove(tuple(pair))
        cls.current.extend(map(tuple,cls.delta['added']))

    def test_reviewed_chain_retains_historical_and_current_checks(self):
        old,new=verify_translation_chain(self.current)
        self.assertEqual(old['retained_units'],718)
        self.assertEqual(new['retained_units'],727)

    def test_unrelated_changes_missing_labels_and_placeholder_edits_fail(self):
        for index in [0,-1,-2,-3]:
            values=self.current.copy();source,target=values[index]
            values[index]=(source,target+'。')
            with self.assertRaises(AssertionError):verify_translation_chain(values)
        with self.assertRaises(AssertionError):verify_translation_chain(self.current[:-1])
