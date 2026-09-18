import copy
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from build import localize_format_names
from probe_personal_data_translation import verify_output_profile_translation_chain
from probe_pdf_budget_translation import pair
from render import format_uuid, FORMATS, SUBMISSION_FORMATS


class OutputProfileTests(unittest.TestCase):
    def test_profile_selects_a_distinct_format_without_changing_default(self):
        for fmt, uid in FORMATS.items():
            self.assertEqual(format_uuid('review', fmt), uid)
            self.assertEqual(format_uuid('submission', fmt), SUBMISSION_FORMATS[fmt])
            self.assertNotEqual(format_uuid('submission', fmt), uid)
        with self.assertRaises(KeyError): format_uuid('typo', 'pdf')

    def test_labels_do_not_change_format_identity_or_steps(self):
        metadata = {'formats': [{'uuid': 'pdf', 'name': 'PDF', 'steps': [{'name': 'weasyprint'}]}]}
        expected = copy.deepcopy(metadata); expected['formats'][0]['name'] = 'PDF－內部檢核版'
        localize_format_names(metadata, {'pdf': 'PDF－內部檢核版'})
        self.assertEqual(metadata, expected)
        for names in [{'missing': 'text'}, {'pdf': ''}, {'pdf': None}]:
            with self.assertRaises(ValueError): localize_format_names(metadata, names)

    def test_exact_one_sentence_delta_and_no_lost_review_hints(self):
        values = [pair(f.read_text()) for f in (ROOT/'translation/tree').rglob('translation.md')]
        _, chain = verify_output_profile_translation_chain(values)
        self.assertEqual(chain['output_profiles']['retained_units'], 747)
        for mutant in [values[:-1], values + [('extra', '額外')], [(a, b+'。') for a, b in values]]:
            with self.assertRaises(AssertionError): verify_output_profile_translation_chain(mutant)
