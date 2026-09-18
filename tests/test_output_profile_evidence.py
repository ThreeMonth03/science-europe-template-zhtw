import json
from pathlib import Path
import sys
import unittest
from bs4 import BeautifulSoup
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from artifact_utils import sha
from check_output_profiles import checklist, transformed, pdf_marker_projection


class OutputProfileEvidence(unittest.TestCase):
    def test_transform_rejects_missing_or_duplicated_diagnostics(self):
        changes = [('Warning.', '', False), ('Plan,butmissing.', 'Plan.', False)]
        self.assertEqual(transformed('Original.csvWarning.Plan,butmissing.', changes), 'Original.csvPlan.')
        for value in ['Original.csvPlan,butmissing.', 'Warning.Warning.Plan,butmissing.']:
            with self.assertRaises(AssertionError): transformed(value, changes)

    def test_generated_bullet_projection_is_bounded_and_rejects_authored_bullets(self):
        soups = [BeautifulSoup('<p>Keep Original.csv.</p>', 'html.parser')]*2
        values, counts = pdf_marker_projection(['•KeepOriginal.csv.•', 'KeepOriginal.csv.'], soups, '•')
        self.assertEqual(values[0], values[1])
        self.assertEqual(counts[0]['•'], 2)
        for raw in [['•••text', 'text'], ['••text', '◦text']]:
            with self.assertRaises(AssertionError): pdf_marker_projection(raw, soups, '•')
        authored = [BeautifulSoup('<p>• authored text</p>', 'html.parser')]*2
        with self.assertRaises(AssertionError): pdf_marker_projection(['••', ''], authored, '•')

    def test_checklist_excludes_authored_warning_like_markup_and_partial_facts(self):
        soup = BeautifulSoup('<div class="question" id="q"><div class="answer-detail">'
            '<p class="data-gap" data-fact-id="author" data-status="missing">尚待補充：原文</p></div>'
            '<p class="data-gap" data-fact-id="owned" data-status="missing">Owned notice</p>'
            '<p class="quality-summary" data-fact-id="quality-methods" data-status="partial">Plan.</p></div>', 'html.parser')
        self.assertEqual([r['fact'] for r in checklist(soup)], ['owned'])

    def test_native_evidence_is_bound_and_explicitly_partial(self):
        root = ROOT/'reviews/2026-09-18-output-profiles'
        report = json.loads((root/'output-profiles-report.json').read_text())
        self.assertTrue(report['selected_checks_passed'])
        self.assertFalse(report['release_acceptance']); self.assertFalse(report['microsoft_word_acceptance'])
        self.assertEqual(len(report['rows']), 2)
        self.assertEqual(report['checker_sha256'], sha(root/'reproduce/check_output_profiles.py'))
        for row in report['rows']:
            self.assertEqual(row['checklist_items'], 10)
            self.assertEqual(row['remaining_system_diagnostics'], 0)
            for name, digest in row['artifacts'].items():
                if name.endswith('.html'): continue  # Font-embedded originals stay in the runtime directory.
                path = root/name.replace('renders/', 'native/', 1)
                self.assertEqual(sha(path), digest)
        render = json.loads((root/'provenance/missing-info-render-report.json').read_text())
        self.assertTrue(render['all_renders_succeeded']); self.assertEqual(len(render['renders']), 12)
        self.assertEqual({r['reachable_replies'] for r in render['validation']}, {115})
        visual = json.loads((root/'visual-review.json').read_text())
        self.assertFalse(visual['full_document_visual_acceptance'])
        self.assertEqual(len(visual['findings']), 5)
