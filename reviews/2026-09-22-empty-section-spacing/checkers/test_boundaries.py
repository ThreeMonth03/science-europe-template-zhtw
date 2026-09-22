import unittest
from bs4 import BeautifulSoup
import check

class BoundaryTests(unittest.TestCase):
    def test_word_cover_and_all_word_text_are_never_stripped(self):
        pages=['Unnumbered cover','Original 1/2 remains 2/2']
        self.assertEqual(check.content_pages('word_preview',pages),pages)
        with self.assertRaises(AssertionError):check.content_pages('pdf',pages)
        with self.assertRaises(AssertionError):check.content_pages('unknown',pages)

    def test_strip_only_exact_generated_counters(self):
        self.assertEqual(check.without_counters(['Original1/2answer1/2','Last2/2']),['Original1/2answer','Last'])
        with self.assertRaises(AssertionError):check.without_counters(['Original2/2'])
        with self.assertRaises(AssertionError):check.without_counters(['Original'])

    def test_missing_or_ambiguous_titles_fail_closed(self):
        with self.assertRaises(AssertionError):check.location(['original'],'missing')
        with self.assertRaises(AssertionError):check.location(['title title'],'title')
        self.assertEqual(check.location(['abc','def'],'cde'),(2,1,2))

    def test_orphan_section_detected(self):
        page=BeautifulSoup('<div id="dmp-content"><section class="dmp-section" id="sec-test"><h2>Title</h2><div class="question"><h3>Question</h3></div></section></div>','html.parser')
        self.assertTrue(check.boundaries(page,['TitleQuestion'])[0]['heading_kept_with_question'])
        self.assertFalse(check.boundaries(page,['Title','Question'])[0]['heading_kept_with_question'])

    def test_q8_name_permission_split_detected(self):
        page=BeautifulSoup('<div id="q-copyright-ipr"><h3>Q8</h3><div class="answer"><ul><li><div>Dataset</div>Permission</li></ul></div></div><div id="q-ethical-issues"><h3>Q9</h3></div>','html.parser')
        self.assertTrue(check.q8_pair(page,['Q8DatasetPermissionQ9']))
        self.assertFalse(check.q8_pair(page,['Q8Dataset','PermissionQ9']))
if __name__=='__main__':unittest.main()
