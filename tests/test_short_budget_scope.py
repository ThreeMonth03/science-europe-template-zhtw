import sys
import unittest
from unittest.mock import patch
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from probe_short_budget_scope import prior_helper
from check_short_budget_outputs import question_pages, prompt_lines


class ShortBudgetScopeTests(unittest.TestCase):
    def test_only_inserted_macro_and_call_are_removed(self):
        before = 'original-prefix\n{%- macro ordinary(header, rows) -%}\n{{ original }}tail'
        after = before.replace('{%- macro ordinary', '{%- macro short_table(original, rows) -%}\nnew hint\n{%- macro ordinary').replace('{{ original }}', '{{ short_table(original, rows) }}')
        self.assertEqual(prior_helper(after), before)
        self.assertNotEqual(prior_helper(after.replace('tail', 'unrelated change')), before)

    def test_unknown_or_duplicate_helper_is_rejected(self):
        for source in ['', '{%- macro short_table(original, rows) -%}'*2]:
            with self.assertRaises(AssertionError): prior_helper(source)

    def test_body_comparison_retains_all_punctuation(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup('<div class="question"><h3>1. Question?</h3></div>', 'html.parser')
        self.assertEqual(question_pages(['cover', 'metadata1.Question?Answer.', 'Next。'], soup), ['Answer.', 'Next。'])

    def test_prompt_lines_can_span_separate_poppler_blocks(self):
        data = b'<doc><page><block><line yMin="10" xMin="100">Information</line></block><block><line yMin="11" xMin="200">Other column</line></block><block><line yMin="25" xMin="100">not</line></block><block><line yMin="40" xMin="100">provided:</line></block><block><line yMin="55" xMin="100">currency.</line></block></page></doc>'
        with patch('check_short_budget_outputs.subprocess.check_output', return_value=data):
            self.assertEqual(prompt_lines(Path('fake.pdf'), 'Information not provided: currency.'), {'page': 1, 'line_count': 4})
            with self.assertRaises(AssertionError): prompt_lines(Path('fake.pdf'), 'Information not provided: amount.')
