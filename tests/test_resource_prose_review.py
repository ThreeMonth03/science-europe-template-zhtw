import json
from pathlib import Path
import sys
import unittest
import zipfile
from lxml import etree as E
from docx import Document

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/'reviews/2026-09-18-resource-prose'
sys.path.insert(0,str(ROOT/'scripts'))
from artifact_utils import sha
from rehearse_resource_prose import join_word,c14n,word_prefix_geometry,SENTENCES
from rehearse_profile_pdf import snapshot,prefix_geometry
from check_short_resources_outputs import fonts
from check_short_budget_outputs import prompt_lines


class ResourceProseReview(unittest.TestCase):
    def test_frozen_archive_is_complete_and_never_claims_native_acceptance(self):
        expected=json.loads((ARCHIVE/'checksums.json').read_text())
        self.assertEqual(expected,{str(p.relative_to(ARCHIVE)):sha(p) for p in ARCHIVE.rglob('*') if p.is_file() and p.name!='checksums.json'})
        report=json.loads((ARCHIVE/'provenance/trial-report.json').read_text())
        self.assertTrue(report['completed']);self.assertEqual(len(report['rows']),8)
        for key in ('native_export','template_modified','release_acceptance','microsoft_word_acceptance'):self.assertFalse(report[key])
        self.assertEqual(report['checker_sha256'],sha(ARCHIVE/'reproduce/rehearse_resource_prose.py'))
        self.assertEqual(sum(r['selected'] for r in report['rows']),4)
        for row in report['rows']:
            self.assertEqual(row['pdf_pages'][0],row['pdf_pages'][1]);self.assertEqual(row['word_pages'][0],row['word_pages'][1])
            for name,digest in row['artifact_sha256'].items():self.assertEqual(sha(ARCHIVE/'trials'/name),digest)

    def test_every_word_delta_is_reversible_and_all_other_parts_are_identical(self):
        report=json.loads((ARCHIVE/'provenance/trial-report.json').read_text())
        for row in report['rows']:
            stem=row['stem'];source=ARCHIVE/'native-baseline'/(stem+'.docx')
            self.assertEqual(sha(source),row['source_docx_sha256'])
            with self.subTest(stem=stem),zipfile.ZipFile(source) as old,zipfile.ZipFile(ARCHIVE/'trials'/(stem+'-joined.docx')) as new:
                expected,selected=join_word(E.fromstring(old.read('word/document.xml')),row['language'])
                self.assertEqual(selected,row['selected']);self.assertEqual(c14n(expected),c14n(E.fromstring(new.read('word/document.xml'))))
                self.assertEqual(old.namelist(),new.namelist())
                for part in old.namelist():
                    if part!='word/document.xml':self.assertEqual(old.read(part),new.read(part))
                if not selected:self.assertEqual(sha(source),sha(ARCHIVE/'trials'/(stem+'-joined.docx')))

    def test_pdf_baseline_mismatches_are_visible_and_paired_prefixes_are_unchanged(self):
        report=json.loads((ARCHIVE/'provenance/trial-report.json').read_text())
        for row in report['rows']:
            stem=row['stem'];before,after=[ARCHIVE/'trials'/(stem+'-'+mode+'.pdf') for mode in ('baseline','joined')]
            native=ARCHIVE/'native-baseline'/(stem+'.pdf');self.assertEqual(sha(native),row['source_pdf_sha256'])
            self.assertEqual(prefix_geometry(snapshot(before)[1]),prefix_geometry(snapshot(after)[1]))
            self.assertEqual(fonts(before),fonts(after))
            matches=row['language']!='chinese' or row['profile']!='review'
            self.assertEqual(snapshot(native)[1]==snapshot(before)[1],matches)
            self.assertEqual(fonts(native)==fonts(before),matches)
            self.assertEqual(row['native_pdf_baseline_geometry_identical'],matches)
            paths=[ARCHIVE/'trials/word-preview'/(stem+'-'+mode+'.pdf') for mode in ('baseline','joined')]
            self.assertEqual(*[word_prefix_geometry(snapshot(p)[1]) for p in paths])

    def test_punctuation_and_line_metrics_preserve_the_actual_findings(self):
        report=json.loads((ARCHIVE/'provenance/punctuation.json').read_text())
        self.assertTrue(report['completed']);self.assertEqual(len(report['rows']),2)
        for row in report['rows']:
            self.assertFalse(row['real_whitespace_before_punctuation'])
            stem='profile-partial-'+row['profile']+'-chinese'
            texts=[p.text for p in Document(ARCHIVE/'native-baseline'/(stem+'.docx')).paragraphs]
            for value in row['html_word_pdf_text']:self.assertIn(value,texts)
            for kind in ('pdf','docx'):self.assertEqual(sha(ARCHIVE/'native-baseline'/(stem+'.'+kind)),row['input_sha256'][kind])
        metrics=json.loads((ARCHIVE/'provenance/line-metrics.json').read_text())['rows'];self.assertEqual(len(metrics),8)
        for row in metrics:
            chinese=row['stem'].endswith('-chinese');language='chinese' if chinese else 'english'
            self.assertEqual(row['before_line_count'],2);self.assertEqual(row['after_line_count'],1 if chinese else 2)
            folder=ARCHIVE/'trials'/('word-preview' if row['kind']=='word' else '')
            path=folder/(row['stem']+'-joined.pdf');self.assertEqual(sha(path),row['after_pdf_sha256'])
            self.assertEqual(prompt_lines(path,SENTENCES[language][0]+SENTENCES[language][1][1]),row['after'])
        word=next(r for r in metrics if r['stem']=='profile-partial-submission-chinese' and r['kind']=='word')
        self.assertEqual(word['before_q15_heading_budget_pages'],[5,6]);self.assertEqual(word['after_q15_heading_budget_pages'],[6,6])


if __name__=='__main__':unittest.main()
