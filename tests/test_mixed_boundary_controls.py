import copy
from collections import Counter
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / 'reviews/2026-09-18-short-resource-rows/reproduce/english'
sys.path.insert(0, str(ROOT / 'scripts'))
from mixed_row_content import content
from check_mixed_boundary_controls import scope
from prepare_mixed_boundary_controls import cases
from rehearse_profile_pdf import snapshot
from check_word_boundary_content import assess


def fixture(count, long_index):
    header = 'PurposeBudgetFunding'
    heading = '<thead><tr><th>Purpose</th><th>Budget</th><th>Funding</th></tr></thead>'
    paragraphs = [f'MIX-LONG-09-PARA-{n:02d}:keep{n}.' for n in range(1, 61)]
    rows = []; strings = []
    for n in range(count):
        title = 'LONG_RESOURCE' if n == long_index else f'Resource[{n}]'
        purpose = ''.join('<p>' + p + '</p>' for p in paragraphs) if n == long_index else f'<p>Keep{n}.</p>'
        if n == long_index: purpose = '<div class="answer-detail" data-fact-id="resource-justification" data-status="complete">' + purpose + '</div>'
        purpose += '<p>Allocation.</p>'
        rows.append(f'<tr data-item-id="item-{n}"><td><p><strong>{title}</strong></p>{purpose}</td><td><p>100 TWD</p></td><td><p>Institute.</p></td></tr>')
        strings.append(f'{title}Keep{n}.Allocation.100TWDInstitute.')
    source = '<section id="q-required-resources"><table class="resource-table">' + heading + '<tbody>' + ''.join(rows) + '</tbody></table></section>'
    identity = 'LONG_RESOURCE100TWDInstitute.'
    first = 'PREFIX' + header + ''.join(strings[:long_index]) + (header if long_index else '') + identity + ''.join(paragraphs[:30])
    second = header + identity + ''.join(paragraphs[30:]) + 'Allocation.'
    if long_index < count - 1: second += header + ''.join(strings[long_index + 1:])
    return source, [first, second]


class MixedBoundaryTests(unittest.TestCase):
    def test_unresolved_word_paragraphs_are_not_silently_accepted(self):
        result = assess(Counter({'Paragraph.': 2, 'Splitparagraph.': 1}), 'Paragraph.SplitOTHERparagraph.')
        self.assertFalse(result['all_paragraphs_verified'])
        self.assertFalse(result['complete_content_acceptance'] or result['layout_acceptance'])
        self.assertEqual(result['expected_paragraphs'], 3)
        self.assertEqual(result['contiguous_paragraph_occurrences'], 1)
        self.assertEqual(len(result['unresolved_paragraphs']), 2)
        self.assertFalse(assess(Counter({'A': 1}), 'A')['complete_content_acceptance'])

    def test_first_middle_last_and_small_groups_preserve_every_row(self):
        for count, index in [(9, 0), (9, 4), (9, 8), (7, 3), (32, 0)]:
            source, pages = fixture(count, index)
            actual = content(pages, source)
            self.assertEqual(len(actual['rows']), count)
            self.assertEqual(actual['long']['index'], index + 1)
            self.assertEqual(actual['long']['purpose_pages'], [1, 2])
            self.assertEqual(actual['long']['missing_identity_header_pages'], [])
            self.assertTrue(actual['long']['tail_together'])

    def test_cross_column_painting_is_allowed_but_within_cell_order_is_not(self):
        source, pages = fixture(9, 4)
        ordinary = 'Resource[0]Keep0.Allocation.100TWDInstitute.'
        interleaved = ordinary.replace('Allocation.100TWDInstitute.', '100TWDInstitute.Allocation.')
        changed = [pages[0].replace(ordinary, interleaved), pages[1]]
        self.assertEqual(content(changed, source)['canonical'], content(pages, source)['canonical'])
        wrong = [pages[0].replace('Keep0.Allocation.', 'Allocation.Keep0.'), pages[1]]
        with self.assertRaises(AssertionError): content(wrong, source)

    def test_deleted_duplicate_changed_and_wrong_row_text_all_fail(self):
        source, pages = fixture(9, 4)
        variants = [pages[0].replace('Keep0.', ''), pages[0].replace('Keep0.', 'Keep0.Keep0.'),
                    pages[0].replace('Keep0.', 'KEEP0.'), pages[0].replace('Keep0.', 'Keep1.'),
                    pages[0].replace('100TWD', '101TWD', 1)]
        for bad in variants:
            with self.assertRaises(AssertionError): content([bad, pages[1]], source)
        with self.assertRaises(AssertionError):
            content([pages[0], pages[1].replace('MIX-LONG-09-PARA-40:keep40.', '')], source)

    def test_missing_continuation_is_reported_not_silently_accepted(self):
        source, pages = fixture(9, 4)
        full = 'PurposeBudgetFundingLONG_RESOURCE100TWDInstitute.'
        value = content([pages[0], pages[1].removeprefix(full)], source)
        self.assertEqual(value['long']['missing_identity_header_pages'], [2])
        self.assertEqual(value['long']['purpose_pages_without_name'], [2])

    def test_real_jinja_scope_retains_group_and_total_bounds(self):
        for count, index, short, long in [(9, 0, 8, 1), (9, 4, 8, 1), (7, 3, 0, 1), (32, 0, 31, 1), (33, 32, 0, 0)]:
            source, _ = fixture(count, index)
            value = scope(source, FROZEN)
            self.assertEqual(value['resource_count'], count)
            self.assertEqual(len(value['selected_short_ids']), short)
            self.assertEqual(len(value['expanded_long_ids']), long)
            self.assertFalse(value['native_pdf_entry_input'])

    def test_generator_preserves_original_facts_and_adds_only_owned_items(self):
        ids = {k: v for k, v in [('costQUuid', 'costs'), ('costTitleQUuid', 'title'), ('costAmountQUuid', 'amount'),
            ('costDescriptionQUuid', 'purpose'), ('costCurrencyQUuid', 'currency'), ('costCoverQUuid', 'funding'), ('costAllocationQUuid', 'activities')]}
        items = ['item-' + str(n) for n in range(8)]
        base = {'plan.costs': {'type': 'ItemListReply', 'value': items}, 'other': {'type': 'StringReply', 'value': 'Keep EXACT.csv'}}
        for n, item in enumerate(items):
            for field, value in [('title', 'Resource ' + str(n)), ('amount', '0' if n == 1 else '5000'),
                ('purpose', 'Keep original purpose.'), ('currency', 'TWD'), ('funding', 'Institute.'), ('activities', 'FAIR.')]:
                base['plan.costs.' + item + '.' + field] = {'type': 'StringReply', 'value': value}
        long = copy.deepcopy(base)
        long['plan.costs.item-0.purpose']['value'] = '\n\n'.join(f'BUDGET-PARA-{n:02d}: original.' for n in range(1, 61))
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / 'en'; folder.mkdir()
            for name, values in [('budget-many', base), ('budget-long', long)]:
                (folder / (name + '.events.json')).write_text(json.dumps([dict(path=p, value=v) for p, v in values.items()]))
            results = cases(folder, ids)
        for name, expected in [('mixed-bound-32-first', 32), ('mixed-bound-33-last', 33)]:
            replies = results[name]
            self.assertEqual(replies['other'], base['other'])
            self.assertEqual(len(replies['plan.costs']['value']), expected)
            for path, value in base.items():
                if path != 'plan.costs': self.assertEqual(replies[path], value)
            self.assertEqual(replies['plan.costs.item-1.amount']['value'], '0')

    def test_new_oracle_also_rechecks_all_eight_previous_native_pairs(self):
        archive = ROOT / 'reviews/2026-09-21-native-mixed-header'
        for case in ['mixed-long-last', 'mixed-gaps']:
            for profile in ['review', 'submission']:
                for language in ['english', 'chinese']:
                    stem = '-'.join([case, profile, language])
                    pairs = [content(snapshot(archive / phase / 'native' / (stem + '.pdf'))[0],
                        (archive / phase / 'html-input' / (stem + '.html')).read_text()) for phase in ['before', 'after']]
                    self.assertEqual(pairs[0]['canonical'], pairs[1]['canonical'])
                    self.assertFalse(pairs[1]['long']['missing_identity_header_pages'])
                    self.assertTrue(pairs[1]['long']['tail_together'])


if __name__ == '__main__': unittest.main()
