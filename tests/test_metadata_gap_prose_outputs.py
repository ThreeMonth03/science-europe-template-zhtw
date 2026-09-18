from pathlib import Path
import sys
import unittest
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from check_metadata_gap_prose_outputs import prose_geometry, FACTS
from test_archive_gap_outputs import bbox, page


class MetadataGapProseOutputTests(unittest.TestCase):
    def test_geometry_requires_complete_unique_shorter_prose(self):
        before = BeautifulSoup('<div id="q-docs-metadata"><p data-fact-id="' + FACTS[0]
            + '">First.</p><p data-fact-id="' + FACTS[1] + '">Last.</p></div>', 'html.parser')
        after = BeautifulSoup('<p class="metadata-publication-gap">First; last.</p>', 'html.parser')
        old = bbox(page((50, 'First.'), (100, 'Last.')))
        new = bbox(page((50, 'First; last.')))
        result = prose_geometry(old, new, before, after)
        self.assertLess(result['after_span_pt'], result['before_span_pt'])
        for changed in [bbox(page((50, 'First;'))), bbox(page((50, 'First; Last.'))),
                        new.replace(b'yMax="60"', b'yMax="58"'),
                        bbox(page((50, 'First; last.'), (100, 'First; last.'))),
                        bbox(page((50, 'First;')), page((100, 'last.')))]:
            with self.assertRaises(AssertionError):
                prose_geometry(old, changed, before, after)
