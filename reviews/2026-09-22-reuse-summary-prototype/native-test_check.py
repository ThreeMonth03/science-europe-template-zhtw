import unittest
from unittest.mock import patch
from lxml import etree
import check


class LayoutTests(unittest.TestCase):
    def run_layout(self, xml):
        with patch('check.subprocess.check_output', return_value=xml.encode()):
            return check.layout('synthetic.pdf')

    def test_nested_page_is_counted(self):
        _, pages, text = self.run_layout('<html xmlns="urn:test"><body><doc><page width="100" height="100"><flow><word xMin="1" xMax="9" yMin="2" yMax="8">yes</word></flow></page></doc></body></html>')
        self.assertEqual(1, len(pages)); self.assertEqual('yes', text)

    def test_empty_inventory_rejected(self):
        with self.assertRaises(AssertionError): self.run_layout('<html><body><doc/></body></html>')

    def test_blank_page_rejected(self):
        with self.assertRaises(AssertionError): self.run_layout('<html><body><page width="100" height="100"/></body></html>')

    def test_off_page_word_rejected(self):
        with self.assertRaises(AssertionError): self.run_layout('<html><body><page width="100" height="100"><word xMin="95" xMax="109" yMin="2" yMax="8">bad</word></page></body></html>')


class WordScopeTests(unittest.TestCase):
    def fixture(self):
        return etree.fromstring('<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:bookmarkStart w:name="q-how-data"/><w:tbl><w:t>Q1 table</w:t></w:tbl><w:bookmarkStart w:name="q-what-data"/><w:tbl><w:t>Q8 table</w:t></w:tbl></w:body></w:document>')

    def test_only_q1_is_in_scope(self):
        question = check.word_question(self.fixture())
        self.assertEqual('Q1 table', ''.join(question.itertext()))

    def test_other_question_cannot_replace_deleted_table(self):
        tree = self.fixture(); body = tree[0]; body.remove(body[1])
        self.assertEqual('', ''.join(check.word_question(tree).itertext()))

    def test_missing_boundary_rejected(self):
        tree = self.fixture(); body = tree[0]; body.remove(body[2])
        with self.assertRaises(AssertionError): check.word_question(tree)

    def test_reversed_boundary_rejected(self):
        with self.assertRaises(AssertionError): check.word_question(self.fixture(), 'q-what-data', 'q-how-data')


if __name__ == '__main__': unittest.main()
