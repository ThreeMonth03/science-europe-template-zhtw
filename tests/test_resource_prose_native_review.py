"""Keep native acceptance distinct from the previous offline Q15 trial."""
import json
from pathlib import Path
import sys
import unittest
import zipfile
from bs4 import BeautifulSoup
from docx import Document

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/'reviews/2026-09-18-resource-prose-native'
sys.path.insert(0,str(ROOT/'scripts'))
from artifact_utils import sha
from check_resource_prose_outputs import check_word,compare_native_text
from check_short_resources_outputs import fonts,compare_text
from rehearse_profile_pdf import snapshot,prefix_geometry
from rehearse_resource_prose import word_prefix_geometry,SENTENCES
from rehearse_profile_pagination import locate,geometry
from check_short_budget_outputs import prompt_lines


class ResourceProseNativeReview(unittest.TestCase):
    def test_frozen_native_artifacts_and_candidate_are_bound(self):
        expected=json.loads((ARCHIVE/'checksums.json').read_text())
        self.assertEqual(expected,{str(p.relative_to(ARCHIVE)):sha(p) for p in ARCHIVE.rglob('*') if p.is_file() and p.name!='checksums.json'})
        report=json.loads((ARCHIVE/'provenance/native-comparison.json').read_text())
        self.assertTrue(report['selected_checks_passed']);self.assertTrue(report['native_export'])
        self.assertFalse(report['release_acceptance']);self.assertFalse(report['microsoft_word_acceptance'])
        self.assertEqual(len(report['rows']),16);self.assertEqual(sum(r['selected'] for r in report['rows']),12)
        self.assertEqual(report['checker_sha256'],sha(ARCHIVE/'reproduce/check_resource_prose_outputs.py'))
        self.assertEqual(report['contract_sha256'],sha(ARCHIVE/'reproduce/english/scripts/resource_prose_contract.py'))
        candidate=json.loads((ARCHIVE/'provenance/candidate-manifest.json').read_text())
        self.assertEqual(candidate['status'],'candidate');self.assertEqual(candidate['translation_units'],748)
        self.assertEqual(candidate['untranslated_units'],[])
        self.assertTrue(all(not c['dirty'] for c in candidate['checkouts'].values()))
        self.assertEqual(candidate['source']['version'],'0.3.41')
        for row in report['rows']:
            for phase,key in [('before','prior_artifact_sha256'),('after','artifact_sha256')]:
                for name,digest in row[key].items():
                    if name.endswith('.html'):
                        source=ARCHIVE/phase/'question-content'/Path(name).name
                        self.assertTrue(source.read_text().startswith('<!-- Native HTML SHA256: '+digest+' -->'))
                    else:self.assertEqual(sha(ARCHIVE/phase/name.replace('renders/','native/',1)),digest)

    def test_independent_prepared_grammar_and_translation_proofs_are_retained(self):
        for language in ('en','zh'):
            report=json.loads((ARCHIVE/'provenance'/('candidate-short-resources-engine-'+language+'.json')).read_text())
            self.assertTrue(report['passed']);self.assertEqual(len(report['rows']),130)
            self.assertEqual(len(report['engine']['rows']),130)
            self.assertEqual(report['helper_sha256'],sha(ARCHIVE/'reproduce/english/src/pdf/short-resources.html.j2'))
        report=json.loads((ARCHIVE/'provenance/candidate-resource-prose-translation.json').read_text())
        self.assertTrue(report['passed']);self.assertEqual(sum(r['checks'] for r in report['rows']),500)
        self.assertEqual(sum(r['joined'] for r in report['rows']),40)
        scope=json.loads((ARCHIVE/'provenance/candidate-resource-prose-scope.json').read_text())
        self.assertTrue(scope['passed']);self.assertEqual(scope['translation_units'],748)

    def test_native_word_body_preserves_everything_outside_the_owned_pair(self):
        report=json.loads((ARCHIVE/'provenance/native-comparison.json').read_text())
        for row in report['rows']:
            stem=row['case']+'-'+row['profile']+'-'+row['language']
            paths=[ARCHIVE/phase/'native'/(stem+'.docx') for phase in ('before','after')]
            with self.subTest(stem=stem):
                self.assertEqual(check_word(*map(Document,paths),row['language'],row['selected']),row['word'])
                with zipfile.ZipFile(paths[0]) as a,zipfile.ZipFile(paths[1]) as b:
                    for part in ('word/styles.xml','word/fontTable.xml','word/numbering.xml'):self.assertEqual(a.read(part),b.read(part))

    def test_native_layout_and_actual_line_reduction_are_rechecked(self):
        report=json.loads((ARCHIVE/'provenance/native-comparison.json').read_text())
        for row in report['rows']:
            stem=row['case']+'-'+row['profile']+'-'+row['language']
            soup=BeautifulSoup((ARCHIVE/'after/question-content'/(stem+'.html')).read_text(),'html.parser')
            for kind,folder,prefix in [('pdf','native',prefix_geometry),('word','word-preview',word_prefix_geometry)]:
                paths=[ARCHIVE/phase/folder/(stem+'.pdf') for phase in ('before','after')]
                snapshots=[snapshot(p) for p in paths]
                self.assertEqual(len(snapshots[0][0]),len(snapshots[1][0]))
                compare_native_text([s[0] for s in snapshots],soup,row['case'])
                self.assertEqual(*[fonts(p) for p in paths])
                self.assertEqual(*[[v for v in prefix(s[1]) if v[0]>1] for s in snapshots])
                if not row['selected']:self.assertEqual(*[geometry(p)[1:] for p in paths])
                if row['case']=='profile-partial':
                    q=soup.select_one('#q-required-resources');self.assertEqual(locate(paths[1],[q.h3.get_text(),q.h4.get_text()])[1],[6,6])
        metrics=json.loads((ARCHIVE/'provenance/line-metrics.json').read_text())['rows']
        self.assertEqual(len(metrics),8)
        for row in metrics:
            language='chinese' if row['stem'].endswith('-chinese') else 'english'
            self.assertEqual(row['before_line_count'],2);self.assertEqual(row['after_line_count'],1 if language=='chinese' else 2)
            path=ARCHIVE/'after'/('native' if row['kind']=='pdf' else 'word-preview')/(row['stem']+'.pdf')
            self.assertEqual(sha(path),row['after_pdf_sha256'])
            self.assertEqual(prompt_lines(path,SENTENCES[language][0]+SENTENCES[language][1][1]),row['after'])


if __name__=='__main__':unittest.main()
