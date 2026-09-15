import copy
import sys
import unittest
from pathlib import Path
from bs4 import BeautifulSoup
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from check_q9_word_outputs import groups
from check_q8_word_outputs import compare_word
from test_q8_word_outputs import document


class Q9WordTests(unittest.TestCase):
    def test_scope_allows_only_q9_name(self):
        a,b=document(),document()
        for d in [a,b]:
            d.paragraphs[2].text='9. Ethics?';d.paragraphs[5].text='10. Sharing?'
        b.paragraphs[3].style='Pilot List Lead'
        self.assertEqual(1,compare_word(a,b,['Name.csv'],question=9))
        with self.assertRaises(AssertionError):compare_word(a,b,['Name.csv'])
        b.paragraphs[4].style='Pilot List Lead'
        with self.assertRaises(AssertionError):compare_word(a,b,['Name.csv'],question=9)

    def test_ignored_style_does_not_pass(self):
        with self.assertRaises(AssertionError):compare_word(document(),document(),['Name.csv'],question=9)

    def test_groups_do_not_invent_a_missing_flag(self):
        html='<div id="q-ethical-issues"><div class="answer"><ul><li><strong>One.csv</strong><ul><li>Personal.</li></ul></li><li><strong>Unknown</strong><span>Not provided.</span></li></ul></div></div>'
        self.assertEqual([('One.csv',['Personal.'])],groups(BeautifulSoup(html,'html.parser')))
        self.assertEqual([],groups(BeautifulSoup(html.replace('One.csv','x'*81),'html.parser')))

    def test_complex_flags_are_not_selected(self):
        html='<div id="q-ethical-issues"><div class="answer"><ul><li><strong>Name</strong><ul><li><em>Authored</em></li></ul></li></ul></div></div>'
        self.assertEqual([],groups(BeautifulSoup(html,'html.parser')))
