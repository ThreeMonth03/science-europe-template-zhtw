"""Preserve both successful A/B evidence and the two unmatched native baselines."""
from collections import Counter
import json
from pathlib import Path
import sys
import unittest
from bs4 import BeautifulSoup,Comment
from docx import Document
ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/'reviews/2026-09-18-mixed-budget'
sys.path.insert(0,str(ROOT/'scripts'))
from artifact_utils import sha
from rehearse_mixed_budget import content,MARKERS
from rehearse_profile_pdf import snapshot,prefix_geometry
from check_short_resources_outputs import fonts
from check_word_short_budget_outputs import verify_preview_paragraphs


class MixedBudgetReviewTests(unittest.TestCase):
    def report(self):return json.loads((ARCHIVE/'provenance/trial-report.json').read_text())

    def test_archive_checksums_and_explicit_acceptance_boundary(self):
        expected=json.loads((ARCHIVE/'checksums.json').read_text())
        self.assertEqual(expected,{str(p.relative_to(ARCHIVE)):sha(p) for p in ARCHIVE.rglob('*') if p.is_file() and p.name!='checksums.json'})
        report=self.report();self.assertTrue(report['completed']);self.assertEqual(len(report['rows']),8)
        for key in ['template_modified','native_export','word_modified','release_acceptance','microsoft_word_acceptance','all_native_baselines_reproduced']:self.assertFalse(report[key])
        self.assertTrue(report['all_trial_page_counts_nonincreasing'])
        self.assertEqual(report['checker_sha256'],sha(ARCHIVE/'reproduce/rehearse_mixed_budget.py'))
        self.assertEqual(report['contract_sha256'],sha(ARCHIVE/'reproduce/mixed_budget_trial.py'))
        native=json.loads((ARCHIVE/'provenance/native-missing-info-render-report.json').read_text())
        self.assertTrue(native['all_renders_succeeded']);self.assertEqual(len(native['renders']),24)
        for row in report['rows']:
            stem=row['stem']
            for fmt,digest in row['source_sha256'].items():
                path=ARCHIVE/'native'/(stem+'.'+fmt)
                if fmt=='html':self.assertTrue((ARCHIVE/'native/question-content'/path.name).read_text().startswith('<!-- Full HTML SHA256: '+digest+' -->'))
                else:self.assertEqual(sha(path),digest)
                receipt=json.loads(path.with_suffix(path.suffix+'.fixture.json').read_text())
                self.assertEqual(receipt['package_sha256'],native['package_sha256'][row['language']+'.zip'])
                locale='en' if row['language']=='english' else 'zh-Hant'
                for suffix,key in [('.json','recipe_sha256'),('.events.json','events_sha256')]:self.assertEqual(sha(ARCHIVE/'fixtures'/locale/(row['case']+suffix)),receipt[key])
            for name,digest in row['trial_sha256'].items():self.assertEqual(sha(ARCHIVE/'trials'/name),digest)

    def test_only_selected_row_hints_change_and_long_table_is_identical(self):
        for row in self.report()['rows']:
            stem=row['stem'];before,after=[BeautifulSoup((ARCHIVE/'trials/question-content'/(stem+'-'+mode+'.html')).read_text(),'html.parser') for mode in ['baseline','keep-short-rows']]
            selected=after.select('.pdf-short-resource-row');self.assertEqual(len(selected),8)
            for node in selected:
                self.assertEqual(node.attrs,{'class':['pdf-short-resource-row'],'data-item-id':node['data-item-id'],'style':'break-inside: avoid'})
                del node['class'];del node['style']
            # Collector provenance comments deliberately hash different full HTML
            # inputs. Exclude only this exact leading non-document record.
            for soup in [before,after]:
                node=soup.contents[0];self.assertIsInstance(node,Comment)
                self.assertRegex(str(node),r'^ Full HTML SHA256: [0-9a-f]{64} $');node.extract()
            self.assertEqual(str(before),str(after))
            self.assertEqual(len(before.select('.pdf-resource-reading')),1)

    def test_actual_pdf_rows_content_and_native_font_discrepancy_are_rechecked(self):
        for row in self.report()['rows']:
            stem=row['stem'];source=(ARCHIVE/'trials/question-content'/(stem+'-baseline.html')).read_text()
            paths=[ARCHIVE/'trials'/(stem+'-'+mode+'.pdf') for mode in ['baseline','keep-short-rows']]
            values=[snapshot(path) for path in paths];native=ARCHIVE/'native'/(stem+'.pdf');original=snapshot(native)
            parsed=[content(v[0],source) for v in values];native_parsed=content(original[0],source)
            with self.subTest(stem=stem):
                self.assertEqual(parsed[0]['canonical'],parsed[1]['canonical']);self.assertEqual(native_parsed['canonical'],parsed[0]['canonical'])
                self.assertEqual(Counter(c for c in ''.join(values[0][0]) if c in MARKERS),Counter(c for c in ''.join(values[1][0]) if c in MARKERS))
                self.assertEqual(prefix_geometry(values[0][1]),prefix_geometry(values[1][1]))
                self.assertEqual(fonts(paths[0]),fonts(paths[1]));self.assertLessEqual(len(values[1][0]),len(values[0][0]))
                self.assertEqual(parsed[0]['rows'],row['prior_rows']);self.assertEqual(parsed[1]['rows'],row['rows'])
                self.assertTrue(all(len(v['pages'])==1 for v in parsed[1]['rows']))
                if all(len(v['pages'])==1 for v in parsed[0]['rows']):self.assertEqual(values[0][1],values[1][1])
                for phase,value in zip(['native','baseline','trial'],[native_parsed,*parsed]):
                    repeated={r['page'] for r in value['repeated_headers'] if r['kind']=='long-identity'}
                    missing=sorted(set(value['long_pages'][1:])-repeated)
                    # Preserve the newly observed native defect, never certify it
                    # through an offline replay that did not reproduce it.
                    expected=[9] if phase=='native' and stem=='mixed-long-last-review-chinese' else []
                    self.assertEqual(missing,expected)
                matches=row['language']!='chinese' or row['profile']!='review'
                self.assertEqual(original[1]==values[0][1],matches);self.assertEqual(fonts(native)==fonts(paths[0]),matches)
                self.assertEqual(row['native_baseline_geometry_identical'],matches)

    def test_word_retains_every_long_paragraph_and_continuation_identity(self):
        for row in self.report()['rows']:
            stem=row['stem'];preview=ARCHIVE/'word-preview'/(stem+'.pdf')
            self.assertEqual(sha(preview),row['word_preview_sha256'])
            soup=BeautifulSoup((ARCHIVE/'native/question-content'/(stem+'.html')).read_text(),'html.parser')
            doc=Document(ARCHIVE/'native'/(stem+'.docx'));self.assertEqual(verify_preview_paragraphs(doc,preview,soup),row['word_preview_paragraphs_checked'])
            pages=snapshot(preview)[0];whole=''.join(pages)
            markers=[f'MIX-LONG-09-PARA-{n:02d}:' for n in range(1,61)]
            self.assertTrue(all(whole.count(m)==1 for m in markers));self.assertEqual([whole.index(m) for m in markers],sorted(whole.index(m) for m in markers))
            title=''.join(soup.select_one('.resource-table tbody').find_all('tr',recursive=False)[8].td.p.get_text().split())
            for page in pages:
                if any(m in page for m in markers):self.assertIn(title,page)
            self.assertEqual(row['word_continuation_without_row_name'],[])

    def test_pdf_oracle_rejects_changed_missing_and_wrong_row_content(self):
        stem='mixed-long-last-review-english';source=(ARCHIVE/'trials/question-content'/(stem+'-baseline.html')).read_text()
        pages=snapshot(ARCHIVE/'native'/(stem+'.pdf'))[0]
        for old,new in [('700TWD','600TWD'),('MIX-LONG-09-PARA-17:',''),('MIX-LONG-09-PARA-17:','MIX-LONG-09-PARA-18:')]:
            bad=[p.replace(old,new) for p in pages]
            with self.subTest(value=old),self.assertRaises(AssertionError):content(bad,source)

    def test_native_header_defect_addendum_is_immutable_and_bound_to_the_pdf(self):
        folder=ROOT/'reviews/2026-09-18-mixed-budget-header'
        checksums=json.loads((folder/'checksums.json').read_text())
        self.assertEqual(checksums,{str(p.relative_to(folder)):sha(p) for p in folder.rglob('*') if p.is_file() and p.name!='checksums.json'})
        report=json.loads((folder/'inventory.json').read_text())
        self.assertFalse(report['native_header_acceptance']);self.assertFalse(report['cause_confirmed'])
        self.assertEqual(report['source_pdf_sha256'],sha(ARCHIVE/'native/mixed-long-last-review-chinese.pdf'))
        self.assertEqual(report['source_archive_checksums_sha256'],sha(ARCHIVE/'checksums.json'))
        self.assertEqual(report['missing_header_pages'],[9])


if __name__=='__main__':unittest.main()
