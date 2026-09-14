import json
from pathlib import Path
import sys
import unittest
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from check_preservation_outputs import compare_prior, assert_no_punctuation_only_lines


class PreservationChecksTests(unittest.TestCase):
    def pair(self):
        old=''.join(f'<div class="question" id="q-{n}"><p>Original {n}.</p></div>' for n in range(14))
        old+='<div class="question" id="q-data-preservation"><p>Original preservation.</p><div class="answer-detail"><p>Author text.</p></div></div>'
        new=old.replace('Original preservation.</p>','Original preservation.</p><p data-fact-id="preservation-selection-review" data-status="needs-review">Review selection.</p>')
        return BeautifulSoup(old,'html.parser'),BeautifulSoup(new,'html.parser')

    def test_only_new_review_notice_is_allowed(self):
        a,b=self.pair(); self.assertEqual(15,compare_prior(a,b))
        self.assertIsNotNone(b.select_one('[data-fact-id="preservation-selection-review"]'))

    def test_prior_comparison_rejects_another_question_change(self):
        a,b=self.pair(); b.find(id='q-2').p.string='Changed.'
        with self.assertRaises(AssertionError): compare_prior(a,b)

    def test_prior_comparison_rejects_preservation_or_authored_rewrites(self):
        for selector in ['#q-data-preservation > p','.answer-detail > p']:
            a,b=self.pair(); b.select_one(selector).string='Changed.'
            with self.assertRaises(AssertionError): compare_prior(a,b)

    def test_reviewed_phrase_dictionary_has_no_duplicate_keys(self):
        pairs=json.loads((ROOT/'docs/readability-phrases.json').read_text(),object_pairs_hook=list)
        self.assertEqual(len(pairs),len({k for k,v in pairs}))

    def test_new_fixture_tables_remain_release_blockers(self):
        from run_pilot import TABLE_CASES
        self.assertTrue({'preservation-complete','preservation-partial','preservation-custom','preservation-no-cold'} <= TABLE_CASES)

    def test_punctuation_only_line_is_checked_in_q11_not_another_page(self):
        def xml(lines): return '<doc>'+''.join('<line><word>'+line+'</word></line>' for line in lines)+'</doc>'
        assert_no_punctuation_only_lines(xml(['。','11. Question','Keep data。','12. Next','。']),'11.','12.')
        for terminal in ['。','；','?']:
            with self.assertRaises(AssertionError):
                assert_no_punctuation_only_lines(xml(['11. Question','Keep data',terminal,'12. Next']),'11.','12.')
