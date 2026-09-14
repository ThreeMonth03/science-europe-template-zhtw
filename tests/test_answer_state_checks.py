import sys
import unittest
from pathlib import Path
from bs4 import BeautifulSoup
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_answer_state_outputs import compare_prior, LEAD, OLD_LEAD, SUPPORT


class AnswerStateCheckTests(unittest.TestCase):
    def pair(self):
        old = ''.join(f'<div class="question" id="q-{i}"><p>Original {i}.</p></div>' for i in range(13))
        old += f'<div class="question" id="q-store-backup"><div class="storage-detail-limits"><p>{OLD_LEAD["english"]}</p><ul><li>Exact location unknown.</li></ul></div></div>'
        old += '<div class="question" id="q-data-preservation"><ul><li>Special repository. Service.</li></ul><div class="answer-detail"><p>Author-2027-12-31.csv.</p></div></div>'
        new = old.replace(OLD_LEAD['english'], LEAD['english']).replace('<li>Special repository. Service.</li>',
            '<li class="repository-distribution" data-item-id="a">Special repository. <span data-requirement-id="SE-5b" data-fact-id="repository-long-term-support" data-status="missing">' + SUPPORT['english']['missing'] + '</span> Service.</li>')
        return BeautifulSoup(old, 'html.parser'), BeautifulSoup(new, 'html.parser')

    def test_only_bounded_changes_pass_without_mutating_input(self):
        a, b = self.pair(); original = str(b)
        self.assertEqual(15, compare_prior(a, b, 'english'))
        self.assertEqual(original, str(b))

    def test_rejects_other_text_structure_and_authored_changes(self):
        for selector in ['#q-2 p', '.answer-detail p', '.storage-detail-limits li']:
            a, b = self.pair(); b.select_one(selector).string = 'Rewritten.'
            with self.assertRaises(AssertionError): compare_prior(a, b, 'english')
        a, b = self.pair(); b.select_one('#q-2 p').name = 'h4'
        with self.assertRaises(AssertionError): compare_prior(a, b, 'english')

    def test_rejects_wrong_support_text_or_scope(self):
        for change in ['text', 'status', 'parent']:
            a, b = self.pair(); n = b.select_one('[data-fact-id="repository-long-term-support"]')
            if change == 'text': n.string = 'Will be funded for ten years.'
            elif change == 'status': n['data-status'] = 'explicit-no'
            else: n.parent.name = 'p'
            with self.assertRaises(AssertionError): compare_prior(a, b, 'english')

    def test_support_mixed_is_a_known_table_case(self):
        from run_pilot import TABLE_CASES
        self.assertIn('support-mixed', TABLE_CASES)
