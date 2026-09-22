from collections import Counter
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'experiments/full-km-followups'))
from followup_build import translation_delta
from probe_pdf_budget_translation import pair


class FullKmFollowupTranslationTests(unittest.TestCase):
    def test_exact_six_new_units_do_not_change_767_old_occurrences(self):
        old = [pair(p.read_text()) for p in (ROOT / 'translation/tree').rglob('translation.md')]
        added = list(json.loads((ROOT / 'experiments/full-km-followups/translations.json').read_text()).items())
        self.assertEqual(translation_delta(old, old + added)['total'], 773)
        for bad in [old + added[:-1], old + added + added[:1],
                    old[1:] + added + [old[0]],  # same multiset is valid, tested separately below
                    old[1:] + [(old[0][0], old[0][1] + '!')] + added]:
            if Counter(bad) == Counter(old + added):
                self.assertEqual(translation_delta(old, bad)['retained'], 767)
            else:
                with self.assertRaises(AssertionError): translation_delta(old, bad)
        self.assertTrue(all('。' not in zh if source.endswith(':') else zh.endswith('。') for source, zh in added))


if __name__ == '__main__': unittest.main()
