import copy
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from build import build, localize_format_names, select_tdk, set_template_language, tdk_provenance
from probe_personal_data_translation import CURRENT_POLISH, verify_submission_translation_chain
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

    def test_descriptor_languages_preserve_identity_and_formats(self):
        original = {'organizationId': 'example', 'templateId': 'dmp', 'version': '0.3.78',
                    'formats': [{'uuid': 'pdf', 'name': 'PDF', 'steps': [{'name': 'weasyprint'}]}]}
        for language in ('en', 'zh-Hant'):
            metadata = copy.deepcopy(original)
            set_template_language(metadata, language)
            expected = copy.deepcopy(original); expected['language'] = language
            self.assertEqual(metadata, expected)
        with self.assertRaises(ValueError): set_template_language(copy.deepcopy(original), 'zh_Hant')

    def test_tdk_override_records_the_actual_cli_without_changing_default(self):
        tooling = Path('/tmp/locked-tool')
        self.assertEqual(select_tdk(tooling), tooling / '.venv/bin/dsw-tdk')
        isolated = Path('/tmp/isolated-435/bin/dsw-tdk')
        self.assertEqual(select_tdk(tooling, isolated), isolated)
        with self.assertRaisesRegex(ValueError, 'preview-only'):
            build(SimpleNamespace(tdk=isolated, preview=False))
        with patch('build.subprocess.check_output', return_value='dsw-tdk, version 4.35.0\n') as command:
            self.assertEqual(tdk_provenance(isolated), {'executable': str(isolated), 'version': '4.35.0'})
            command.assert_called_once_with([str(isolated), '--version'], text=True)
        with patch('build.subprocess.check_output', return_value='unidentified CLI'):
            with self.assertRaises(ValueError): tdk_provenance(isolated)

    def test_exact_one_sentence_delta_and_no_lost_review_hints(self):
        values = [pair(f.read_text()) for f in (ROOT/'translation/tree').rglob('translation.md')]
        _, chain = verify_submission_translation_chain(values)
        self.assertEqual(chain['current_language_polish'], CURRENT_POLISH)
        self.assertEqual(chain['current_language_polish']['baseline_units'], 775)
        self.assertEqual(chain['output_profiles']['retained_units'], 747)
        for mutant in [values[:-1], values + [('extra', '額外')], [(a, b+'。') for a, b in values]]:
            with self.assertRaises(AssertionError): verify_submission_translation_chain(mutant)
