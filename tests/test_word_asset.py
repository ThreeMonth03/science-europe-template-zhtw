import copy
import json
from pathlib import Path
import sys
import unittest
from dsw.tdk.model import TemplateFile, TemplateFileType

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'reviews/2026-09-21-word-asset'
sys.path.insert(0, str(ROOT / 'experiments/word-asset'))
from asset_recipe import ARCHIVE as PARENT, SEAL as PARENT_SEAL, HERE, XML, OLD_XML, WORD_FORMATS, baseline, helper, patch, reverse, sha
from asset_native import run

SEAL = '6b02a8089961f516ad4bada87dea2a382831a6b9a91a357d706844051211ed0d'


class WordAssetTests(unittest.TestCase):
    def test_sealed_inventory_and_distinct_acceptance_scopes(self):
        seal = ARCHIVE / 'checksums.json'; self.assertEqual(sha(seal.read_bytes()), SEAL)
        files = json.loads(seal.read_text())
        self.assertEqual(len(files), 193)
        self.assertEqual(set(files), {str(p.relative_to(ARCHIVE)) for p in ARCHIVE.rglob('*') if p.is_file() and p != seal})
        for name, digest in files.items(): self.assertEqual(sha((ARCHIVE / name).read_bytes()), digest)
        inventory = json.loads((ARCHIVE / 'inventory.json').read_text())
        self.assertEqual(inventory['parent_seal_sha256'], PARENT_SEAL)
        for key in ['native_asset_pipeline_checked', 'all_html_pdf_word_outputs_preserved',
                    'full_source_translation_rehearsal_passed', 'source_integration_pending']:
            self.assertTrue(inventory[key])
        for key in ['source_integrated', 'translation_tree_modified', 'production_touched', 'full_source_native_render_checked',
                    'full_visual_acceptance', 'release_acceptance', 'microsoft_word_acceptance', 'global_switch_complete']:
            self.assertFalse(inventory[key])
        self.assertEqual((inventory['native_pairs'], inventory['full_source_structural_checks'],
                          inventory['retained_translation_pairs'], inventory['new_translation_units']), (12, 3312, 762, 5))

    def test_one_helper_moves_without_byte_or_unrelated_pipeline_changes(self):
        for language in ['english', 'chinese']:
            old = baseline(language); new = patch(old, language)
            self.assertEqual(reverse(new, language), old)
            self.assertEqual(len(new['files']), len(old['files']) - 1)
            self.assertEqual(len(new['assets']), len(old['assets']) + 1)
            self.assertEqual(new['assets'][:-1], old['assets'])
            self.assertEqual(next(f['content'].encode() for f in old['files'] if f['fileName'] == OLD_XML), helper())
            self.assertEqual([f for f in old['formats'] if f['uuid'] not in WORD_FORMATS],
                             [f for f in new['formats'] if f['uuid'] not in WORD_FORMATS])
            for mutation in ['asset', 'step', 'content']:
                bad = copy.deepcopy(new)
                if mutation == 'asset': bad['assets'][-1]['contentType'] = 'text/jinja2'
                elif mutation == 'step': next(f for f in bad['formats'] if f['uuid'] in WORD_FORMATS)['steps'][-1]['options'] = {}
                else: bad['files'][0]['content'] += ' '
                with self.assertRaises(AssertionError): reverse(bad, language)
            with self.assertRaises(AssertionError): patch(new, language)

    def test_real_tdk_classifies_xml_as_asset_and_built_package_carries_same_bytes(self):
        item = TemplateFile(filename=Path(XML))
        self.assertEqual(item.content_type, 'application/xml'); self.assertEqual(item.remote_type, TemplateFileType.ASSET)
        self.assertEqual(TemplateFile(filename=Path(OLD_XML)).remote_type, TemplateFileType.FILE)
        members = json.loads((ARCHIVE / 'provenance/package-members.json').read_text())
        old = json.loads((PARENT / 'provenance/package-members.json').read_text())
        for language in ['english', 'chinese']:
            self.assertEqual(set(members[language]) - set(old[language]), {'template/assets/' + XML})
            self.assertEqual({n for n in old[language] if old[language][n] != members[language][n]}, {'template/template.json'})
            self.assertEqual(members[language]['template/assets/' + XML], sha(helper()))
            self.assertEqual(json.loads((ARCHIVE / 'after' / (language + '.json')).read_text()), patch(baseline(language), language))

    def test_all_twelve_native_pairs_reproduce_exact_output_parity(self):
        rows = run(ARCHIVE / 'after', ARCHIVE / 'fixtures', compacted=True)
        proof = json.loads((ARCHIVE / 'provenance/native.json').read_text())
        self.assertEqual(json.loads(json.dumps(rows)), proof['rows'])
        self.assertEqual(len(rows), 12)
        for row in rows:
            self.assertTrue(row['html_bytes_identical']); self.assertTrue(row['word_components_identical_except_timestamps'])
            self.assertTrue(all(v['pixels_and_geometry_identical'] for v in row['rendered'].values()))
            if row['case'] == 'ethics-long': self.assertTrue(row['table_placement']['complete_short_table'])
        self.assertFalse(proof['full_source_translation_checked'])

    def test_cleanup_and_retained_diagnostic_failures(self):
        cleanup = json.loads((ARCHIVE / 'after/owned-test-template-cleanup.json').read_text())
        self.assertTrue(cleanup['run_completed_successfully']); self.assertEqual(len(cleanup['deleted']), 2)
        self.assertEqual((cleanup['project_references'], cleanup['document_references']), (0, 0))
        quota = json.loads((ARCHIVE / 'provenance/storage-allowance.json').read_text())
        self.assertTrue(quota['restored']); self.assertEqual(quota['before'], quota['after'])
        life = json.loads((ARCHIVE / 'provenance/worker-lifecycle.json').read_text())
        self.assertTrue(life['stock_worker_restored']); self.assertTrue(all(r['status'] == 'exited' for r in life['after']))
        cli = json.loads((ARCHIVE / 'diagnostics/fixture-cli-failure.json').read_text())
        self.assertFalse(cli['all_renders_succeeded']); self.assertEqual(cli['validation'], []); self.assertEqual(cli['renders'], [])
        initial = json.loads((ARCHIVE / 'diagnostics/initial-checker.json').read_text())
        self.assertFalse(initial['passed'])
        self.assertEqual(initial['checker_sha256'], sha((ARCHIVE / 'diagnostics/initial-asset-native.py').read_bytes()))


if __name__ == '__main__': unittest.main()
