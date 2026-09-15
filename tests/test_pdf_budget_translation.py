import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from probe_pdf_budget_translation import pair, verify


class PdfBudgetTranslationTests(unittest.TestCase):
    def test_exact_pairs_and_only_two_existing_branch_copies(self):
        currency = ('Currency: {projectCostItemCurrencyReply}.', '幣別：{projectCostItemCurrencyReply}')
        old = [currency, ('Original {x}.', '原句{x}。')]
        verify(old, old + [currency] * 2)
        for new in [old, old + [currency], old + [currency] * 3,
                    [currency, ('Original {x}.', '原句{x}')] + [currency] * 2,
                    [currency, ('Original {x}.', '原句{y}。')] + [currency] * 2]:
            with self.assertRaises(AssertionError): verify(old, new)

    def test_parser_retains_inner_and_outer_translation_spaces(self):
        text = '### Sentence (en)\n\n```text\nOriginal {x}.\n```\n### Translation (zh_Hant)\n\n~~~jinja\n 原句 {x}。 \n~~~'
        self.assertEqual(('Original {x}.', ' 原句 {x}。 '), pair(text))
