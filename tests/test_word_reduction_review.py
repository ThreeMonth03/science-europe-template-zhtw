import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from diagnose_word_import_layout import sha
REVIEW = ROOT / 'reviews/2026-09-17-word-layout-reduction'


class WordReductionReviewTests(unittest.TestCase):
    def test_archive_is_complete_and_checksum_bound(self):
        hashes = json.loads((REVIEW / 'checksums.json').read_text())
        files = {str(p.relative_to(REVIEW)) for p in REVIEW.rglob('*') if p.is_file() and p.name != 'checksums.json'}
        self.assertEqual(set(hashes), files)
        for name, digest in hashes.items():
            self.assertEqual(sha(REVIEW / name), digest, name)

    def test_reduced_case_retains_failure_and_source_provenance(self):
        report = json.loads((REVIEW / 'reduced/report.json').read_text())
        self.assertTrue(report['completed'])
        self.assertTrue(report['diagnostic_not_native'])
        self.assertFalse(report['release_acceptance'])
        self.assertEqual(report['script_sha256'], sha(REVIEW / 'reproduce/reduce_word_layout_case.py'))
        self.assertEqual(report['helper_sha256'], sha(REVIEW / 'reproduce/diagnose_word_import_layout.py'))
        self.assertEqual([r['language'] for r in report['rows']], ['chinese', 'english'])
        for row in report['rows']:
            lang = row['language']
            for key in ('source_unchanged', 'kept_paragraph_table_xml_unchanged',
                        'reproduces_native_q5_pagination', 'pre_q5_line_geometry_unchanged'):
                self.assertTrue(row[key], key)
            self.assertEqual(row['retained_body_blocks'], 53)
            self.assertEqual(row['before']['pages'], 6)
            self.assertEqual(row['after']['pages'], 4 if lang == 'chinese' else 3)
            expected = [[3], [3], [4], [4], [4]] if lang == 'chinese' else [[3]] * 5
            for phase in ('before', 'after'):
                self.assertEqual(row[phase]['q5_paragraph_page_spans'], expected)
                self.assertEqual(row[phase]['q5_together'], lang == 'english')
            baseline = ROOT / 'reviews/2026-09-17-storage-context-pagination/after'
            self.assertEqual(sha(baseline / 'native' / f'metadata-partial-{lang}.docx'), row['source_sha256'])
            self.assertEqual(sha(baseline / 'word-preview' / f'metadata-partial-{lang}.pdf'), row['before']['pdf_sha256'])
            self.assertEqual(sha(REVIEW / 'reduced' / f'reduced-{lang}.docx'), row['docx_sha256'])
            self.assertEqual(sha(REVIEW / 'reduced' / f'reduced-{lang}.pdf'), row['after']['pdf_sha256'])


if __name__ == '__main__': unittest.main()
