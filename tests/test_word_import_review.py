import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / 'reviews/2026-09-17-word-import-layout'


class WordImportReviewTests(unittest.TestCase):
    def test_archive_is_complete_and_checksum_bound(self):
        hashes = json.loads((REVIEW / 'checksums.json').read_text())
        files = {str(p.relative_to(REVIEW)) for p in REVIEW.rglob('*') if p.is_file() and p.name != 'checksums.json'}
        self.assertEqual(set(hashes), files)
        for name, digest in hashes.items():
            self.assertEqual(hashlib.sha256((REVIEW / name).read_bytes()).hexdigest(), digest, name)

    def test_diagnostics_keep_native_failure_and_nonadopted_engine_changes_visible(self):
        reports = {lang: json.loads((REVIEW / 'memory-and-reopen' / lang / 'report.json').read_text()) for lang in ('chinese', 'english')}
        for lang, report in reports.items():
            self.assertTrue(report['completed'])
            self.assertTrue(report['source_unchanged'])
            self.assertTrue(report['all_memory_exports_same_normalized_text'])
            self.assertFalse(report['all_exports_same_normalized_text'])
            self.assertFalse(report['release_acceptance'])
            self.assertEqual(report['unmodified_docx_q5_together'], lang == 'english')
            self.assertEqual(report['saved_policy_copy_q5_together_after_reopen'], lang == 'english')
            native = ROOT / 'reviews/2026-09-17-storage-context-pagination/after/native' / ('metadata-partial-' + lang + '.docx')
            self.assertEqual(report['source_sha256'], hashlib.sha256(native.read_bytes()).hexdigest())
        engine = json.loads((REVIEW / 'engine-comparison/report.json').read_text())
        self.assertTrue(engine['completed'])
        self.assertTrue(engine['native_inputs_unchanged'])
        self.assertFalse(engine['release_acceptance'])
        self.assertEqual(len(engine['rows']), 20)
        for row in engine['rows']:
            self.assertGreater(row['body_paragraphs_retained'], 0)
            self.assertEqual(row['page_delta'], int(row['language'] == 'chinese'))
            self.assertEqual(row['unchanged_normalized_text'], (row['case'], row['language']) != ('budget-long', 'chinese'))


if __name__ == '__main__': unittest.main()
