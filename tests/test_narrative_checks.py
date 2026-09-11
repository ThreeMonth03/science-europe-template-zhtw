import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_narrative_outputs import compare_questions, page_bounds


class NarrativeCheckerTests(unittest.TestCase):
    def document(self):
        names = ['q-access-security', 'q-share-restrictions', 'q-store-backup'] + [f'q-test-{i}' for i in range(12)]
        return BeautifulSoup(''.join(f'<div class="question" id="{name}"><p>Retained fact for {name}.</p></div>' for name in names), 'html.parser')

    def test_unchanged_questions_pass(self):
        self.assertEqual(15, compare_questions(self.document(), self.document(), 'english'))

    def test_unplanned_answer_loss_is_rejected(self):
        old, new = self.document(), self.document()
        new.find(id='q-store-backup').p.string = 'Different claim.'
        with self.assertRaises(AssertionError): compare_questions(old, new, 'english')

    def test_only_declared_archive_paragraph_and_reference_are_excluded(self):
        old, new = self.document(), self.document()
        paragraph = old.new_tag('p')
        paragraph.string = 'We will be archiving data for long-term preservation already during our project.'
        old.find(id='q-access-security').append(paragraph)
        reference = new.new_tag('p', attrs={'class': 'answer-reference'})
        reference.string = 'See question 5 for archival and backup arrangements.'
        new.find(id='q-access-security').append(reference)
        self.assertEqual(15, compare_questions(old, new, 'english'))

    def test_page_boundary_check_rejects_off_page_text(self):
        xml = b'<html><page width="595" height="842"><word xMin="20" yMin="30" xMax="596" yMax="45">clipped</word></page></html>'
        with patch('check_narrative_outputs.subprocess.check_output', return_value=xml):
            with self.assertRaises(AssertionError): page_bounds(Path('synthetic.pdf'))
