from importlib.resources import files
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'reviews/2026-09-21-budget-grouping-integration'
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'experiments/mixed-budget-header'))
from artifact_utils import sha
from check_budget_grouping_integration import ARCHIVE as BASELINE, SEAL, project_metadata
from check_budget_grouping_native import pair
from compact import restore_source


class BudgetGroupingNativeTests(unittest.TestCase):
    def test_sealed_archive_and_reference(self):
        self.assertEqual(sha(ARCHIVE / 'checksums.json'), 'a434d783ffc7737696d7519a49026dad7f07c2120d4882d7637663e831b8cf28')
        self.assertEqual(json.loads((ARCHIVE / 'checksums.json').read_text()),
            {str(p.relative_to(ARCHIVE)): sha(p) for p in ARCHIVE.rglob('*') if p.is_file() and p.name != 'checksums.json'})
        self.assertEqual(sha(BASELINE / 'checksums.json'), SEAL)
        report = json.loads((ARCHIVE / 'provenance/budget-grouping-native.json').read_text())
        self.assertEqual(report['checker_sha256'], sha(ARCHIVE / 'reproduce/check_budget_grouping_native.py'))
        self.assertEqual(report['frozen_seal'], SEAL)
        self.assertTrue(report['selected_checks_passed'] and report['native_export'])
        self.assertFalse(report['release_acceptance'] or report['microsoft_word_acceptance'])

    def test_integrated_package_metadata_and_asset_hashes(self):
        manifest = json.loads((ARCHIVE / 'provenance/candidate-manifest.json').read_text())
        self.assertEqual(manifest['status'], 'candidate')
        self.assertTrue(all(not state['dirty'] for state in manifest['checkouts'].values()))
        self.assertEqual(manifest['translation_units'], 748)
        new_members = json.loads((ARCHIVE / 'provenance/package-members.json').read_text())
        old_members = json.loads((BASELINE / 'provenance/package-projection.json').read_text())
        for language in ['english', 'chinese']:
            before = json.loads((BASELINE / f'package/after-{language}.json').read_text())
            after = json.loads((ARCHIVE / f'package/{language}.json').read_text())
            self.assertEqual(project_metadata(after, before, manifest['package_timestamp']), before)
            old = old_members[language]['members'][1]; new = new_members[language]
            self.assertEqual(set(new), set(old))
            self.assertEqual({name for name in old if old[name] != new[name]}, {'template/template.json'})

    def test_all_eight_native_pairs_recomputed(self):
        report = json.loads((ARCHIVE / 'provenance/budget-grouping-native.json').read_text())
        self.assertEqual(len(report['rows']), 8)
        for row in report['rows']:
            with self.subTest(stem=row['stem']):
                result = pair(ARCHIVE / 'after', row['stem'], report['package_sha256'], compacted=True)
                proof = json.loads((ARCHIVE / 'after/renders' / (row['stem'] + '.html.compact.json')).read_text())
                self.assertEqual(result['artifacts']['html'], proof['compact_html_sha256'])
                result['artifacts']['html'] = proof['original_html_sha256']
                self.assertEqual(json.loads(json.dumps(result)), row)

    def test_compact_html_restores_exact_exported_bytes(self):
        font = files('dsw_document_template_tool').joinpath('resources/fonts/NotoSansTC-Variable.ttf').read_bytes()
        digest = hashlib.sha256(font).hexdigest()
        paths = list((ARCHIVE / 'after/renders').glob('*.html'))
        self.assertEqual(len(paths), 8)
        for path in paths:
            proof = json.loads(path.with_suffix('.html.compact.json').read_text())
            self.assertEqual(set(proof['fonts']), {digest})
            self.assertFalse(proof['native_pdf_entry_input'])
            self.assertEqual(sha(path), proof['compact_html_sha256'])
            self.assertEqual(hashlib.sha256(restore_source(path.read_bytes(), {digest: font})).hexdigest(), proof['original_html_sha256'])

    def test_local_runtime_restored_and_no_release_claim(self):
        life = json.loads((ARCHIVE / 'provenance/worker-lifecycle.json').read_text())
        self.assertEqual(life['deleted_owned_templates'], 2)
        self.assertTrue(life['stock_worker_restored'] and life['template_zip_backups_retained'])
        self.assertFalse(life['production_touched'])
        self.assertTrue(all(row['status'] == 'exited' for row in life['after']))
        inventory = json.loads((ARCHIVE / 'inventory.json').read_text())
        self.assertFalse(inventory['release_acceptance'] or inventory['microsoft_word_acceptance'])


if __name__ == '__main__': unittest.main()
