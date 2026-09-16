import copy
import json
from pathlib import Path
import sys
import unittest
import zipfile
from lxml import etree as E

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from rehearse_budget_tail import PROFILES, NS, q, select, transform, validate_change
from artifact_utils import sha


def fixture(chinese=False):
    title = '資料管理預算' if chinese else 'Data-management budget'
    header = '資源項目與用途' if chinese else 'Resource and purpose'
    return E.fromstring(('''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>
      <w:p><w:r><w:t>14. Previous</w:t></w:r></w:p>
      <w:p><w:pPr><w:pStyle w:val="Heading3"/></w:pPr><w:r><w:t>15. Resources</w:t></w:r></w:p>
      <w:p><w:r><w:t>Overview with 0 TWD.</w:t></w:r></w:p>
      <w:p><w:pPr><w:pStyle w:val="Heading4"/></w:pPr><w:r><w:t>''' + title + '''</w:t></w:r></w:p>
      <w:tbl><w:tblGrid><w:gridCol w:w="3880"/><w:gridCol w:w="1980"/><w:gridCol w:w="2059"/></w:tblGrid>
      <w:tr><w:tc><w:p><w:r><w:t>''' + header + '''</w:t></w:r></w:p></w:tc></w:tr>
      <w:tr><w:tc><w:p><w:pPr><w:pStyle w:val="PilotLabel"/></w:pPr><w:r><w:t>Resource</w:t></w:r></w:p>
      <w:p><w:r><w:t>Purpose.</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
      </w:body></w:document>''').encode())


class BudgetTailTrials(unittest.TestCase):
    def test_frozen_counterexamples_and_checksums(self):
        archive = ROOT / 'reviews/2026-09-16-word-budget-tail'
        checksums = json.loads((archive / 'checksums.json').read_text())
        actual = {str(f.relative_to(archive)): sha(f) for f in archive.rglob('*')
                  if f.is_file() and f.name != 'checksums.json'}
        self.assertEqual(checksums, actual)
        report = json.loads((archive / 'trials/report.json').read_text())
        self.assertTrue(report['completed'])
        self.assertEqual(len(report['rows']), 24)
        for row in report['rows']:
            stem = row['case'] + '-' + row['language']
            source = archive / 'native-source' / (stem + '.docx')
            trial = archive / 'trials' / (stem + '-' + row['profile'] + '.docx')
            self.assertEqual(sha(source), row['source_sha256'])
            self.assertEqual(sha(trial), row['docx_sha256'])
            self.assertEqual(sha(trial.with_suffix('.pdf')), row['preview_sha256'])
            with zipfile.ZipFile(source) as before, zipfile.ZipFile(trial) as after:
                self.assertEqual(set(before.namelist()), set(after.namelist()))
                for name in before.namelist():
                    if name != 'word/document.xml':
                        self.assertEqual(before.read(name), after.read(name))
                validate_change(E.fromstring(before.read('word/document.xml')),
                                E.fromstring(after.read('word/document.xml')), row['profile'])
        mixed = {r['profile']: r for r in report['rows']
                 if r['case'] == 'budget-mixed-gaps' and r['language'] == 'chinese'}
        self.assertEqual(mixed['release-budget-heading']['anchors']['budget_heading'], [7])
        self.assertEqual(mixed['release-budget-heading']['anchors']['resource_1'], [8])
        self.assertEqual(mixed['release-table-labels']['anchors']['resource_1'], [7])
        self.assertEqual(mixed['release-table-labels']['anchors']['resource_1_end'], [8])
        self.assertTrue(all(pages == [8] for pages in mixed['keep-overview']['anchors'].values()))

    def test_all_profiles_restore_exactly_in_both_languages(self):
        for chinese in [False, True]:
            source = fixture(chinese)
            frozen = E.tostring(source)
            for profile, expected in zip(PROFILES, [0, 1, 1, 3]):
                with self.subTest(chinese=chinese, profile=profile):
                    result, edits = transform(source, profile)
                    self.assertEqual(edits, expected)
                    self.assertEqual(E.tostring(source), frozen)
                    validate_change(source, result, profile)

    def test_rejects_text_grid_and_unrelated_keep_edits(self):
        source = fixture()
        for profile in PROFILES:
            after, _ = transform(source, profile)
            for kind in ['text', 'grid', 'other-keep', 'font', 'missing-content']:
                with self.subTest(profile=profile, kind=kind):
                    changed = copy.deepcopy(after)
                    if kind == 'text':
                        changed.find('.//w:t', NS).text = 'Changed answer'
                    elif kind == 'grid':
                        changed.find('.//w:gridCol', NS).set(q('w'), '3881')
                    elif kind == 'other-keep':
                        p = changed.find('w:body/w:p', NS)
                        props = E.SubElement(p, q('pPr'))
                        E.SubElement(props, q('keepNext'), {q('val'): '0'})
                    elif kind == 'font':
                        run = changed.find('.//w:r', NS)
                        E.SubElement(E.SubElement(run, q('rPr')), q('sz'), {q('val'): '18'})
                    else:
                        p = changed.find('.//w:tbl/w:tr/w:tc/w:p', NS)
                        p.getparent().remove(p)
                    with self.assertRaises(AssertionError):
                        validate_change(source, changed, profile)

    def test_rejects_ambiguous_question_and_unreviewed_heading(self):
        for case in ['duplicate', 'heading']:
            source = fixture()
            _, leading = select(source)
            if case == 'duplicate':
                source.find(q('body')).insert(0, copy.deepcopy(leading[0]))
            else:
                leading[-1].find('.//w:t', NS).text = 'Unknown budget'
            with self.assertRaises(AssertionError):
                transform(source, 'keep-overview')

    def test_rejects_duplicate_or_wrong_keep_value(self):
        source = fixture()
        for kind in ['duplicate', 'wrong-value']:
            after, _ = transform(source, 'keep-overview')
            _, leading = select(after)
            props = leading[1].find(q('pPr'))
            if kind == 'duplicate':
                E.SubElement(props, q('keepNext'), {q('val'): '1'})
            else:
                props.find(q('keepNext')).set(q('val'), '0')
            with self.assertRaises(AssertionError):
                validate_change(source, after, 'keep-overview')


if __name__ == '__main__':
    unittest.main()
