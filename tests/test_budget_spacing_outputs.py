import copy
import sys
import unittest
from pathlib import Path
from lxml import etree
from docx.oxml.ns import qn
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_budget_spacing_outputs import compare_style_roots, long_page_checks
from bs4 import BeautifulSoup


class BudgetSpacingOutputTests(unittest.TestCase):
    def styles(self):
        old = etree.Element(qn('w:styles'))
        etree.SubElement(old, qn('w:style'), attrib={qn('w:styleId'): 'Normal'})
        etree.SubElement(old, qn('w:style'), attrib={qn('w:styleId'): 'PilotLongBudget'})
        new = copy.deepcopy(old)
        margins = etree.SubElement(etree.SubElement(new[-1], qn('w:tcPr')), qn('w:tcMar'))
        for edge in ['top', 'bottom']:
            etree.SubElement(margins, qn('w:' + edge), attrib={qn('w:w'): '28', qn('w:type'): 'dxa'})
        return old, new

    def test_exact_margin_change_allowed(self):
        compare_style_roots(*self.styles())

    def test_unrelated_style_change_rejected(self):
        old, new = self.styles(); etree.SubElement(new[0], qn('w:pPr'))
        with self.assertRaises(AssertionError): compare_style_roots(old, new)

    def test_other_padding_or_font_change_rejected(self):
        for field, value in [(qn('w:w'), '0'), (qn('w:type'), 'pct')]:
            old, new = self.styles(); new[-1][0][0][0].set(field, value)
            with self.assertRaises(AssertionError): compare_style_roots(old, new)
        old, new = self.styles(); etree.SubElement(new[-1], qn('w:rPr'))
        with self.assertRaises(AssertionError): compare_style_roots(old, new)

    def test_long_page_checks_reject_missing_split_and_duplicated_answers(self):
        purposes = [f'BUDGET-PARA-{i:02}:Original.' for i in range(1, 61)]
        soup = BeautifulSoup('<div id="q-required-resources"><h4>Budget</h4><table class="resource-table"><thead><tr><th>Purpose</th><th>Amount</th><th>Funding</th></tr></thead><tbody><tr><td><p><strong>Resource1</strong></p><div class="answer-detail"><p>First.</p>' + ''.join('<p>' + s + '</p>' for s in purposes) + '</div></td><td>5000TWD</td><td>Institute</td></tr><tr><td><p><strong>Resource2</strong></p></td><td>0TWD</td><td>Institute</td></tr></tbody></table></div>', 'html.parser')
        page = 'BudgetPurposeAmountFundingResource15000TWDInstituteFirst.' + ''.join(purposes) + 'Resource20TWD'
        self.assertTrue(long_page_checks([page], soup, True)['tail_shares_last_purpose_page'])
        for pages in [[page.replace(purposes[0], '')], [page, page],
                      [page.split(purposes[0])[0] + 'BUDGET-', 'PARA-01:Original.' + page.split(purposes[0])[1]],
                      [page.replace('Resource1', '')], [page.replace('Budget', '')]]:
            with self.assertRaises(AssertionError): long_page_checks(pages, soup, True)
