import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from artifact_utils import sha
REVIEW = ROOT / 'reviews/2026-09-17-q5-word-join'


class Q5WordJoinReviewTests(unittest.TestCase):
    def test_archive_checksums_and_native_receipts_are_bound(self):
        hashes = json.loads((REVIEW / 'checksums.json').read_text())
        files = {str(p.relative_to(REVIEW)) for p in REVIEW.rglob('*') if p.is_file() and p.name != 'checksums.json'}
        self.assertEqual(set(hashes), files)
        for name, digest in hashes.items(): self.assertEqual(sha(REVIEW / name), digest, name)
        report = json.loads((REVIEW / 'q5-word-join-report.json').read_text())
        self.assertEqual(report['checker_sha256'], sha(REVIEW / 'reproduce/check_q5_word_join_outputs.py'))
        self.assertEqual(report['word_contract_sha256'], sha(REVIEW / 'reproduce/q5_word_join_contract.py'))
        for row in report['rows']:
            stem = row['case'] + '-' + row['language']
            for fmt in ('pdf', 'docx'):
                name = stem + '.' + fmt
                self.assertEqual(row['after_sha256']['renders/' + name], sha(REVIEW / 'native' / name))
            for fmt in ('html', 'pdf', 'docx'):
                name = stem + '.' + fmt + '.fixture.json'
                self.assertEqual(row['after_sha256']['renders/' + name], sha(REVIEW / 'native' / name))
                receipt = json.loads((REVIEW / 'native' / name).read_text())
                self.assertEqual(receipt['package_sha256'], report['package_sha256'][row['language'] + '.zip'])
            self.assertEqual(row['after_sha256']['word-preview/' + stem + '.pdf'], sha(REVIEW / 'word-preview' / (stem + '.pdf')))

    def test_native_fix_is_separate_from_historic_failure_and_release(self):
        report = json.loads((REVIEW / 'q5-word-join-report.json').read_text())
        self.assertTrue(report['selected_checks_passed'])
        self.assertFalse(report['release_acceptance'])
        self.assertEqual(len(report['rows']), 20)
        self.assertEqual(sum(r['joined_pairs'] for r in report['rows']), 10)
        for row in report['rows']:
            self.assertTrue(row['passed'])
            self.assertFalse(row['errors'])
            self.assertFalse(row['reading_issues'])
            self.assertEqual(row['pages'], row['prior_pages'])
            self.assertLessEqual(row['word_pages'], row['prior_word_pages'])
            if row['selected']:
                self.assertTrue(row['pre_q5_word_geometry_unchanged'])
                self.assertEqual(len(set(row['q5_locations']['word']['after'])), 1)
        chinese = next(r for r in report['rows'] if (r['case'], r['language']) == ('metadata-partial', 'chinese'))
        self.assertEqual(chinese['q5_locations']['word'], dict(before=[3, 3, 4, 4, 4], after=[4] * 5))
        old = json.loads((ROOT / 'reviews/2026-09-17-storage-context-pagination/after/storage-context-report.json').read_text())
        self.assertFalse(old['pagination_checks_passed'])
        pixels = json.loads((REVIEW / 'q5-word-join-pixels.json').read_text())
        self.assertTrue(pixels['passed'])
        self.assertEqual(len(pixels['rows']), 30)
        expected = {(r['case'], r['language'], 'renders') for r in report['rows']}
        expected |= {(r['case'], r['language'], 'word-preview') for r in report['rows'] if not r['selected']}
        self.assertEqual({(r['case'], r['language'], r['format']) for r in pixels['rows']}, expected)
        for name in ('candidate-manifest.json', 'rebuild-manifest.json'):
            manifest = json.loads((REVIEW / name).read_text())
            self.assertEqual({key: manifest['sha256'][key] for key in report['package_sha256']}, report['package_sha256'])
            self.assertEqual(manifest['untranslated_units'], [])
            self.assertEqual(manifest['source']['version'], '0.3.35')
            self.assertFalse(any(v['dirty'] for v in manifest['checkouts'].values()))


if __name__ == '__main__': unittest.main()
