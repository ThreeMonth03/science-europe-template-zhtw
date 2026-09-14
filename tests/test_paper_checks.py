import sys
import unittest
from pathlib import Path
from bs4 import BeautifulSoup
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_paper_outputs import check_values, compare_prior


class PaperChecksTests(unittest.TestCase):
    def pair(self):
        other = ''.join(f'<div class="question" id="q-{i}"><p>Other {i}.</p></div>' for i in range(14))
        prefix = '<div class="question" id="q-data-preservation"><div class="dataset-section" data-item-id="one"><h5>Dataset</h5><div class="preservation-summary dataset-policy"><div class="answer-detail"><p>Author.csv.</p><p>Second paragraph.</p></div><p data-fact-id="preservation-data-stage" data-status="complete">Stage.</p>'
        reference = '<p data-fact-id="preservation-related-paper" data-status="complete">Related paper: https://example.org/Paper.csv.</p>'
        tail = '<p>Publish.</p><div class="reading-gap"><p class="data-gap">Missing.</p></div><p>Metadata.</p></div>'
        new_reference = '<div class="paper-reference" data-fact-id="preservation-related-paper" data-status="complete"><p><span class="paper-reference-label">Related paper:</span> <span class="paper-reference-value"><a href="https://example.org/Paper.csv">https://example.org/Paper.csv</a></span></p></div>'
        return [BeautifulSoup(v, 'html.parser') for v in [other + prefix + reference + tail + '</div></div>', other + prefix + tail + new_reference + '</div></div>']]

    def test_only_reference_relocation_and_template_period_removal_allowed(self):
        old, new = self.pair(); before = str(new)
        self.assertEqual(15, compare_prior(old, new, {'one': 'https://example.org/Paper.csv'}, 'english'))
        self.assertEqual(before, str(new))

    def test_value_link_label_and_status_mutations_fail(self):
        for field in ['value', 'link', 'label', 'status']:
            old, new = self.pair()
            if field == 'value': new.select_one('.paper-reference-value a').string = 'https://example.org/Other.csv'
            elif field == 'link': new.select_one('.paper-reference-value a')['href'] = 'https://other.example/'
            elif field == 'label': new.select_one('.paper-reference-label').string = 'Wrong:'
            else: new.select_one('.paper-reference')['data-status'] = 'missing'
            with self.assertRaises(AssertionError): compare_prior(old, new, {'one': 'https://example.org/Paper.csv'}, 'english')

    def test_no_whole_question_or_authored_text_exclusion(self):
        for selector in ['#q-2 p', '.answer-detail p', '.reading-gap p', '[data-fact-id="preservation-data-stage"]']:
            old, new = self.pair(); new.select_one(selector).string = 'Changed.'
            with self.assertRaises(AssertionError): compare_prior(old, new, {'one': 'https://example.org/Paper.csv'}, 'english')

    def test_wrong_placement_and_duplicate_reference_fail(self):
        for kind in ['inside', 'duplicate']:
            _, new = self.pair(); ref = new.select_one('.paper-reference')
            if kind == 'inside': new.select_one('.preservation-summary').append(ref.extract())
            else: ref.insert_after(BeautifulSoup(str(ref), 'html.parser'))
            with self.assertRaises(AssertionError): check_values(new, {'one': 'https://example.org/Paper.csv'}, 'english')

    def test_fixture_table_failure_still_blocks_release(self):
        from run_pilot import TABLE_CASES
        self.assertIn('paper-references', TABLE_CASES)
