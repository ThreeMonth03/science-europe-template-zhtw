from pathlib import Path
import sys
import unittest
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_metadata_gap_panel_outputs import pair_geometry, FACTS, CASES
from test_archive_gap_outputs import bbox, page


class MetadataGapPanelOutputTests(unittest.TestCase):
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
