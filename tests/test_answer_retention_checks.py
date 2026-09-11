import sys
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_answer_retention import compact, numbered_question


class RetentionCheckTests(unittest.TestCase):
    def test_comparison_preserves_case_sensitive_identifiers(self):
        self.assertNotEqual(compact('CHANGELOG.md'), compact('changelog.md'))
        self.assertEqual(compact('2048\n GB'), compact('2048 GB'))

    def test_duplicate_upstream_ids_do_not_select_the_wrong_question(self):
        soup = BeautifulSoup('<div class="question" id="duplicate"><h3>5. Backup?</h3></div>'
                             '<div class="question" id="duplicate"><h3>12. Software?</h3></div>', 'html.parser')
        self.assertIn('Software?', numbered_question(soup, 12).get_text())
        with self.assertRaises(ValueError):
            numbered_question(soup, 13)
