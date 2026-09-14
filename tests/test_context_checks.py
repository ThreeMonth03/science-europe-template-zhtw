import sys
import unittest
from pathlib import Path
from bs4 import BeautifulSoup
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_context_outputs import compare_html, joined_paragraphs, check_flow


class ContextChecksTests(unittest.TestCase):
    def pair(self):
        other = ''.join(f'<div class="question" id="q-{i}"><p>Other {i}.</p></div>' for i in range(14))
        context = '<div class="answer-detail" data-fact-id="preservation-dataset-description"><p>Author.csv.</p><p>Second paragraph.</p></div><p data-fact-id="preservation-data-stage">Raw data.</p>'
        policy = '<p>Publish.</p><div class="reading-gap"><p class="data-gap" data-fact-id="retention-period" data-status="missing">Missing.</p></div><p>Metadata.</p>'
        prefix = '<div class="question" id="q-data-preservation"><div class="dataset-section" data-item-id="first">'
        old = other + prefix + '<div class="dataset-policy">' + context + '</div><div class="preservation-summary dataset-policy">' + policy + '</div></div></div>'
        new = other + prefix + '<div class="preservation-summary dataset-policy">' + context + policy + '</div></div></div>'
        return [BeautifulSoup(v, 'html.parser') for v in [old, new]]

    def test_only_structure_changes_with_same_text_facts_and_author_blocks(self):
        old, new = self.pair()
        self.assertEqual(15, compare_html(old, new))
        self.assertEqual(['Rawdata.Publish.', 'Metadata.'], check_flow(new))

    def test_text_state_scope_and_author_paragraph_changes_fail(self):
        for change in ['text', 'state', 'scope', 'author']:
            old, new = self.pair()
            if change == 'text': new.find(id='q-2').p.string = 'Changed.'
            elif change == 'state': new.select_one('.data-gap')['data-status'] = 'complete'
            elif change == 'scope': new.select_one('.dataset-section')['data-item-id'] = 'other'
            else:
                detail = new.select_one('.answer-detail'); detail.clear()
                detail.append(BeautifulSoup('<p>Author.csv.Second paragraph.</p>', 'html.parser'))
            with self.assertRaises(AssertionError): compare_html(old, new)

    def test_only_consecutive_whole_owned_paragraphs_join(self):
        rows = [(t, 'Body', None, None) for t in ['Author.', 'Stage.', 'Publish.', 'Missing.', 'Metadata.']]
        result, reduction = joined_paragraphs(rows, ['Stage.Publish.', 'Metadata.'])
        self.assertEqual(1, reduction)
        self.assertEqual(['Author.', 'Stage.Publish.', 'Missing.', 'Metadata.'], [r[0] for r in result])
        for target in ['Stage.Publish.Metadata.', 'age.Publish.', 'Stage.Changed.']:
            with self.assertRaises(AssertionError): joined_paragraphs(rows, [target])

    def test_different_styles_are_not_silently_flattened(self):
        with self.assertRaises(AssertionError):
            joined_paragraphs([('Stage.', 'Body'), ('Author.', 'Pilot Lead')], ['Stage.Author.'])

    def test_old_split_context_is_rejected(self):
        old, _ = self.pair()
        with self.assertRaises(AssertionError): check_flow(old)
