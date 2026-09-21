import copy
from pathlib import Path
import sys
import unittest
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from prepare_header_controls import single_long
from check_header_controls import long_content, blank_space
from preview_word_short_budget import report_name


class HeaderControlTests(unittest.TestCase):
    def test_preview_receipt_names_are_bounded_and_old_names_stay_stable(self):
        self.assertEqual(report_name(['empty-review']), 'word-preview-empty-review.json')
        cases = ['long-name-' + str(n) for n in range(60)]
        self.assertLessEqual(len(report_name(cases).encode()), 240)
        self.assertEqual(report_name(cases), report_name(list(cases)))
        self.assertNotEqual(report_name(cases), report_name(list(reversed(cases))))
        self.assertNotEqual(report_name(cases), report_name(cases[:-1]))

    def test_single_row_fixture_only_removes_the_named_tail(self):
        events = [dict(uuid='u', path='cost', value=dict(value=['first', 'second'])),
                  dict(uuid='v', path='cost.first.answer', value=dict(value='Keep original wording.')),
                  dict(uuid='w', path='cost.second.answer', value=dict(value='Remove only tail.')),
                  dict(uuid='x', path='other', value=dict(value='Keep another question.'))]
        before = copy.deepcopy(events)
        actual = single_long(events, 'cost')
        self.assertEqual(events, before)
        self.assertEqual([e['path'] for e in actual], ['cost', 'cost.first.answer', 'other'])
        self.assertEqual(actual[0]['value']['value'], ['first'])
        self.assertEqual(actual[1]['value'], events[1]['value'])
        self.assertEqual(actual[2]['value'], events[3]['value'])
        self.assertEqual(actual, single_long(events, 'cost'))
        with self.assertRaises(AssertionError): single_long(actual, 'cost')

    def fixture(self):
        paragraphs = [f'BUDGET-PARA-{n:02d}:Original{n}.' for n in range(1, 61)]
        soup = BeautifulSoup('<section id="q-required-resources"><table class="resource-table">'
            '<thead><tr><th>Purpose</th><th>Budget</th><th>Funding</th></tr></thead>'
            '<tbody><tr><td><p>Resource</p><div class="answer-detail">' +
            ''.join('<p>' + v + '</p>' for v in paragraphs) +
            '</div><p>Allocation.</p></td><td>900TWD</td><td>Institute.</td></tr></tbody></table></section>', 'html.parser')
        header = 'PurposeBudgetFundingResource900TWDInstitute.'
        return soup, [header + ''.join(paragraphs[:30]), header + ''.join(paragraphs[30:]) + 'Allocation.']

    def test_long_content_requires_each_full_original_paragraph_once(self):
        soup, pages = self.fixture()
        value = long_content(pages, soup)
        self.assertEqual(value['long_pages'], [1, 2])
        self.assertEqual(value['missing_header_pages'], [])
        self.assertTrue(value['tail_together'])
        for invalid in [pages[:1] + [pages[1].replace('BUDGET-PARA-40:Original40.', '')],
                        pages[:1] + [pages[1] + 'BUDGET-PARA-40:Original40.'],
                        pages[:1] + [pages[1].replace('Original40.', 'Changed40.')]]:
            with self.assertRaises(AssertionError): long_content(invalid, soup)

    def test_header_and_orphan_diagnostics_do_not_change_the_baseline(self):
        soup, pages = self.fixture()
        header = 'PurposeBudgetFundingResource900TWDInstitute.'
        missing = [pages[0], pages[1].removeprefix(header)]
        self.assertEqual(long_content(missing, soup)['missing_header_pages'], [2])
        orphan = [pages[0], pages[1].removesuffix('Allocation.'), 'Allocation.']
        self.assertFalse(long_content(orphan, soup)['tail_together'])

    def test_identical_allocation_in_another_row_cannot_change_long_row_location(self):
        soup, pages = self.fixture()
        tail = BeautifulSoup('<tr><td><p>Tail</p><p>Allocation.</p></td><td><p>0 TWD</p></td><td><p>Other.</p></td></tr>', 'html.parser').tr
        soup.select_one('tbody').append(tail)
        pages.append('PurposeBudgetFundingTailAllocation.0TWDOther.')
        value = long_content(pages, soup)
        self.assertEqual(value['allocation_pages'], [2])
        self.assertEqual(value['short_tail_pages'], [3])
        self.assertTrue(value['tail_together'])

    def test_whitespace_measurement_excludes_only_the_proven_footer(self):
        data = b'<html><page width="595" height="842"><flow><block><line yMin="100"><word yMax="114">Body</word></line><line yMin="800"><word yMax="811">1/1</word></line></block></flow></page></html>'
        value = blank_space(data)
        self.assertEqual(value['last_body_word_bottom_pt'], 114)
        self.assertGreater(value['space_to_bottom_content_margin_pt'], 600)


if __name__ == '__main__': unittest.main()
