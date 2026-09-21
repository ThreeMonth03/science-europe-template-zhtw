import importlib.util
from importlib.resources import files
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'reviews/2026-09-21-large-resource-groups'
BASELINE = ROOT / 'reviews/2026-09-21-mixed-boundary-controls'
FROZEN_EN = ROOT / 'reviews/2026-09-18-short-resource-rows/reproduce/english'
sys.path.insert(0, str(ROOT / 'scripts'))
from artifact_utils import sha
from check_large_resource_groups import pair
from word_budget_geometry import inspect


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value


class LargeResourceGroupsTests(unittest.TestCase):
    def test_sealed_evidence_and_prior_reference(self):
        self.assertEqual(json.loads((ARCHIVE / 'checksums.json').read_text()),
            {str(p.relative_to(ARCHIVE)): sha(p) for p in ARCHIVE.rglob('*') if p.is_file() and p.name != 'checksums.json'})
        reference = json.loads((ARCHIVE / 'provenance/baseline-reference.json').read_text())
        self.assertEqual(reference['checksums_sha256'], sha(BASELINE / 'checksums.json'))
        report = json.loads((ARCHIVE / 'provenance/comparison.json').read_text())
        self.assertTrue(report['selected_checks_passed'] and report['prototype_only'])
        self.assertFalse(report['release_acceptance'] or report['microsoft_word_acceptance'] or report['full_control_matrix_complete'])
        self.assertEqual(report['checker_sha256'], sha(ARCHIVE / 'reproduce/check_large_resource_groups.py'))
        self.assertEqual(report['word_oracle_sha256'], sha(ARCHIVE / 'reproduce/word_budget_geometry.py'))

    def test_all_eight_native_pairs_recompute_exactly(self):
        packages = [json.loads((ARCHIVE / 'provenance' / name).read_text())['sha256'] for name in ['before-manifest.json', 'manifest.json']]
        report = json.loads((ARCHIVE / 'provenance/comparison.json').read_text())
        self.assertEqual(len(report['rows']), 8)
        for row in report['rows']:
            with self.subTest(stem=row['stem']):
                value = pair(BASELINE / 'after', ARCHIVE / 'after', row['stem'], compacted=True, package_hashes=packages)
                self.assertEqual(json.loads(json.dumps(value)), row)

    def test_prior_word_evidence_gaps_are_resolved_without_rewriting_history(self):
        previous = json.loads((BASELINE / 'provenance/comparison.json').read_text())
        self.assertFalse(previous['complete_word_content_acceptance'])
        proof = json.loads((ARCHIVE / 'provenance/prior-word-cell-proof.json').read_text())
        self.assertEqual(len(proof['rows']), 40)
        self.assertEqual(proof['oracle_sha256'], sha(ARCHIVE / 'reproduce/word_budget_geometry.py'))
        for row in proof['rows']:
            folder = BASELINE / row['phase']; stem = row['stem']
            pdf = folder / 'word-preview' / (stem + '.pdf')
            self.assertEqual(row['preview_sha256'], sha(pdf))
            result = inspect(folder / 'renders' / (stem + '.docx'), pdf, (folder / 'renders' / (stem + '.html')).read_text())
            self.assertEqual(result, row['result'])
            self.assertTrue(result['all_original_budget_cells_verified'])
            self.assertFalse(result['layout_acceptance'])

    def test_pandoc_ast_changes_and_pdf_groups(self):
        probe = module('large_groups_probe_test', ROOT / 'experiments/large-resource-groups/probe.py')
        report = json.loads((ARCHIVE / 'structure/report.json').read_text())
        self.assertEqual(report['checker_sha256'], sha(ARCHIVE / 'reproduce/experiment/probe.py'))
        self.assertEqual(len(report['rows']), 37)
        values = [json.loads((ARCHIVE / 'structure' / (n + '.json')).read_text()) for n in ['disabled', 'before', 'after']]
        for row in report['rows']:
            before, old, after = [v[row['case']] for v in values]
            self.assertEqual(after, probe.expected(before) if row['eligible'] else before)
            self.assertEqual(row['changed_from_previous'], old != after)
            if not row['eligible']: self.assertEqual(old, after)
        self.assertEqual(probe.pdf_controls(FROZEN_EN), report['pdf_groups'])

    def test_exact_package_projection_preserves_other_files_and_assets(self):
        recipe = module('large_groups_recipe_test', ROOT / 'experiments/large-resource-groups/prototype.py')
        prototype = json.loads((ARCHIVE / 'provenance/prototype.json').read_text())
        self.assertEqual(prototype['recipe_sha256'], sha(ARCHIVE / 'reproduce/experiment/prototype.py'))
        proof = json.loads((ARCHIVE / 'provenance/package-projection.json').read_text())
        for language in ['english', 'chinese']:
            old, new = [json.loads((ARCHIVE / 'package' / (p + '-' + language + '.json')).read_text()) for p in ['before', 'after']]
            self.assertEqual(recipe.patch(old), new)
            self.assertEqual(recipe.project(new), old)
            lua = [(ARCHIVE / 'package' / (p + '-' + language + '.lua')).read_text() for p in ['before', 'after']]
            self.assertEqual(recipe.patch_word(lua[0]), lua[1])
            members = proof[language]['members']
            self.assertEqual(set(members[0]), set(members[1]))
            self.assertEqual({n for n in members[0] if members[0][n] != members[1][n]},
                             {'template/template.json', 'template/assets/src/word/pilot.lua'})
            self.assertEqual(proof[language]['zip_sha256'][1], prototype['packages'][language + '.zip']['sha256'])
            for index, (phase, value) in enumerate(zip(['before', 'after'], [old, new])):
                encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
                self.assertEqual(hashlib.sha256(encoded).hexdigest(), members[index]['template/template.json'])
                self.assertEqual(sha(ARCHIVE / 'package' / (phase + '-' + language + '.lua')), members[index]['template/assets/src/word/pilot.lua'])

    def test_all_new_compact_html_restores_exact_native_exports(self):
        sys.path.insert(0, str(ROOT / 'experiments/mixed-budget-header'))
        from compact import restore_source
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

    def test_only_two_owned_templates_cleaned_and_services_restored(self):
        life = json.loads((ARCHIVE / 'provenance/lifecycle.json').read_text())
        self.assertEqual(life['deleted_owned_templates'], 2)
        self.assertTrue(life['stock_worker_restored'] and life['template_zip_backups_retained'])
        self.assertFalse(life['production_touched'] or life['capture_observer_attached'])
        self.assertTrue(all(r['status'] == 'exited' for r in life['after']))


if __name__ == '__main__': unittest.main()
