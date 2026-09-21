import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
from bs4 import BeautifulSoup
from docx import Document
from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from artifact_utils import sha
from check_submission_preview_native import run_checks, compare_docx, word_html_inventory
from submission_preview_integration import CONTRACT, frozen_package
from check_budget_grouping_integration import project_metadata

ARCHIVE = ROOT / 'reviews/2026-09-21-submission-preview-integration'
SEAL = '91c722c3fa9e436c8ffd517f8b24e3d1e1d4ed274dfba769ed41e9da36c7ddbf'


def english_root():
    return next(p for p in [ROOT.parent / 'english', ROOT.parent / 'science-europe-template']
                if (p / 'scripts/output_profile_contract.py').is_file())


class SubmissionPreviewNativeTests(unittest.TestCase):
    def test_archive_inventory_seal_and_acceptance_limits(self):
        self.assertEqual(sha(ARCHIVE / 'checksums.json'), SEAL)
        checksums = json.loads((ARCHIVE / 'checksums.json').read_text())
        self.assertEqual(len(checksums), 179)
        self.assertEqual(set(checksums), {str(p.relative_to(ARCHIVE)) for p in ARCHIVE.rglob('*') if p.is_file() and p.name != 'checksums.json'})
        for name, digest in checksums.items(): self.assertEqual(sha(ARCHIVE / name), digest, name)
        inventory = json.loads((ARCHIVE / 'inventory.json').read_text())
        self.assertEqual((inventory['native_pairs'], inventory['native_artifacts'], inventory['word_previews']), (16, 48, 16))
        self.assertTrue(inventory['source_integrated'] and inventory['native_integrated_render_checked'])
        for key in ['production_touched', 'global_switch_complete', 'release_acceptance', 'microsoft_word_acceptance']:
            self.assertFalse(inventory[key])
        proof = json.loads((ARCHIVE / 'provenance/native.json').read_text())
        self.assertEqual(proof['checker_sha256'], sha(ARCHIVE / 'reproduce/check_submission_preview_native.py'))

    def test_all_sixteen_native_pairs_are_recomputed(self):
        rows = run_checks(ARCHIVE / 'native', ARCHIVE / 'fixtures', english_root(), compacted=True)
        for row in rows:
            receipt = json.loads((ARCHIVE / 'native/renders' / (row['stem'] + '.html.compact.json')).read_text())
            self.assertEqual(row['artifacts']['html'], receipt['compact_html_sha256'])
            row['artifacts']['html'] = receipt['original_html_sha256']
        expected = json.loads((ARCHIVE / 'provenance/native.json').read_text())
        self.assertTrue(expected['passed'])
        self.assertEqual(json.loads(json.dumps(rows)), expected['rows'])

    def test_actual_packages_bind_sources_formats_and_render_receipts(self):
        candidate = json.loads((ARCHIVE / 'provenance/candidate-manifest.json').read_text())
        runtime = json.loads((ARCHIVE / 'native/manifest.json').read_text())
        self.assertEqual(candidate['status'], 'candidate')
        self.assertTrue(all(not s['dirty'] for s in candidate['checkouts'].values()))
        self.assertEqual(candidate['source']['commit'], '41bb0ac59e86f5591b641a001a04240375426545')
        self.assertEqual(candidate['checkouts']['translation']['commit'], 'd17911ff57d29ede821193a0f03da1827f70e8de')
        self.assertEqual(candidate['source']['version'], candidate['translation']['version'])
        self.assertEqual(candidate['source']['version'], '0.3.44')
        members = json.loads((ARCHIVE / 'provenance/package-members.json').read_text())
        baseline_members = json.loads((ROOT / 'reviews/2026-09-21-dataset-labels/provenance/package-members.json').read_text())['before']
        for language in ['english', 'chinese']:
            package = json.loads((ARCHIVE / 'package' / (language + '.json')).read_text())
            raw = (json.dumps(package, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), members[language]['template/template.json'])
            self.assertEqual(set(members[language]), set(baseline_members[language]))
            for name, digest in members[language].items():
                if name != 'template/template.json': self.assertEqual(digest, baseline_members[language][name])
            baseline = frozen_package(language); prior = {f['fileName']: f for f in baseline['files']}
            projected = copy.deepcopy(package)
            for item in projected['files']:
                name = item['fileName']
                self.assertEqual(hashlib.sha256(item['content'].encode()).hexdigest(), CONTRACT['languages'][language]['after'][name])
                item['content'] = prior[name]['content']
            project_metadata(projected, baseline, candidate['package_timestamp'], versions=('0.3.43', '0.3.44'))
            self.assertEqual(runtime['identical_package_sha256'][language + '.zip'], candidate['sha256'][language + '.zip'])
        structural = json.loads((ARCHIVE / 'provenance/candidate-submission-preview-structure.json').read_text())
        self.assertTrue(structural['passed']); self.assertEqual(len(structural['rows']), 544)
        self.assertTrue(json.loads((ARCHIVE / 'provenance/candidate-budget-grouping-scope.json').read_text())['passed'])

    def test_docx_component_and_timestamp_mutations_are_rejected(self):
        source = ARCHIVE / 'native/renders/submission-metadata-submission-chinese.docx'
        with zipfile.ZipFile(source) as package: members = {n: package.read(n) for n in package.namelist()}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'mutant.docx'
            for mode in ['punctuation', 'link', 'invalid-timestamp', 'other-core-metadata']:
                data = dict(members)
                name = 'word/document.xml' if mode == 'punctuation' else 'word/_rels/document.xml.rels' if mode == 'link' else 'docProps/core.xml'
                tree = etree.fromstring(data[name])
                if mode == 'punctuation':
                    text = tree.find('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t')
                    text.text += '。'
                elif mode == 'link':
                    node = next(n for n in tree if n.get('TargetMode') == 'External'); node.set('Target', 'https://example.org/unreviewed')
                elif mode == 'invalid-timestamp': tree.find('{http://purl.org/dc/terms/}created').text = 'yesterday'
                else: etree.SubElement(tree, '{http://purl.org/dc/elements/1.1/}description').text = 'unreviewed'
                data[name] = etree.tostring(tree)
                with zipfile.ZipFile(path, 'w') as package:
                    for name, value in data.items(): package.writestr(name, value)
                with self.subTest(mode=mode), self.assertRaises((AssertionError, ValueError)):
                    compare_docx(source, path)

    def test_visible_word_inventory_does_not_ignore_punctuation_or_author_text(self):
        stem = ARCHIVE / 'native/renders/submission-metadata-submission-chinese'
        document = Document(stem.with_suffix('.docx'))
        soup = BeautifulSoup(stem.with_suffix('.html').read_text(), 'html.parser')
        self.assertGreater(word_html_inventory(document, soup), 0)
        for selector in ['.quality-summary', '.answer-detail']:
            broken = copy.deepcopy(soup); node = broken.select_one(selector); self.assertIsNotNone(node)
            node.append('。')
            with self.assertRaises(AssertionError): word_html_inventory(document, broken)

    def test_owned_local_cleanup_and_stock_worker_restoration(self):
        cleanup = json.loads((ARCHIVE / 'provenance/owned-test-template-cleanup.json').read_text())
        self.assertTrue(cleanup['run_completed_successfully']); self.assertEqual(len(cleanup['deleted']), 2)
        self.assertEqual((cleanup['project_references'], cleanup['document_references']), (0, 0))
        runtime = json.loads((ARCHIVE / 'native/manifest.json').read_text())
        for name, backup in cleanup['backups'].items(): self.assertEqual(backup['sha256'], runtime['identical_package_sha256'][name])
        lifecycle = json.loads((ARCHIVE / 'provenance/worker-lifecycle.json').read_text())
        self.assertTrue(lifecycle['stock_worker_restored'])
        self.assertEqual(len(lifecycle['after']), 4)
        self.assertTrue(all(s['status'] == 'exited' for s in lifecycle['after']))
        self.assertFalse(lifecycle['production_touched'])
