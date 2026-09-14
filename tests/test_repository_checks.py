import sys
import unittest
from pathlib import Path
from bs4 import BeautifulSoup
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_repository_outputs import compare_prior, scoped_pages, OLD_LEAD, LEAD


class RepositoryChecksTests(unittest.TestCase):
    def pair(self):
        old = ''.join(f'<div class="question" id="q-{i}"><p>Original {i}.</p></div>' for i in range(14))
        rows = ''.join(f'<li class="repository-distribution" data-item-id="r{i}">Repository-{i}.<span data-fact-id="repository-long-term-support" data-status="complete">Support.</span></li>' for i in range(1, 4))
        unit = f'<div class="answer-lead"><p>{OLD_LEAD["english"]}</p></div><ul>{rows}</ul>'
        old += f'<div class="question" id="q-data-preservation">{unit}<div class="answer-detail"><p>Authored.csv</p></div></div>'
        new_unit = unit.replace(OLD_LEAD['english'], LEAD['english'])
        for i in range(1, 4):
            new_unit = new_unit.replace(f'>Repository-{i}.', f'><span class="repository-label"><strong>Distribution {i}:</strong></span>Repository-{i}.')
        new = old.replace(unit, '<div class="repository-destinations short-repository-list">' + new_unit + '</div>')
        return BeautifulSoup(old, 'html.parser'), BeautifulSoup(new, 'html.parser')

    def test_only_expected_label_lead_wrapper_changes_pass(self):
        a, b = self.pair(); value = str(b)
        self.assertEqual(15, compare_prior(a, b, 'english'))
        self.assertEqual(value, str(b))

    def test_wrong_number_lost_answer_and_other_question_changes_fail(self):
        for selector in ['.repository-label strong', '[data-fact-id]', '.answer-detail p', '#q-2 p']:
            a, b = self.pair(); b.select_one(selector).string = 'Changed.'
            with self.assertRaises(AssertionError): compare_prior(a, b, 'english')
        a, b = self.pair(); b.select_one('.repository-distribution')['data-item-id'] = 'wrong-row'
        with self.assertRaises(AssertionError): compare_prior(a, b, 'english')

    def test_question_scope_excludes_same_labels_in_q10_and_q12(self):
        self.assertEqual({2: 'One', 3: 'Two'}, scoped_pages('Q10 One\fQ11 One\fTwo Q12 One', 'Q11', 'Q12'))
        for text in ['Q10 One Q12', 'Q11 One Q11 Two Q12', 'Q11 One']:
            with self.assertRaises(AssertionError): scoped_pages(text, 'Q11', 'Q12')

    def test_new_cases_keep_stock_table_gate(self):
        from run_pilot import TABLE_CASES
        self.assertTrue({'repository-gap', 'repository-long'} <= TABLE_CASES)
