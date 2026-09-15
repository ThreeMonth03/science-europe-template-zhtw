import sys
import unittest
from pathlib import Path
from bs4 import BeautifulSoup
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_pdf_budget_reading_outputs import exact_long_sequence, normalize_owned_indent, question_pages, sequence_pages, positioned_budget_lists


class PdfBudgetReadingTests(unittest.TestCase):
    def fixture(self):
        return BeautifulSoup('<div id="q-required-resources"><h4>Budget</h4><table class="resource-table"><thead><tr><th>Purpose</th><th>Amount</th><th>Funding</th></tr></thead><tbody><tr><td><p><strong>Resource</strong></p><div class="answer-detail"><p>BUDGET-PARA-01:First.</p><p>BUDGET-PARA-02:Second.</p><ul><li>Keep.</li></ul></div><p>Allocation.</p></td><td>5000TWD</td><td>Institute</td></tr><tr><td>Tail.</td><td>0TWD</td><td>Institute</td></tr></tbody></table></div>', 'html.parser')

    def pages(self):
        return ['PrefixBudgetPurposeAmountFundingResource5000TWDInstituteBUDGET-PARA-01:First.',
                'PurposeAmountFundingResource5000TWDInstituteBUDGET-PARA-02:Second.Keep.Allocation.PurposeAmountFundingTail.0TWDInstitute']

    def test_exact_content_and_only_verified_header_repeats(self):
        self.assertEqual(1, exact_long_sequence(self.pages(), self.fixture()))
        for original, replacement in [('5000TWD', ''), ('Keep.', ''), ('Allocation.', ''), ('0TWD', ''), ('Second.', 'Second.Second.'), ('InstituteBUDGET', 'InstitutionBUDGET')]:
            pages = self.pages(); pages[1] = pages[1].replace(original, replacement)
            with self.assertRaises(AssertionError): exact_long_sequence(pages, self.fixture())

    def test_normalization_never_trims_author_paragraph(self):
        soup = BeautifulSoup('<table class="resource-table"><tbody><tr><td><p>\n 支援項目：管理。\n </p><div class="answer-detail"><p>\n 支援項目：  我的原句。\n </p></div></td></tr></tbody></table>', 'html.parser')
        author = str(soup.select_one('.answer-detail'))
        normalize_owned_indent(soup)
        self.assertEqual('支援項目：管理。', soup.select_one('td > p').text)
        self.assertEqual(author, str(soup.select_one('.answer-detail')))

    def test_cover_exclusion_keeps_page_position(self):
        soup = BeautifulSoup('<div class="question"><h3>1. First</h3></div>', 'html.parser')
        self.assertEqual(['', 'Answer', 'More'], question_pages(['Cover', '1.FirstAnswer', 'More'], soup))
        self.assertNotEqual(question_pages(['1.FirstAnswer', 'More'], soup), question_pages(['Cover', '1.FirstAnswer', 'More'], soup))

    def test_only_verified_page_suffix_bullets_can_be_excluded(self):
        bbox = '<doc><page><line><word>•</word><word>Keep.</word></line></page></doc>'.encode()
        self.assertEqual(['BudgetText'], sequence_pages(['BudgetText•'], bbox, self.fixture()))
        for pages in [['Budget•Text'], ['BudgetText••'], ['BudgetText']]:
            with self.assertRaises(AssertionError): sequence_pages(pages, bbox, self.fixture())
        soup = self.fixture(); soup.find('li').string = 'Author • original.'
        with self.assertRaises(AssertionError): sequence_pages(['BudgetText•'], bbox, soup)

    def test_budget_bullets_must_share_their_original_item_line(self):
        soup = self.fixture(); item = soup.new_tag('li'); item.string = 'Second.'; soup.ul.append(item)
        bbox = '<doc><page><line><word>•</word><word>Keep.</word></line><line><word>•</word><word>Second.</word></line></page></doc>'.encode()
        self.assertEqual(2, positioned_budget_lists(bbox, soup))
        for changed in [bbox.replace(b'<word>Second.</word>', b'<word>Changed.</word>'), bbox.replace('<word>•</word>'.encode(), b'')]:
            with self.assertRaises(AssertionError): positioned_budget_lists(changed, soup)
