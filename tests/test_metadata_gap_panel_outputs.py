from pathlib import Path
import sys
import unittest
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_metadata_gap_panel_outputs import pair_geometry, prefix_before_q3, FACTS, CASES
from test_archive_gap_outputs import bbox, page


class MetadataGapPanelOutputTests(unittest.TestCase):
    def test_prefix_uses_complete_wrapped_title_and_retains_body_geometry(self):
        soup = BeautifulSoup('<div class="question"><h3>1. First question?</h3></div><div id="q-docs-metadata"><h3>3. A long metadata question?</h3></div>', 'html.parser')
        body = page((50, '1. First question?'), (80, 'Keep Original.csv.'), (100, '3. A long metadata'), (115, 'question?'), (150, 'Answer.'))
        before = bbox(page((50, 'Cover 0.3.35')), body)
        after = bbox(page((50, 'Cover 0.3.36')), body)
        original = prefix_before_q3(before, soup)
        self.assertEqual(original, prefix_before_q3(after, soup))
        self.assertEqual(len(original), 4)
        for changed in [after.replace(b'Original.csv', b'original.csv'), after.replace(b'yMin="80"', b'yMin="81"')]:
            self.assertNotEqual(original, prefix_before_q3(changed, soup))
        with self.assertRaises(AssertionError):
            prefix_before_q3(after.replace(b'question?', b'question!'), soup)

    def test_missing_pair_must_shrink_without_losing_text_or_changing_metrics(self):
        soup = BeautifulSoup('<div id="q-docs-metadata"><p data-fact-id="' + FACTS[0]
            + '">First.</p><p data-fact-id="' + FACTS[1] + '">Last.</p></div>', 'html.parser')
        before = bbox(page((50, 'First.'), (100, 'Last.')))
        after = bbox(page((50, 'First.'), (80, 'Last.')))
        result = pair_geometry(before, after, soup)
        self.assertEqual(result['before_span_pt'] - result['after_span_pt'], 20)
        for changed in [before, bbox(page((50, 'First.')), page((80, 'Last.'))),
                        after.replace(b'First.', b'first.'), after.replace(b'xMax="150"', b'xMax="151"')]:
            with self.assertRaises(AssertionError):
                pair_geometry(before, changed, soup)

    def test_native_scope_has_answered_authored_empty_and_no_controls(self):
        self.assertEqual(CASES, ['metadata-partial', 'metadata-complete', 'metadata-private-text', 'empty', 'negative'])
