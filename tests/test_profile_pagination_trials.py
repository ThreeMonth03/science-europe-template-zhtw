import copy
import json
from pathlib import Path
import sys
import unittest
import zipfile

from lxml import etree as E

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from artifact_utils import sha
from rehearse_profile_pagination import W, PROFILES, select, text, transform, validate_change, c14n
from rehearse_profile_pdf import prefix_geometry


def source():
    path = ROOT/'reviews/2026-09-18-output-profiles/native/profile-partial-submission-chinese.docx'
    with zipfile.ZipFile(path) as archive:
        return [E.fromstring(archive.read(n)) for n in ('word/document.xml', 'word/styles.xml')]


class ProfilePaginationTrials(unittest.TestCase):
    def test_every_trial_is_local_and_preserves_all_text(self):
        for path in (ROOT/'reviews/2026-09-18-output-profiles/native').glob('*.docx'):
            with zipfile.ZipFile(path) as archive:
                doc, styles = [E.fromstring(archive.read(n)) for n in ('word/document.xml', 'word/styles.xml')]
            frozen = c14n(doc), c14n(styles)
            for mode in PROFILES:
                with self.subTest(file=path.name, mode=mode):
                    after, revised = transform(doc, styles, mode)
                    validate_change(doc, styles, after, revised, mode)
                    self.assertEqual(frozen, (c14n(doc), c14n(styles)))
                    self.assertEqual([n.text for n in doc.iter(W+'t')], [n.text for n in after.iter(W+'t')])

    def test_oracle_rejects_unrelated_content_format_and_style_changes(self):
        doc, styles = source()
        for mode in PROFILES:
            for mutation in ('text', 'font', 'table', 'style', 'keep'):
                with self.subTest(mode=mode, mutation=mutation):
                    after, revised = transform(doc, styles, mode)
                    if mutation == 'text': next(after.iter(W+'t')).text = 'Lost author text'
                    elif mutation == 'font':
                        run = next(after.iter(W+'r'))
                        props = run.find(W+'rPr')
                        if props is None: props = E.SubElement(run, W+'rPr')
                        E.SubElement(props, W+'sz', {W+'val': '8'})
                    elif mutation == 'table': next(after.iter(W+'gridCol')).set(W+'w', '1')
                    elif mutation == 'style': revised[0].set('unexpected', 'true')
                    else:
                        para = after.find(W+'body/'+W+'p')
                        props = para.find(W+'pPr')
                        if props is None: props = E.SubElement(para, W+'pPr')
                        E.SubElement(props, W+'keepNext', {W+'val': '0'})
                    with self.assertRaises(AssertionError): validate_change(doc, styles, after, revised, mode)

    def test_merged_label_has_explicit_semantic_tradeoff(self):
        doc, styles = source(); heading, label, summary = select(doc)
        result, revised = transform(doc, styles, 'joined-label')
        headers = lambda d, style: [text(p) for p in d.iter(W+'p') if (p.find(W+'pPr/'+W+'pStyle') is not None and p.find(W+'pPr/'+W+'pStyle').get(W+'val') == style)]
        self.assertEqual(headers(doc, 'Heading3'), headers(result, 'Heading3'))
        before = headers(doc, 'Heading5'); before.remove(text(label))
        self.assertEqual(before, headers(result, 'Heading5'))
        self.assertEqual(c14n(styles), c14n(revised))

    def test_rejects_ambiguous_or_unbounded_q11(self):
        for mutation in ('duplicate', 'long', 'intervening', 'missing-style'):
            doc, styles = source(); heading, label, summary = select(doc)
            if mutation == 'duplicate': doc.find(W+'body').append(copy.deepcopy(heading))
            elif mutation == 'long': next(summary.iter(W+'t')).text = '中'*401
            elif mutation == 'intervening': label.addnext(E.Element(W+'bookmarkStart'))
            else: label.find(W+'pPr').remove(label.find(W+'pPr/'+W+'pStyle'))
            with self.assertRaises((AssertionError, AttributeError)): transform(doc, styles, 'joined-label')

    def test_pdf_prefix_removes_only_verified_whole_footer_lines(self):
        def bbox(q15_first=False, shift=False, bad_footer=False):
            first = '<line yMin="10"><word yMin="10" xMin="'+('2' if shift else '1')+'">Keep</word></line>'
            marker = '<line yMin="20"><word>15.</word><word>Resources</word></line>'
            footer = '<line yMin="95"><word>1</word><word>/</word><word>'+('3' if bad_footer else '2')+'</word></line>'
            second = '<line yMin="95"><word>2/2</word></line>'
            return ('<doc><page height="100">'+first+(marker if q15_first else '')+footer+'</page><page height="100">'+('' if q15_first else marker)+second+'</page></doc>').encode()
        self.assertEqual(prefix_geometry(bbox(True)), prefix_geometry(bbox(False)))
        self.assertNotEqual(prefix_geometry(bbox(True)), prefix_geometry(bbox(False, True)))
        with self.assertRaises(AssertionError): prefix_geometry(bbox(bad_footer=True))

    def test_frozen_rehearsal_explicitly_is_not_a_template_release(self):
        root = ROOT/'reviews/2026-09-18-profile-pagination'
        listed = {}
        for line in (root/'SHA256SUMS').read_text().splitlines():
            digest, name = line.split('  ', 1)
            listed[name.removeprefix('./')] = digest
        self.assertEqual(listed, {str(p.relative_to(root)): sha(p) for p in root.rglob('*') if p.is_file() and p.name != 'SHA256SUMS'})
        inventory = json.loads((root/'inventory.json').read_text())
        self.assertFalse(inventory['template_modified'])
        self.assertFalse(inventory['release_acceptance'])
        self.assertFalse(inventory['microsoft_word_acceptance'])
        for kind in ('word', 'pdf'):
            report = json.loads((root/kind/'report.json').read_text())
            self.assertTrue(report['completed']); self.assertEqual(len(report['rows']), 8)
            self.assertFalse(report['release_acceptance']); self.assertFalse(report['native_export'])
            runner = 'rehearse_profile_pagination.py' if kind == 'word' else 'rehearse_profile_pdf.py'
            self.assertEqual(report['checker_sha256'], sha(root/'reproduce'/runner))
            for row in report['rows']:
                self.assertEqual(row['pages'], 6)
                if row['trial'] != 'baseline': self.assertTrue(row['together'])
                stem = 'profile-partial-'+row['mode']+'-'+row['language']+'-'+row['trial']
                self.assertEqual(sha(root/kind/(stem+'.pdf')), row['pdf_sha256'])
                if kind == 'word':
                    self.assertEqual(sha(root/kind/(stem+'.docx')), row['docx_sha256'])
                    if row['trial'] == 'baseline': self.assertTrue(row['native_preview_geometry_identical'])
                elif not row['native_baseline_geometry_identical']:
                    self.assertEqual((row['language'], row['mode']), ('chinese', 'review'))
            selected = {r['trial']: r for r in report['rows'] if (r['language'], r['mode']) == ('chinese', 'submission')}
            if kind == 'word':
                self.assertEqual(selected['baseline']['q11_heading_summary_pages'], [4, 5])
                self.assertEqual(selected['joined-label']['q11_heading_summary_pages'], [5, 5])
            else:
                self.assertEqual(selected['baseline']['q15_heading_table_pages'], [[5], [6]])
                self.assertEqual(selected['keep-short-q15']['q15_heading_table_pages'], [[6], [6]])
        self.assertFalse(json.loads((root/'pdf/report.json').read_text())['all_native_baselines_reproduced'])


if __name__ == '__main__': unittest.main()
