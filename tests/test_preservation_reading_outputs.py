import importlib.util
import json
from pathlib import Path
import sys
import unittest
import zipfile
from bs4 import BeautifulSoup
from docx import Document
from lxml import etree as E

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT/'reviews/2026-09-18-preservation-reading'
sys.path.insert(0, str(ROOT/'scripts'))
from artifact_utils import sha
from check_preservation_reading_outputs import body_xml, style_archive
from check_word_rhythm_outputs import compare_questions
from rehearse_profile_pagination import W, select


def contract():
    spec = importlib.util.spec_from_file_location('frozen_q11_label_contract', ARCHIVE/'reproduce/preservation_reading_contract.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


class PreservationReadingOutputs(unittest.TestCase):
    def test_archive_inventory_and_report_are_bound(self):
        expected = json.loads((ARCHIVE/'checksums.json').read_text())
        self.assertEqual(expected, {str(p.relative_to(ARCHIVE)): sha(p) for p in ARCHIVE.rglob('*')
            if p.is_file() and p.name != 'checksums.json' and '__pycache__' not in p.parts})
        report = json.loads((ARCHIVE/'provenance/native-comparison.json').read_text())
        self.assertTrue(report['selected_checks_passed']); self.assertEqual(len(report['rows']), 12)
        self.assertFalse(report['release_acceptance']); self.assertFalse(report['microsoft_word_acceptance'])
        self.assertEqual(sum(r['merged_word_paragraphs'] for r in report['rows']), 4)
        self.assertEqual(sum(r['question_comparisons'] for r in report['rows']), 180)
        self.assertEqual(report['checker_sha256'], sha(ARCHIVE/'reproduce/check_preservation_reading_outputs.py'))
        self.assertEqual(report['contract_sha256'], sha(ARCHIVE/'reproduce/preservation_reading_contract.py'))
        for row in report['rows']:
            for phase, key in (('before', 'prior_artifact_sha256'), ('after', 'artifact_sha256')):
                for name, digest in row[key].items():
                    if name.endswith('.html'):
                        path = ARCHIVE/phase/'question-content'/Path(name).name
                        self.assertEqual(path.read_text().splitlines()[0], '<!-- Native HTML SHA256: '+digest+' -->')
                    else:
                        self.assertEqual(sha(ARCHIVE/phase/name.replace('renders/', 'native/', 1)), digest)

    def test_native_word_delta_and_html_are_exact_for_all_twelve_pairs(self):
        oracle = contract()
        for path in sorted((ARCHIVE/'after/native').glob('*.docx')):
            with self.subTest(name=path.name):
                before = ARCHIVE/'before/native'/path.name
                docs = [Document(p) for p in (before, path)]; anchors = []
                if path.name.startswith('profile-partial-'):
                    _, label, _ = select(docs[0].element)
                    anchors = [label.getprevious().get(W+'name')]
                oracle.word_content(*[body_xml(d) for d in docs], anchors)
                with zipfile.ZipFile(before) as old, zipfile.ZipFile(path) as new:
                    oracle.prior_reference(*[style_archive(z.read('word/styles.xml')) for z in (old, new)])
                soups = [BeautifulSoup((ARCHIVE/phase/'question-content'/path.with_suffix('.html').name).read_text(), 'html.parser')
                         for phase in ('before', 'after')]
                self.assertEqual(compare_questions(*soups), 15)

    def test_oracle_rejects_unrelated_word_changes(self):
        name = 'profile-partial-submission-chinese.docx'
        docs = [Document(ARCHIVE/phase/'native'/name) for phase in ('before', 'after')]
        _, label, _ = select(docs[0].element); anchors = [label.getprevious().get(W+'name')]
        old, new = [body_xml(d) for d in docs]; oracle = contract()
        for mutation in ('text', 'font', 'bookmark', 'table', 'question-heading'):
            with self.subTest(mutation=mutation):
                root = E.fromstring(new)
                if mutation == 'text': next(root.iter(W+'t')).text = 'Unexpected answer replacement'
                elif mutation == 'font': next(root.iter(W+'rPr')).append(E.Element(W+'sz', {W+'val': '8'}))
                elif mutation == 'bookmark':
                    mark = next(root.iter(W+'bookmarkStart')); mark.getparent().remove(mark)
                elif mutation == 'table': next(root.iter(W+'gridCol')).set(W+'w', '1')
                else:
                    node = next(p for p in root.iter(W+'pStyle') if p.get(W+'val') == 'Heading3')
                    node.set(W+'val', 'BodyText')
                with self.assertRaises(AssertionError): oracle.word_content(old, E.tostring(root), anchors)

    def test_fix_and_unchanged_controls_are_reported_separately(self):
        report = json.loads((ARCHIVE/'provenance/native-comparison.json').read_text())
        for row in report['rows']:
            self.assertTrue(row['passed'])
            if row['case'] == 'profile-partial':
                self.assertEqual(len(set(row['q11_heading_summary_pages'])), 1)
                if (row['language'], row['profile']) == ('chinese', 'submission'):
                    self.assertEqual(row['prior_q11_heading_summary_pages'], [4, 5])
                    self.assertEqual(row['q11_heading_summary_pages'], [5, 5])
            else:
                self.assertEqual(row['merged_word_paragraphs'], 0)
                self.assertEqual(row['word_changed_body_geometry_pages'], [])
        manifest = json.loads((ARCHIVE/'provenance/candidate-manifest.json').read_text())
        self.assertEqual(manifest['status'], 'candidate')
        self.assertEqual(manifest['translation_units'], 748)
        self.assertFalse(any(v['dirty'] for v in manifest['checkouts'].values()))
        failure = json.loads((ARCHIVE/'diagnostics-quota/missing-info-render-report.json').read_text())
        self.assertFalse(failure['all_renders_succeeded'])
        self.assertEqual(len(failure['renders']), 1)


if __name__ == '__main__': unittest.main()
