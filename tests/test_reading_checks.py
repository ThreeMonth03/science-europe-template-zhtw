import sys
import unittest
from pathlib import Path
from bs4 import BeautifulSoup
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_reading_outputs import compare_unchanged


class ReadingCheckerTests(unittest.TestCase):
    def source(self):
        return ''.join(f'<div class="question" id="{qid}"><p>Retain answer {i}.</p></div>'
                       for i, qid in enumerate(['q-what-data', 'q-docs-metadata'] + [f'q-{j}' for j in range(13)]))

    def test_only_instrument_section_is_excluded(self):
        before = self.source().replace('<p>Retain answer 0.', '<div><h4>Instrument datasets</h4>Old wording</div><p>Retain answer 0.')
        after = before.replace('Old wording', 'Reviewed wording')
        self.assertEqual(15, compare_unchanged(*[BeautifulSoup(s, 'html.parser') for s in (before, after)]))

    def test_unrelated_q2_and_q3_answer_loss_fails(self):
        for index in (0, 1, 8):
            before = self.source(); after = before.replace(f'Retain answer {index}.', '')
            with self.assertRaises(AssertionError): compare_unchanged(*[BeautifulSoup(s, 'html.parser') for s in (before, after)])
