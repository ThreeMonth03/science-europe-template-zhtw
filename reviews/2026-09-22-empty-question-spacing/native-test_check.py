import unittest
from unittest.mock import patch
from lxml import etree
import check

class CheckerTests(unittest.TestCase):
    def test_pdf_nested_pages_are_counted(self):
        xml=b'<html><body><doc><page width="100" height="100"><line><word xMin="1" yMin="2" xMax="9" yMax="8">yes</word></line></page></doc></body></html>'
        with patch('check.subprocess.check_output',return_value=xml):self.assertEqual(1,len(check.pdf('x')[1]))
    def test_no_pages_is_not_success(self):
        with patch('check.subprocess.check_output',return_value=b'<html><body/></html>'):
            with self.assertRaises(AssertionError):check.pdf('x')
    def test_outside_page_is_rejected(self):
        xml=b'<html><body><page width="100" height="100"><word xMin="1" yMin="2" xMax="109" yMax="8">bad</word></page></body></html>'
        with patch('check.subprocess.check_output',return_value=xml):
            with self.assertRaises(AssertionError):check.pdf('x')
    def test_heading_scope_requires_a_unique_bookmark(self):
        xml=etree.fromstring(('<w:document xmlns:w="'+check.W+'"><w:body><w:bookmarkStart w:name="q-a"/><w:p><w:pPr><w:pStyle w:val="Heading3"/></w:pPr><w:r><w:t>Original</w:t></w:r></w:p></w:body></w:document>').encode())
        self.assertEqual('Original',''.join(check.heading(xml,'q-a').itertext()))
        with self.assertRaises(AssertionError):check.heading(xml,'q-other')
    def test_not_a_question_heading_is_rejected(self):
        xml=etree.fromstring(('<w:document xmlns:w="'+check.W+'"><w:body><w:bookmarkStart w:name="q-a"/><w:p><w:pPr><w:pStyle w:val="BodyText"/></w:pPr></w:p></w:body></w:document>').encode())
        with self.assertRaises(AssertionError):check.heading(xml,'q-a')
    def test_bookmark_only_paragraph_does_not_replace_heading(self):
        xml=etree.fromstring(('<w:document xmlns:w="'+check.W+'"><w:body><w:p><w:bookmarkStart w:name="q-a"/></w:p><w:p><w:pPr><w:pStyle w:val="Heading3"/></w:pPr><w:r><w:t>Correct</w:t></w:r></w:p></w:body></w:document>').encode())
        self.assertEqual('Correct',''.join(check.heading(xml,'q-a').itertext()))
    def test_search_must_not_cross_next_question(self):
        xml=etree.fromstring(('<w:document xmlns:w="'+check.W+'"><w:body><w:bookmarkStart w:name="q-a"/><w:bookmarkStart w:name="q-b"/><w:p><w:pPr><w:pStyle w:val="Heading3"/></w:pPr></w:p></w:body></w:document>').encode())
        with self.assertRaises(AssertionError):check.heading(xml,'q-a')
    def test_escaped_property_text_is_not_a_heading(self):
        xml=etree.fromstring(('<w:document xmlns:w="'+check.W+'"><w:body><w:bookmarkStart w:name="q-a"/><w:p>&lt;w:pPr&gt;&lt;w:pStyle w:val="Heading3" /&gt;&lt;/w:pPr&gt;<w:r><w:t>Unstyled</w:t></w:r></w:p></w:body></w:document>').encode())
        with self.assertRaises(AssertionError):check.heading(xml,'q-a')
if __name__=='__main__':unittest.main()
