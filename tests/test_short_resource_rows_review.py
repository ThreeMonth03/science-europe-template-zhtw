"""Recheck the immutable bilingual native row-pagination evidence."""
import json
from pathlib import Path
import sys
import unittest
import zipfile
from bs4 import BeautifulSoup
from docx import Document
ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/'reviews/2026-09-18-short-resource-rows'
sys.path.insert(0,str(ROOT/'scripts'))
from artifact_utils import sha
from check_budget_outputs import body,xml
from check_short_resources_outputs import fonts
from check_resource_prose_outputs import compare_native_text
from check_short_resource_rows_outputs import row_pages
from rehearse_profile_pdf import snapshot,prefix_geometry
from rehearse_resource_prose import word_prefix_geometry
from rehearse_profile_pagination import geometry


class ShortResourceRowsReview(unittest.TestCase):
    def test_frozen_archive_artifacts_and_candidate_binding(self):
        expected=json.loads((ARCHIVE/'checksums.json').read_text())
        self.assertEqual(expected,{str(p.relative_to(ARCHIVE)):sha(p) for p in ARCHIVE.rglob('*') if p.is_file() and p.name!='checksums.json'})
        report=json.loads((ARCHIVE/'provenance/native-comparison.json').read_text())
        self.assertTrue(report['selected_checks_passed']);self.assertTrue(report['native_export'])
        self.assertFalse(report['release_acceptance']);self.assertFalse(report['microsoft_word_acceptance'])
        self.assertEqual(len(report['rows']),16);self.assertEqual(sum(r['selected'] for r in report['rows']),4)
        self.assertEqual(report['checker_sha256'],sha(ARCHIVE/'reproduce/check_short_resource_rows_outputs.py'))
        self.assertEqual(report['contract_sha256'],sha(ARCHIVE/'reproduce/english/scripts/short_resource_rows_contract.py'))
        candidate=json.loads((ARCHIVE/'provenance/candidate-manifest.json').read_text())
        self.assertEqual(candidate['status'],'candidate');self.assertEqual(candidate['source']['version'],'0.3.42')
        self.assertEqual(candidate['translation_units'],748);self.assertEqual(candidate['untranslated_units'],[])
        self.assertTrue(all(not c['dirty'] for c in candidate['checkouts'].values()))
        for row in report['rows']:
            for phase,key in [('before','prior_artifact_sha256'),('after','artifact_sha256')]:
                for name,digest in row[key].items():
                    if name.endswith('.html'):
                        self.assertTrue((ARCHIVE/phase/'question-content'/Path(name).name).read_text().startswith('<!-- Native HTML SHA256: '+digest+' -->'))
                    else:self.assertEqual(sha(ARCHIVE/phase/name.replace('renders/','native/',1)),digest)

    def test_prepared_engine_bounds_and_exact_historical_projection(self):
        for language in ['en','zh']:
            proof=json.loads((ARCHIVE/'provenance'/('candidate-short-resource-rows-engine-'+language+'.json')).read_text())
            self.assertTrue(proof['passed']);self.assertEqual(len(proof['rows']),120);self.assertEqual(len(proof['engine']['rows']),28)
            self.assertEqual(proof['source_sha256']['src/pdf/short-resource-rows.html.j2'],sha(ARCHIVE/'reproduce/english/src/pdf/short-resource-rows.html.j2'))
            self.assertTrue(any(r['split_before']>r['split_after'] for r in proof['engine']['rows']))
        scope=json.loads((ARCHIVE/'provenance/candidate-short-resource-rows-scope.json').read_text())
        self.assertTrue(scope['passed']);self.assertEqual(scope['translation_units'],748)
        prior=json.loads((ROOT/'reviews/2026-09-18-resource-prose-native/provenance/candidate-resource-prose-scope.json').read_text())
        self.assertEqual(scope['translation_tree_sha256'],prior['translation_tree_sha256'])
        for row in scope['rows']:
            before=next(r['after'] for r in prior['rows'] if r['language']==row['language'])
            after=row['after'];self.assertEqual(set(after)-set(before),{'src/pdf/short-resource-rows.html.j2'})
            self.assertEqual([n for n in before if before[n]!=after[n]],['src/budget-reading.html.j2'])

    def test_native_word_body_styles_and_links_are_unchanged(self):
        report=json.loads((ARCHIVE/'provenance/native-comparison.json').read_text())
        for row in report['rows']:
            stem='-'.join([row['case'],row['profile'],row['language']])
            paths=[ARCHIVE/p/'native'/(stem+'.docx') for p in ['before','after']]
            docs=list(map(Document,paths))
            with self.subTest(stem=stem):
                self.assertEqual(*[[xml(n) for n in body(doc)] for doc in docs])
                self.assertEqual(*[sorted(r.target_ref for r in doc.part.rels.values() if r.is_external) for doc in docs])
                with zipfile.ZipFile(paths[0]) as a,zipfile.ZipFile(paths[1]) as b:
                    for part in ['word/styles.xml','word/fontTable.xml','word/numbering.xml']:self.assertEqual(a.read(part),b.read(part))

    def test_actual_native_layout_and_every_short_row_are_rechecked(self):
        report=json.loads((ARCHIVE/'provenance/native-comparison.json').read_text())
        for row in report['rows']:
            stem='-'.join([row['case'],row['profile'],row['language']])
            soup=BeautifulSoup((ARCHIVE/'after/question-content'/(stem+'.html')).read_text(),'html.parser')
            for kind,folder,prefix in [('pdf','native',prefix_geometry),('word','word-preview',word_prefix_geometry)]:
                paths=[ARCHIVE/p/folder/(stem+'.pdf') for p in ['before','after']]
                values=[snapshot(p) for p in paths]
                with self.subTest(stem=stem,kind=kind):
                    self.assertEqual(len(values[0][0]),len(values[1][0]))
                    compare_native_text([v[0] for v in values],soup,row['case'])
                    self.assertEqual(*[fonts(p) for p in paths])
                    self.assertEqual(*[[r for r in prefix(v[1]) if r[0]>1] for v in values])
                    if kind=='word' or not row['selected']:self.assertEqual(*[geometry(p)[1:] for p in paths])
                    if row['selected']:
                        before,after=[row_pages(v[0],soup) for v in values]
                        self.assertEqual(before,row['formats'][kind]['prior_rows']);self.assertEqual(after,row['formats'][kind]['rows'])
                        if kind=='pdf':
                            self.assertTrue(all(len(r['pages'])==1 for r in after))
                            self.assertEqual(sum(len(r['pages'])>1 for r in before),1)


if __name__=='__main__':unittest.main()
