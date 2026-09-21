from importlib.resources import files
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'reviews/2026-09-21-submission-notices'
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'experiments/submission-notices')]
from artifact_utils import sha
from notice_recipe import patch, project
from notice_probe import compare, expected
from notice_native import pair


class SubmissionNoticeTests(unittest.TestCase):
    def test_sealed_evidence_and_limits(self):
        self.assertEqual(sha(ARCHIVE / 'checksums.json'), '032adb64eff542ef38ee4edda57da9fbcae9243c142c0bde722f2e26e2474419')
        self.assertEqual(json.loads((ARCHIVE / 'checksums.json').read_text()),
            {str(p.relative_to(ARCHIVE)): sha(p) for p in ARCHIVE.rglob('*') if p.is_file() and p.name != 'checksums.json'})
        report = json.loads((ARCHIVE / 'provenance/native.json').read_text())
        self.assertTrue(report['selected_checks_passed'])
        self.assertFalse(report['global_switch_complete'] or report['release_acceptance'] or report['microsoft_word_acceptance'])
        self.assertEqual(report['checker_sha256'], sha(ARCHIVE / 'reproduce/notice_native.py'))
        structural = json.loads((ARCHIVE / 'provenance/structural.json').read_text())
        self.assertEqual(len(structural['rows']), 264)
        self.assertTrue(all(r['remaining_owned_notices'] == 0 for r in structural['rows']))

    def test_exact_source_patch_and_inverse_preserve_all_other_package_fields(self):
        proof = json.loads((ARCHIVE / 'provenance/package-members.json').read_text())
        for language, count in [('english', 114), ('chinese', 116)]:
            before, after = [json.loads((ARCHIVE / 'package' / (phase + '-' + language + '.json')).read_text()) for phase in ['before', 'after']]
            result, operations = patch(before, language)
            self.assertEqual(result, after)
            self.assertEqual(project(after, operations), before)
            self.assertEqual(sum(o['kind'] == 'marked-notice' for ops in operations.values() for o in ops), count)
            self.assertEqual({k for k in proof[language]['before'] if proof[language]['before'][k] != proof[language]['after'][k]}, {'template/template.json'})
            broken = copy.deepcopy(after)
            name = next(iter(operations)); file = next(f for f in broken['files'] if f['fileName'] == name)
            file['content'] = file['content'].replace("output_profile|default('review')", "output_profile|default('submission')", 1)
            with self.assertRaises(AssertionError): project(broken, operations)

    def test_all_twelve_native_pairs_recompute(self):
        english = next(p for p in [ROOT.parent / 'english', ROOT.parent / 'science-europe-template'] if (p / 'scripts/output_profile_contract.py').is_file())
        sys.path[:0] = [str(english / 'scripts'), str(english / 'tests')]
        from output_profile_contract import expected as partial_projection
        report = json.loads((ARCHIVE / 'provenance/native.json').read_text())
        self.assertEqual(len(report['rows']), 12)
        for row in report['rows']:
            value = pair(ARCHIVE / 'before', ARCHIVE / 'after', row['case'], row['language'], row['profile'], partial_projection, compacted=True)
            stem = '-'.join([row['case'], row['profile'], row['language']])
            proof = json.loads((ARCHIVE / 'after/renders' / (stem + '.html.compact.json')).read_text())
            self.assertEqual(value['artifacts']['html'], proof['compact_html_sha256'])
            value['artifacts']['html'] = proof['original_html_sha256']
            self.assertEqual(json.loads(json.dumps(value)), row)

    def test_authored_warning_and_affirmative_fact_loss_is_rejected(self):
        # Use the original partial-submission fixture as the oracle input.
        source = BeautifulSoup((ARCHIVE / 'before/renders/notice-mixed-english.html').read_text(), 'html.parser')
        english = next(p for p in [ROOT.parent / 'english', ROOT.parent / 'science-europe-template'] if (p / 'scripts/output_profile_contract.py').is_file())
        sys.path[:0] = [str(english / 'scripts'), str(english / 'tests')]
        from output_profile_contract import expected as partial_projection
        old = partial_projection(source, 'english'); new = expected(old, 'english')
        compare(old, new, 'english')
        for selector in ['.answer-detail .data-gap', '[data-fact-id="required-software-list"]', '[data-fact-id="reuse-restrictions"]']:
            broken = copy.deepcopy(new); node = broken.select_one(selector); self.assertIsNotNone(node); node.decompose()
            with self.assertRaises(AssertionError): compare(old, broken, 'english')

    def test_compact_html_is_reversible(self):
        sys.path.insert(0, str(ROOT / 'experiments/mixed-budget-header'))
        from compact import restore_source
        font = files('dsw_document_template_tool').joinpath('resources/fonts/NotoSansTC-Variable.ttf').read_bytes()
        digest = hashlib.sha256(font).hexdigest()
        paths = list(ARCHIVE.glob('*/renders/*.html')); self.assertEqual(len(paths), 18)
        for path in paths:
            proof = json.loads(path.with_suffix('.html.compact.json').read_text())
            self.assertEqual(sha(path), proof['compact_html_sha256'])
            self.assertEqual(hashlib.sha256(restore_source(path.read_bytes(), {digest: font})).hexdigest(), proof['original_html_sha256'])

    def test_quota_failure_retained_and_only_five_owned_templates_cleaned(self):
        failed = json.loads((ARCHIVE / 'failed-quota/missing-info-render-report.json').read_text())
        self.assertFalse(failed['all_renders_succeeded']); self.assertEqual(len(failed['renders']), 1)
        self.assertIn('No space left for this document', (ARCHIVE / 'failed-quota/render-empty-review-english-html.log').read_text())
        for phase, count in [('before', 2), ('failed', 1), ('after', 2)]:
            proof = json.loads((ARCHIVE / 'provenance' / (phase + '-cleanup.json')).read_text())
            self.assertEqual(len(proof['deleted']), count)
            self.assertEqual((proof['project_references'], proof['document_references']), (0, 0))
        life = json.loads((ARCHIVE / 'provenance/lifecycle.json').read_text())
        self.assertTrue(life['stock_worker_restored'])
        self.assertTrue(all(r['status'] == 'exited' for r in life['after']))


if __name__ == '__main__': unittest.main()
