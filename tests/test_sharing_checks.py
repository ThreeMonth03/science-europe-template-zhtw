import sys
import unittest
from pathlib import Path
from bs4 import BeautifulSoup
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_sharing_outputs import assert_date_lines, direct_runs, compare_prior
from check_polish_outputs import canonical_word_dates


class SharingCheckTests(unittest.TestCase):
    def test_only_registered_nonbreaking_dates_are_canonicalized(self):
        soup = BeautifulSoup('<span class="date-value" data-iso-date="2027-12-31">2027-12-31</span>', 'html.parser')
        text = '2027\u201112\u201131; Access-2027-12-31.csv; 2028\u201101\u201101'
        self.assertEqual('2027-12-31; Access-2027-12-31.csv; 2028\u201101\u201101', canonical_word_dates(soup, text))

    def test_date_geometry_rejects_split_and_cover_page_false_positive(self):
        for lines, ok in [(['2027-12-31'], True), (['2027\u201112\u201131'], True), (['2027-', '12-31'], False), (['Access-2027-12-31.csv'], False)]:
            content = ['2027-12-31', '10. Sharing'] + lines + ['11. Preservation']
            xml = '<doc>' + ''.join('<line><word>'+v+'</word></line>' for v in content) + '</doc>'
            if ok: assert_date_lines(xml, ['2027-12-31'], '10.Sharing', '11.Preservation')
            else:
                with self.assertRaises(AssertionError): assert_date_lines(xml, ['2027-12-31'], '10.Sharing', '11.Preservation')

    def test_preservation_gap_and_free_block_stop_joining(self):
        soup = BeautifulSoup('<div><p>Published.</p><p>Ten years.</p><div class="reading-gap"><p>Review.</p></div><p>Metadata.</p><div class="answer-detail"><p>Authored.</p></div><p>Budget.</p></div>', 'html.parser')
        self.assertEqual([['Published.', 'Ten years.'], ['Metadata.'], ['Budget.']], direct_runs(soup.div))

    def test_prior_comparison_does_not_hide_unreviewed_changes(self):
        ids = ['q-share-restrictions', 'q-data-preservation'] + [f'q-{i}' for i in range(13)]
        old = BeautifulSoup(''.join(f'<div class="question" id="{q}"><p>Original.</p></div>' for q in ids), 'html.parser')
        new = BeautifulSoup(str(old), 'html.parser')
        self.assertEqual(15, compare_prior(old, new, 'chinese'))
        new.find(id='q-3').p.string = 'Unexpected.'
        with self.assertRaises(AssertionError): compare_prior(old, new, 'chinese')

    def test_reviewed_phrases_do_not_authorize_rewriting_authored_answers(self):
        ids = ['q-share-restrictions', 'q-data-preservation'] + [f'q-{i}' for i in range(13)]
        old = BeautifulSoup(''.join(f'<div class="question" id="{q}"><p>Original.</p></div>' for q in ids), 'html.parser')
        old.find(id='q-data-preservation').append(BeautifulSoup('<div class="answer-detail"><p>專案專用資料儲存庫。</p></div>', 'html.parser').div)
        new = BeautifulSoup(str(old), 'html.parser')
        new.select_one('.answer-detail p').string = '本計畫專用的資料儲存庫。'
        with self.assertRaises(AssertionError): compare_prior(old, new, 'chinese')
