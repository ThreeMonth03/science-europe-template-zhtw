import sys
import unittest
from pathlib import Path
from bs4 import BeautifulSoup
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from check_identifier_outputs import compare_html, check_units
from check_context_outputs import joined_paragraphs


class IdentifierChecksTests(unittest.TestCase):
    def pair(self):
        others=''.join(f'<div class="question" id="q-{i}"><p>Other {i}.</p></div>' for i in range(14))
        start='<div class="question" id="q-persistent-identifier"><div class="dataset-section" data-item-id="data"><div class="distribution-section" data-item-id="dist">'
        labels='<p class="answer-lead"><strong>Distribution 1</strong></p><p class="answer-lead"><strong>Repository</strong></p>'
        fact='<p data-fact-id="persistent-identifier" data-status="complete">Assigned.</p>'
        policy='<p>By repository.</p><p>Resolvable.</p></div>'
        author='<div class="answer-detail"><p>Author.csv.</p><p>Second author paragraph.</p></div>'
        old=start+labels+fact+'<div class="identifier-arrangement dataset-policy">'+policy+author+'</div></div></div>'
        new=start+'<div class="identifier-heading">'+labels+'</div><div class="identifier-arrangement dataset-policy">'+fact+policy+author+'</div></div></div>'
        return [BeautifulSoup(others+s,'html.parser') for s in [old,new]]

    def test_only_declared_wrapper_and_paragraph_move_are_allowed(self):
        old,new=self.pair(); before=str(new)
        self.assertEqual(15,compare_html(old,new)); self.assertEqual(before,str(new))
        self.assertEqual(['Distribution1Repository','Assigned.Byrepository.Resolvable.'],check_units(new))

    def test_text_states_scope_authored_and_other_questions_are_not_excluded(self):
        for selector in ['#q-2 p','.identifier-heading strong','.identifier-arrangement p','.answer-detail p']:
            old,new=self.pair(); new.select_one(selector).string='Changed.'
            with self.assertRaises(AssertionError): compare_html(old,new)
        for key,value in [('data-status','missing'),('data-fact-id','different')]:
            old,new=self.pair(); new.select_one('[data-fact-id]')[key]=value
            with self.assertRaises(AssertionError): compare_html(old,new)
        old,new=self.pair(); new.select_one('.distribution-section')['data-item-id']='other'
        with self.assertRaises(AssertionError): compare_html(old,new)

    def test_authored_or_gap_inside_joining_container_is_rejected(self):
        for selector in ['.identifier-heading','.identifier-arrangement']:
            old,new=self.pair(); new.select_one(selector).append(new.select_one('.answer-detail').extract())
            with self.assertRaises(AssertionError): compare_html(old,new)

    def test_word_join_requires_adjacent_whole_same_style_paragraphs(self):
        rows=[('Heading','Pilot Label',None,None),('One.','Body Text',None,None),('Two.','Body Text',None,None)]
        result,count=joined_paragraphs(rows,['One.Two.'])
        self.assertEqual(1,count); self.assertEqual('One.Two.',result[1][0])
        for target in ['One.Changed.','One.Two.Extra']:
            with self.assertRaises(AssertionError): joined_paragraphs(rows,[target])
        rows[2]=('Two.','Pilot Lead',None,None)
        with self.assertRaises(AssertionError): joined_paragraphs(rows,['One.Two.'])
