"""Synthetic mutation tests for the allowed Word spacing delta."""
import unittest
import check

START='<w:document xmlns:w="'+check.W+'"><w:body>'
END='</w:body></w:document>'
HEADING='<w:p><w:pPr><w:pStyle w:val="Heading2" />{spacing}</w:pPr><w:r><w:t>{text}</w:t></w:r></w:p>'
SPACE='<w:spacing w:before="60" w:after="40"/>'
def doc(text='Title',spacing='',extra=''):
    return (START+HEADING.format(text=text,spacing=spacing)+extra+END).encode()

class ScopeTests(unittest.TestCase):
    def test_exact_spacing_only(self):
        self.assertEqual(check.normalize_xml(doc(),doc(spacing=SPACE),['Title']),1)
    def test_unaffected_documents_exact(self):
        self.assertEqual(check.normalize_xml(doc(),doc(),[]),0)
    def test_missing_or_unapproved_spacing_rejected(self):
        for after,allowed in [(doc(),['Title']),(doc(spacing=SPACE),[])]:
            with self.assertRaises(AssertionError):check.normalize_xml(doc(),after,allowed)
    def test_text_change_rejected(self):
        with self.assertRaises(AssertionError):check.normalize_xml(doc(),doc(text='Lost',spacing=SPACE),['Title'])
    def test_different_spacing_rejected(self):
        with self.assertRaises(AssertionError):check.normalize_xml(doc(),doc(spacing=SPACE.replace('60','0')),['Title'])
    def test_added_keep_next_rejected(self):
        with self.assertRaises(AssertionError):check.normalize_xml(doc(),doc(spacing=SPACE+'<w:keepNext w:val="0"/>'),['Title'])
    def test_ambiguous_same_text_heading_rejected(self):
        extra=HEADING.format(text='Title',spacing='')
        with self.assertRaises(AssertionError):check.normalize_xml(doc(extra=extra),doc(spacing=SPACE,extra=extra),['Title'])
    def test_mixed_section_is_not_empty(self):
        q='<div class="question compact-empty-question"><h3>Question</h3><div class="answer"></div></div>'
        sections=''.join('<section class="dmp-section"><h2>Section '+str(i)+'</h2>'+q*2+'</section>' for i in range(6))
        html='<div id="dmp-content">'+sections+'</div>'
        self.assertEqual(len(check.expected_sections(html)),6)
        self.assertEqual(len(check.expected_sections(html.replace(' compact-empty-question','',1))),5)
    def test_only_declared_question_keep_chain_allowed(self):
        old=doc(text='Question').replace(b'Heading2',b'Heading3').replace(b'</w:pPr>',b'<w:keepNext w:val="0"/></w:pPr>')
        new=old.replace(b'keepNext w:val="0"',b'keepNext w:val="1"')
        check.normalize_xml(old,new,[],['Question'])
        with self.assertRaises(AssertionError):check.normalize_xml(old,new,[],[])
        with self.assertRaises(AssertionError):check.normalize_xml(old,old,[],['Question'])
if __name__=='__main__':unittest.main()
