import copy
import sys
import unittest
from pathlib import Path
from bs4 import BeautifulSoup
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from identifier_followup_contract import expected_fields, check_followups, LABELS, RESOLUTIONS, warning_text
from check_identifier_followup_outputs import compare_html, check_followup_page_text

IDS={name:name for name in ['preservingCUuid','producedDataQUuid','isPublishedDataQUuid','isPublishedDataYesAUuid','publishedDistrosQUuid','publishedDataIdentifierQUuid','publishedDataIdentifierYesAUuid','publishedDataIdentifierAssignsQUuid','publishedDataIdentifierResolvableQUuid']}
IDS.update({f'publishedDataIdentifier{q}{a}AUuid':f'{q}{a}' for q,answers in [('Assigns',['ProjectDataSteward','InstitDataSteward','Repository']),('Resolvable',['Yes','No'])] for a in answers})


class FollowupChecksTests(unittest.TestCase):
    def pair(self,language='english'):
        data=IDS['preservingCUuid']+'.'+IDS['producedDataQUuid']; pub=data+'.dataset.'+IDS['isPublishedDataQUuid']
        dist=pub+'.'+IDS['isPublishedDataYesAUuid']+'.'+IDS['publishedDistrosQUuid']; pid=dist+'.route.'+IDS['publishedDataIdentifierQUuid']
        replies={data:['dataset'],pub:IDS['isPublishedDataYesAUuid'],dist:['route'],pid:IDS['publishedDataIdentifierYesAUuid'],
                 pid+'.'+IDS['publishedDataIdentifierYesAUuid']+'.'+IDS['publishedDataIdentifierResolvableQUuid']:IDS['publishedDataIdentifierResolvableNoAUuid']}
        column=0 if language=='english' else 1
        prefix='<div class="question" id="q-persistent-identifier"><div class="dataset-section" data-item-id="dataset"><div class="distribution-section" data-item-id="route"><div class="identifier-heading"><p class="answer-lead"><strong>Route</strong></p></div><div class="identifier-arrangement dataset-policy"><p data-fact-id="persistent-identifier" data-status="complete">Assigned.</p>'
        tail='</div><div class="answer-detail"><p>Author.csv.</p><p>Second author paragraph.</p></div></div></div></div>'
        old=prefix+'<p>'+RESOLUTIONS['No'][column]+'</p>'+tail
        marker='<p data-requirement-id="SE-5d" data-fact-id="identifier-resolution" data-status="explicit-no">'+RESOLUTIONS['No'][column]+'</p>'
        span='<span data-requirement-id="SE-5d" data-fact-id="identifier-assigner" data-status="missing">'+LABELS['identifier-assigner'][column]+'</span>'
        gap='<div class="identifier-followups reading-gap"><p class="data-gap" data-requirement-id="SE-5d">'+warning_text('missing',[span],language)+'</p></div>'
        new=prefix.replace('<div class="identifier-arrangement dataset-policy">','<div class="identifier-followup-unit short-reading-unit"><div class="identifier-arrangement dataset-policy">')+marker+'</div>'+gap+'</div>'+tail[len('</div>'):]
        other=''.join(f'<div class="question" id="q-{i}"><p>Other {i}.</p></div>' for i in range(14))
        return BeautifulSoup(other+old,'html.parser'),BeautifulSoup(other+new,'html.parser'),replies

    def test_checked_notice_and_markers_are_the_only_changes(self):
        for language in ['english','chinese']:
            old,new,replies=self.pair(language); unchanged=str(new)
            self.assertEqual(15,compare_html(old,new,replies,IDS,language)); self.assertEqual(unchanged,str(new))

    def test_notice_deletion_wording_state_and_scope_mutations_fail(self):
        for mutation in ['remove','text','state','scope','duplicate']:
            old,new,replies=self.pair(); node=new.select_one('.identifier-followups span')
            if mutation=='remove': node.decompose()
            elif mutation=='text': node.string='Invented policy.'
            elif mutation=='state': node['data-status']='explicit-no'
            elif mutation=='scope': new.select_one('.question').append(node.extract())
            else: node.insert_after(copy.deepcopy(node))
            with self.assertRaises(AssertionError): compare_html(old,new,replies,IDS,'english')

    def test_existing_answer_author_and_other_question_are_not_excluded(self):
        for selector in ['[data-fact-id="identifier-resolution"]','.answer-detail p','#q-2 p']:
            old,new,replies=self.pair(); new.select_one(selector).string='Changed.'
            with self.assertRaises(AssertionError): compare_html(old,new,replies,IDS,'english')

    def test_unknown_is_review_and_inactive_parent_has_no_children(self):
        _,_,replies=self.pair(); key=next(k for k in replies if k.endswith(IDS['publishedDataIdentifierResolvableQUuid']))
        replies[key]='future-choice'
        self.assertEqual('needs-review',expected_fields(replies,IDS)[('dataset','route')]['identifier-resolution'][0])
        parent=next(k for k in replies if k.endswith(IDS['publishedDataIdentifierQUuid'])); replies[parent]='No'
        self.assertEqual({},expected_fields(replies,IDS)[('dataset','route')])

    def test_fixture_cannot_bypass_known_stock_table_gate(self):
        from run_pilot import TABLE_CASES
        self.assertIn('identifier-followups',TABLE_CASES)

    def test_notice_must_share_page_with_its_heading_and_policy(self):
        _,soup,_=self.pair()
        q=soup.select_one('#q-persistent-identifier')
        h=soup.new_tag('h3'); h.string='13. Identifier arrangements'; q.insert(0,h)
        q14=soup.new_tag('div',id='q-dm-responsible'); h14=soup.new_tag('h3'); h14.string='14. Responsible staff'; q14.append(h14); soup.append(q14)
        heading=soup.select_one('.identifier-heading').get_text()
        policy=soup.select_one('.identifier-arrangement').get_text()
        notice=soup.select_one('.identifier-followups').get_text()
        for split in ['', '\f']:
            text=h.get_text()+heading+policy+split+notice+h14.get_text()
            if split:
                with self.assertRaises(AssertionError): check_followup_page_text(text,soup)
            else: self.assertEqual(1,len(check_followup_page_text(text,soup)))
