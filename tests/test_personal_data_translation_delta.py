"""Reviewed Q7/Q9 exceptions must not permit unrelated translation drift."""
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from probe_personal_data_translation import DELTA, archived_pairs, verify_tree


class PersonalDataTranslationDeltaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.delta = json.loads(DELTA.read_text())
        cls.old = archived_pairs(cls.delta['baseline'])
        cls.expected = cls.old.copy()
        for pair in cls.delta['removed']: cls.expected.remove(tuple(pair))
        cls.expected.extend(map(tuple, cls.delta['added']))

    def test_only_reviewed_delta_passes(self):
        self.assertEqual(718, verify_tree(self.expected)['retained_units'])

    def test_missing_new_prompt_is_rejected(self):
        with self.assertRaises(AssertionError): verify_tree(self.expected[:-1])

    def test_same_count_does_not_hide_unreviewed_punctuation_change(self):
        changed = self.expected.copy()
        source, target = changed[0]; changed[0] = (source, target+'。')
        with self.assertRaises(AssertionError): verify_tree(changed)

    def test_old_unsupported_claim_cannot_replace_new_neutral_sentence(self):
        changed = self.expected.copy(); changed[-2] = tuple(self.delta['removed'][-2])
        with self.assertRaises(AssertionError): verify_tree(changed)
