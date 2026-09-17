import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from artifact_utils import sha
from check_metadata_gap_panel_outputs import CASES
REVIEW = ROOT / 'reviews/2026-09-17-metadata-gap-panel'


class MetadataGapPanelReviewTests(unittest.TestCase):
    def test_archive_hashes_bind_native_files_receipts_and_checker(self):
        hashes = json.loads((REVIEW / 'checksums.json').read_text())
        files = {str(p.relative_to(REVIEW)) for p in REVIEW.rglob('*') if p.is_file() and p.name != 'checksums.json'}
        self.assertEqual(set(hashes), files)
        for name, digest in hashes.items():
            self.assertEqual(sha(REVIEW / name), digest, name)
        report = json.loads((REVIEW / 'metadata-gap-panel-report.json').read_text())
        self.assertEqual(report['checker_sha256'], sha(REVIEW / 'reproduce/check_metadata_gap_panel_outputs.py'))
        self.assertTrue(report['selected_checks_passed'])
        self.assertFalse(report['release_acceptance'])
        self.assertEqual(len(report['rows']), 10)
        self.assertEqual({(r['case'], r['language']) for r in report['rows']}, {(c, l) for c in CASES for l in ('english', 'chinese')})
        for row in report['rows']:
            stem = row['case'] + '-' + row['language']
            self.assertTrue(row['passed'] and row['unchanged_word'])
            self.assertFalse(row['errors'] or row['reading_issues'])
            self.assertEqual(row['pages'], row['prior_pages'])
            self.assertEqual(row['word_pages'], row['prior_word_pages'])
            self.assertEqual(row['selected'], row['case'] == 'metadata-partial')
            for fmt in ('pdf', 'docx'):
                self.assertEqual(row['after_sha256']['renders/' + stem + '.' + fmt], sha(REVIEW / 'native' / (stem + '.' + fmt)))
            for fmt in ('html', 'pdf', 'docx'):
                name = stem + '.' + fmt + '.fixture.json'
                self.assertEqual(row['after_sha256']['renders/' + name], sha(REVIEW / 'native' / name))
                receipt = json.loads((REVIEW / 'native' / name).read_text())
                self.assertEqual(receipt['package_sha256'], report['package_sha256'][row['language'] + '.zip'])
                self.assertEqual(receipt['timeout_seconds'], 600)
                self.assertEqual(receipt['runner_sha256'], sha(REVIEW / 'reproduce/render.py'))
            self.assertEqual(row['after_sha256']['word-preview/' + stem + '.pdf'], sha(REVIEW / 'word-preview' / (stem + '.pdf')))
            if row['selected']:
                geometry = row['pair_geometry']
                self.assertLess(geometry['after_span_pt'], geometry['before_span_pt'])
        for name in ('candidate-manifest.json', 'rebuild-manifest.json'):
            manifest = json.loads((REVIEW / name).read_text())
            self.assertEqual({key: manifest['sha256'][key] for key in report['package_sha256']}, report['package_sha256'])
            self.assertFalse(any(v['dirty'] for v in manifest['checkouts'].values()))

    def test_failed_attempt_and_checker_bug_remain_separate_from_acceptance(self):
        failure = json.loads((REVIEW / 'failed-attempt/runtime-failure.json').read_text())
        self.assertFalse(failure['passed'])
        self.assertEqual(failure['successful_renders'], 17)
        self.assertEqual(failure['render_report_sha256'], sha(REVIEW / 'failed-attempt/missing-info-render-report.json'))
        self.assertEqual(failure['original_render_runner_sha256'], sha(REVIEW / 'failed-attempt/render-original.py'))
        self.assertEqual(failure['worker_end_state']['ExitCode'], 2)
        self.assertFalse(failure['worker_end_state']['OOMKilled'])
        cleanup = json.loads((REVIEW / 'failed-attempt/owned-test-template-cleanup.json').read_text())
        self.assertTrue(cleanup['failed_run_explicitly_acknowledged'])
        self.assertFalse(cleanup['run_completed_successfully'])
        correction = json.loads((REVIEW / 'checker-correction/report.json').read_text())
        self.assertFalse(correction['selected_checks_passed'])
        self.assertEqual(correction['checker_sha256'], sha(REVIEW / 'checker-correction/check_metadata_gap_panel_outputs.py'))
        renders = json.loads((REVIEW / 'missing-info-render-report.json').read_text())
        self.assertTrue(renders['all_renders_succeeded'])
        self.assertEqual(len(renders['renders']), 30)
        lifecycle = json.loads((REVIEW / 'worker-lifecycle.json').read_text())
        self.assertTrue(lifecycle['same_worker_before_and_after'])
        self.assertEqual(lifecycle['before'], lifecycle['after'])
        self.assertEqual(lifecycle['before'], json.loads((REVIEW / 'worker-start.json').read_text()))
        pixels = json.loads((REVIEW / 'unchanged-control-pixels.json').read_text())
        self.assertTrue(pixels['passed'])
        self.assertEqual(len(pixels['rows']), 8)
        self.assertEqual(pixels['identical_body_pages'], 18)
