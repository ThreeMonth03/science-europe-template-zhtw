import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from artifact_utils import sha
REVIEW = ROOT/'reviews/2026-09-18-metadata-gap-prose'


class MetadataGapProseReviewTests(unittest.TestCase):
    def test_all_archived_files_and_native_receipts_are_bound(self):
        hashes = json.loads((REVIEW/'checksums.json').read_text())
        files = {str(p.relative_to(REVIEW)) for p in REVIEW.rglob('*') if p.is_file() and p.name != 'checksums.json'}
        self.assertEqual(set(hashes), files)
        for name, digest in hashes.items():
            self.assertEqual(sha(REVIEW/name), digest, name)
        report = json.loads((REVIEW/'metadata-gap-prose-report.json').read_text())
        for key, script in [('checker_sha256','check_metadata_gap_prose_outputs.py'),
                            ('word_contract_sha256','probe_metadata_gap_prose.py'),
                            ('prose_contract_sha256','metadata_gap_prose_contract.py')]:
            self.assertEqual(report[key], sha(REVIEW/'reproduce'/script))
        for row in report['rows']:
            stem = row['case']+'-'+row['language']
            for fmt in ('pdf','docx'):
                name = stem+'.'+fmt
                self.assertEqual(row['after_sha256']['renders/'+name], sha(REVIEW/'native'/name))
            for fmt in ('html','pdf','docx'):
                name = stem+'.'+fmt+'.fixture.json'
                self.assertEqual(row['after_sha256']['renders/'+name], sha(REVIEW/'native'/name))
                receipt = json.loads((REVIEW/'native'/name).read_text())
                self.assertEqual(receipt['package_sha256'], report['package_sha256'][row['language']+'.zip'])
            self.assertEqual(row['after_sha256']['word-preview/'+stem+'.pdf'], sha(REVIEW/'word-preview'/(stem+'.pdf')))

    def test_both_missing_facts_retained_and_fallbacks_unchanged(self):
        report = json.loads((REVIEW/'metadata-gap-prose-report.json').read_text())
        self.assertTrue(report['selected_checks_passed'])
        self.assertFalse(report['release_acceptance'])
        self.assertEqual(len(report['rows']), 10)
        self.assertEqual(sum(r['word_joins'] for r in report['rows']), 2)
        for row in report['rows']:
            self.assertTrue(row['passed'])
            self.assertFalse(row['errors'])
            self.assertFalse(row['reading_issues'])
            self.assertEqual(row['pages'], row['prior_pages'])
            self.assertEqual(row['word_pages'], row['prior_word_pages'])
            self.assertEqual(row['word_joins'], int(row['selected']))
            if row['selected']:
                self.assertEqual(row['q3_missing_facts'], ['metadata-dictionary','metadata-access-instructions','metadata-harvestable','storage-capacity'])
                for name in ('prose_geometry','word_prose_geometry'):
                    self.assertLess(row[name]['after_span_pt'], row[name]['before_span_pt'])
                self.assertEqual(row['q5_word_locations'], [3 if row['language']=='english' else 4]*5)
        pixels = json.loads((REVIEW/'unchanged-control-pixels.json').read_text())
        self.assertTrue(pixels['passed'])
        self.assertEqual((len(pixels['rows']), pixels['identical_body_pages']), (8,18))

    def test_rebuild_engines_and_failed_trials_remain_separate(self):
        report = json.loads((REVIEW/'metadata-gap-prose-report.json').read_text())
        for name in ('candidate-manifest.json','rebuild-manifest.json'):
            m = json.loads((REVIEW/name).read_text())
            self.assertEqual({k:m['sha256'][k] for k in report['package_sha256']}, report['package_sha256'])
            self.assertFalse(any(v['dirty'] for v in m['checkouts'].values()))
            self.assertEqual(m['untranslated_units'], [])
            self.assertEqual(m['source']['version'], '0.3.37')
        scope = json.loads((REVIEW/'probes/metadata-gap-prose-scope.json').read_text())
        self.assertTrue(scope['passed'])
        self.assertEqual(scope['translation_units'], 747)
        for row in scope['rows']:
            self.assertEqual(row['changed'], ['src/layout.css','src/questions/03-docs-metadata.html.j2'])
            self.assertEqual(row['prose_checks']['comparisons'], 1726)
        for suffix in ('en','zh'):
            engine = json.loads((REVIEW/'probes'/('metadata-gap-prose-engine-'+suffix+'.json')).read_text())
            self.assertTrue(engine['passed'])
            self.assertEqual((engine['branch_checks'],len(engine['rows']),engine['word_joins']), (33,70,4))
            self.assertEqual(engine['checker_sha256'], sha(REVIEW/'reproduce/probe_metadata_gap_prose.py'))
        failure = REVIEW/'checker-diagnostics/word-hint'
        old = json.loads((failure/'engine-failure.json').read_text())
        self.assertFalse(old['passed'])
        self.assertEqual(old['checker_sha256'], sha(failure/'probe_metadata_gap_prose.py'))
        self.assertTrue(json.loads((REVIEW/'conversion-trial/structure-audit.json').read_text()))
