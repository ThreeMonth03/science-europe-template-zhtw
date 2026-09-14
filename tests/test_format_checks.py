import sys
import unittest
from pathlib import Path
from bs4 import BeautifulSoup
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_format_outputs import compare_unchanged


def document(collection='Collector retained.', formats='Original format.', other='Unchanged.'):
    body = f'<div class="question" id="q-what-data"><p>{collection}</p><h4>Data formats and types</h4><div>{formats}</div><p>After formats.</p></div>'
    body += ''.join(f'<div class="question" id="q-{i}">{other}</div>' for i in range(14))
    return BeautifulSoup(body, 'html.parser')


class FormatComparisonTests(unittest.TestCase):
    def test_only_format_block_can_change(self):
        self.assertEqual(15, compare_unchanged(document(), document(formats='Improved format.')))

    def test_collection_change_is_not_hidden(self):
        with self.assertRaises(AssertionError): compare_unchanged(document(), document(collection='Wrong collector.'))

    def test_other_question_change_is_not_hidden(self):
        with self.assertRaises(AssertionError): compare_unchanged(document(), document(other='Wrong answer.'))

    def test_q2_suffix_change_is_not_hidden(self):
        new = document(); new.find(id='q-what-data').find_all('p')[-1].string = 'Lost suffix.'
        with self.assertRaises(AssertionError): compare_unchanged(document(), new)
