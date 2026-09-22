import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from probe_personal_data_translation import archived_pairs, verify_prose_translation_chain, verify_submission_translation_chain
from probe_pdf_budget_translation import pair


class MetadataGapProseDelta(unittest.TestCase):
    def test_exact_current_tree_retains_every_previous_pair(self):
        current = [pair(p.read_text()) for p in (ROOT/'translation/tree').rglob('translation.md')]
        _, following = verify_submission_translation_chain(current)
        self.assertEqual(following['metadata_gap_prose']['retained_units'], 744)
        self.assertEqual(len(current), 767)
        self.assertEqual(following['submission_reading']['retained_units'], 762)

    def test_rejects_lost_changed_or_additional_translation(self):
        delta = json.loads((ROOT/'docs/metadata-gap-prose-translation-delta.json').read_text())
        old = archived_pairs(delta['baseline'])
        current = old + list(map(tuple, delta['added']))
        verify_prose_translation_chain(current)
        for index in [0, 744, 745, 746]:
            changed = list(current)
            en, zh = changed[index]
            changed[index] = (en, zh + '。')
            with self.assertRaises(AssertionError):
                verify_prose_translation_chain(changed)
        for changed in [current[:-1], current + [('Extra', '額外')]]:
            with self.assertRaises(AssertionError):
                verify_prose_translation_chain(changed)
