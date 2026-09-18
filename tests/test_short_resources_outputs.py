import json
from pathlib import Path
import sys
import unittest
import zipfile
from bs4 import BeautifulSoup
from docx import Document

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/'reviews/2026-09-18-short-resources'
sys.path.insert(0,str(ROOT/'scripts'))
from artifact_utils import sha
from check_budget_outputs import body,xml
from check_word_rhythm_outputs import compare_questions
from check_short_resources_outputs import compare_text,fonts
from rehearse_profile_pdf import snapshot,prefix_geometry
from rehearse_profile_pagination import geometry


class ShortResourcesOutputs(unittest.TestCase):
    def test_archive_hashes_and_native_reports_are_bound(self):
        expected=json.loads((ARCHIVE/'checksums.json').read_text())
        self.assertEqual(expected,{str(p.relative_to(ARCHIVE)):sha(p) for p in ARCHIVE.rglob('*') if p.is_file() and p.name!='checksums.json'})
        report=json.loads((ARCHIVE/'provenance/native-comparison.json').read_text())
        self.assertTrue(report['selected_checks_passed']);self.assertEqual(len(report['rows']),16)
        self.assertFalse(report['release_acceptance']);self.assertFalse(report['microsoft_word_acceptance'])
        self.assertEqual(sum(r['question_comparisons'] for r in report['rows']),240)
        self.assertEqual(sum(r['selected'] for r in report['rows']),4)
        for row in report['rows']:
            for phase,key in [('before','prior_artifact_sha256'),('after','artifact_sha256')]:
                for name,digest in row[key].items():
                    if name.endswith('.html'):
                        line=(ARCHIVE/phase/'question-content'/Path(name).name).read_text().splitlines()[0]
                        self.assertEqual(line,'<!-- Native HTML SHA256: '+digest+' -->')
                    else:self.assertEqual(sha(ARCHIVE/phase/name.replace('renders/','native/',1)),digest)

    def test_every_native_word_body_style_and_question_html_is_unchanged(self):
        for path in (ARCHIVE/'after/native').glob('*.docx'):
            with self.subTest(name=path.name):
                prior=ARCHIVE/'before/native'/path.name
                docs=[Document(p) for p in (prior,path)]
                self.assertEqual(*[[xml(n) for n in body(d)] for d in docs])
                with zipfile.ZipFile(prior) as a,zipfile.ZipFile(path) as b:
                    for part in ('word/styles.xml','word/numbering.xml','word/fontTable.xml'):self.assertEqual(a.read(part),b.read(part))
                soups=[BeautifulSoup((ARCHIVE/phase/'question-content'/path.with_suffix('.html').name).read_text(),'html.parser') for phase in ('before','after')]
                self.assertEqual(compare_questions(*soups),15)

    def test_pdf_changes_are_limited_to_selected_q15(self):
        report=json.loads((ARCHIVE/'provenance/native-comparison.json').read_text())
        for row in report['rows']:
            stem=row['case']+'-'+row['profile']+'-'+row['language']
            paths=[ARCHIVE/phase/'native'/(stem+'.pdf') for phase in ('before','after')]
            with self.subTest(stem=stem):
                self.assertEqual(*[fonts(p) for p in paths])
                self.assertTrue(row['pdf_font_inventory_unchanged'])
                self.assertEqual(fonts(paths[1]),row['pdf_font_inventory'])
                soup=BeautifulSoup((ARCHIVE/'after/question-content'/(stem+'.html')).read_text(),'html.parser')
                compare_text(*[snapshot(p)[0] for p in paths],soup)
                if row['selected']:
                    self.assertEqual(*[prefix_geometry(snapshot(p)[1]) for p in paths])
                    self.assertEqual(row['q15_heading_table_pages'],[[6],[6]])
                else:self.assertEqual(*[geometry(p)[1:] for p in paths])
                self.assertEqual(*[geometry(ARCHIVE/phase/'word-preview'/(stem+'.pdf'))[1:] for phase in ('before','after')])
        selected=next(r for r in report['rows'] if (r['case'],r['profile'],r['language'])==('profile-partial','submission','chinese'))
        self.assertEqual(selected['prior_q15_heading_table_pages'],[[5],[6]])

    def test_text_oracle_retains_punctuation_and_counts_all_bullets(self):
        soup=BeautifulSoup('<p>Original.csv：0。</p>','html.parser')
        compare_text(['Original.csv：0。••'],['•Original.csv：0。•'],soup)
        for wrong in ['Original.csv：0••','Original.csv：1。••','Original.csv：0。•']:
            with self.assertRaises(AssertionError):compare_text(['Original.csv：0。••'],[wrong],soup)
        with self.assertRaises(AssertionError):compare_text(['A•'],['A•'],BeautifulSoup('<p>A•</p>','html.parser'))

    def test_candidate_is_clean_and_both_prepared_engine_proofs_match_the_helper(self):
        manifest=json.loads((ARCHIVE/'provenance/candidate-manifest.json').read_text())
        self.assertEqual(manifest['status'],'candidate');self.assertEqual(manifest['translation_units'],748)
        self.assertFalse(any(v['dirty'] for v in manifest['checkouts'].values()))
        for language in ('en','zh'):
            report=json.loads((ARCHIVE/'provenance'/('candidate-short-resources-engine-'+language+'.json')).read_text())
            self.assertTrue(report['passed']);self.assertEqual(len(report['rows']),114)
            self.assertEqual(len(report['engine']['rows']),114)
            self.assertEqual(report['helper_sha256'],sha(ARCHIVE/'reproduce/src/pdf/short-resources.html.j2'))


if __name__=='__main__':unittest.main()
