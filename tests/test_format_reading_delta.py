import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from probe_personal_data_translation import archived_pairs,verify_current_translation_chain


class FormatReadingDeltaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        delta=json.loads((ROOT/'docs/format-reading-translation-delta.json').read_text())
        cls.current=archived_pairs(delta['baseline'])
        for pair in delta['removed']:cls.current.remove(tuple(pair))
        cls.current.extend(map(tuple,delta['added']))

    def test_exact_reviewed_chain(self):
        personal,following=verify_current_translation_chain(self.current)
        self.assertEqual(personal['retained_units'],718)
        self.assertEqual(following['archive_basis']['retained_units'],727)
        self.assertEqual(following['format_reading']['retained_units'],729)

    def test_unrelated_changes_lost_placeholders_and_punctuation_rejected(self):
        for i in [0,-1,-2,-3,-4,-5]:
            values=self.current.copy();source,target=values[i];values[i]=(source,target+'。')
            with self.assertRaises(AssertionError):verify_current_translation_chain(values)
        with self.assertRaises(AssertionError):verify_current_translation_chain(self.current[:-1])
