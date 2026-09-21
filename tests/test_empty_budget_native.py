from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch as mock_patch
import zipfile
from bs4 import BeautifulSoup
from docx import Document
from docx.oxml.ns import qn
from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'reviews/2026-09-21-empty-budget'
sys.path[:0] = [str(ROOT / 'experiments/table-flow'), str(ROOT / 'scripts')]
from budget_recipe import ARCHIVE as PARENT, SEAL as PARENT_SEAL, baseline, patch
from budget_native import run, gate, word_delta
from diagnose_word import change
from check_header_controls import raster_digest
from rehearse_profile_pagination import geometry
from check_word_short_budget_outputs import word_pages
from notice_native import generated_o_markers
from notice_probe import compact

SEAL = '3af4b110e89ebc277124a5f078ea46ec4693913f33f2a78884f5b8905d6198c2'


def english_root():
    return next(p for p in [ROOT.parent / 'english', ROOT.parent / 'science-europe-template']
                if (p / 'scripts/output_profile_contract.py').is_file())


class EmptyBudgetNativeTests(unittest.TestCase):
    def test_frozen_inventory_explicit_word_blocker_and_scoped_cleanup(self):
        seal = ARCHIVE / 'checksums.json'
        self.assertEqual(hashlib.sha256(seal.read_bytes()).hexdigest(), SEAL)
        files = json.loads(seal.read_text())
        self.assertEqual(len(files), 174)
        self.assertEqual(set(files), {str(p.relative_to(ARCHIVE)) for p in ARCHIVE.rglob('*') if p.is_file() and p != seal})
        for name, digest in files.items(): self.assertEqual(hashlib.sha256((ARCHIVE / name).read_bytes()).hexdigest(), digest)
        inventory = json.loads((ARCHIVE / 'inventory.json').read_text())
        for key in ['source_integrated', 'source_integration_allowed', 'translation_tree_modified', 'production_touched',
                    'visual_gate_passed', 'full_visual_acceptance', 'release_acceptance', 'global_switch_complete', 'microsoft_word_acceptance']:
            self.assertFalse(inventory[key])
        self.assertTrue(inventory['pdf_tail_page_regression_resolved'])
        self.assertEqual(inventory['parent_seal_sha256'], PARENT_SEAL)
        self.assertEqual((inventory['structural_checks'], inventory['native_pairs'], inventory['new_native_artifacts'],
                          inventory['new_word_previews'], inventory['word_diagnostic_variants']), (816, 12, 36, 12, 20))
        cleanup = json.loads((ARCHIVE / 'after/owned-test-template-cleanup.json').read_text())
        self.assertTrue(cleanup['run_completed_successfully']); self.assertEqual(len(cleanup['deleted']), 2)
        self.assertEqual((cleanup['project_references'], cleanup['document_references']), (0, 0))
        allowance = json.loads((ARCHIVE / 'provenance/storage-allowance.json').read_text())
        self.assertTrue(allowance['restored']); self.assertEqual(allowance['before'], allowance['after'])
        life = json.loads((ARCHIVE / 'provenance/worker-lifecycle.json').read_text())
        self.assertTrue(life['stock_worker_restored']); self.assertEqual(len(life['after']), 4)
        self.assertTrue(all(r['status'] == 'exited' for r in life['after']))

    def test_native_content_and_historical_page_limits_reproduce(self):
        rows = run(ARCHIVE / 'after', ARCHIVE / 'fixtures', english_root(), compacted=True)
        proof = json.loads((ARCHIVE / 'provenance/native.json').read_text())
        self.assertEqual(json.loads(json.dumps(rows)), proof['rows'])
        self.assertEqual(gate(rows), {k: proof[k] for k in ['visual_gate_passed', 'visual_blockers']})
        self.assertFalse(proof['passed']); self.assertTrue(proof['content_contract_passed'])
        self.assertEqual(proof['visual_blockers'], [dict(case='ethics-long', language='chinese', profile='review',
            engine='word_preview', issue='header-only-table-continuation', preexisting=True)])
        target = next(r for r in rows if (r['case'], r['language'], r['profile']) == ('ethics-long', 'chinese', 'submission'))
        pdf = target['rendered']['native_pdf']
        self.assertEqual((pdf['before']['pages'], pdf['after']['pages'], pdf['historical_page_limit']), (8, 7, 7))
        broken = copy.deepcopy(rows)
        target = next(r for r in broken if (r['case'], r['language'], r['profile']) == ('ethics-long', 'chinese', 'submission'))
        target['rendered']['native_pdf']['after']['pages'] = 8
        self.assertTrue(any(r['issue'] == 'page-count-increase' and r['limit'] == 7 for r in gate(broken)['visual_blockers']))

    def test_exact_packages_preserve_every_asset_and_version(self):
        members = json.loads((ARCHIVE / 'provenance/package-members.json').read_text())
        old = json.loads((PARENT / 'provenance/package-members.json').read_text())['after']
        prototype = json.loads((ARCHIVE / 'after/prototype.json').read_text())
        for language in ['english', 'chinese']:
            new, operations = patch(baseline(language), language)
            self.assertEqual(json.loads((ARCHIVE / ('after/' + language + '.json')).read_text()), new)
            self.assertEqual(prototype['packages'][language + '.zip']['operations'], operations)
            self.assertEqual(set(members[language]), set(old[language]))
            self.assertEqual({n for n in members[language] if members[language][n] != old[language][n]}, {'template/template.json'})

    def test_word_omission_oracle_rejects_other_text_style_and_asset_changes(self):
        paths = [r / 'after/renders/ethics-missing-submission-chinese.docx' for r in [PARENT, ARCHIVE]]
        row = next(r for r in json.loads((ARCHIVE / 'provenance/native.json').read_text())['rows']
                   if (r['case'], r['profile'], r['language']) == ('ethics-missing', 'submission', 'chinese'))
        class Package:
            def __init__(self, values): self.values = values
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def namelist(self): return list(self.values)
            def read(self, name): return self.values[name]
        values = []
        for path in paths:
            with zipfile.ZipFile(path) as z: values.append({n: z.read(n) for n in z.namelist()})
        for mutation in ['authored', 'style', 'asset']:
            changed = copy.deepcopy(values[1])
            if mutation == 'asset': changed['word/styles.xml'] += b' '
            else:
                tree = etree.fromstring(changed['word/document.xml'])
                if mutation == 'authored':
                    node = next(n for n in tree.iter(qn('w:t')) if n.text and 'AUTHORED-RESOURCE-' in n.text)
                    node.text = node.text.replace('N/A', 'NA')
                else: next(tree.iter(qn('w:pStyle'))).set(qn('w:val'), 'BodyText')
                changed['word/document.xml'] = etree.tostring(tree)
            with mock_patch('budget_native.zipfile.ZipFile', side_effect=[Package(values[0]), Package(changed)]):
                with self.assertRaises(AssertionError): word_delta(*paths, row['changes'])

    def test_twenty_diagnostic_documents_recreate_exactly_and_keep_all_visible_text(self):
        report = json.loads((ARCHIVE / 'word-diagnostic/report.json').read_text())
        self.assertTrue(report['completed']); self.assertTrue(report['diagnostic_only']); self.assertFalse(report['native_checked'])
        self.assertEqual(len(report['rows']), 20)
        for row in report['rows']:
            stem = 'ethics-long-' + row['profile'] + '-' + row['language']; name = stem + '-' + row['mode']
            source = PARENT / 'after/renders' / (stem + '.docx')
            target = ARCHIVE / 'word-diagnostic' / (name + '.docx'); pdf = target.with_suffix('.pdf')
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), row['source_sha256'])
            with tempfile.TemporaryDirectory() as folder:
                recreated = Path(folder) / 'copy.docx'; change(source, recreated, row['mode'])
                with zipfile.ZipFile(target) as a, zipfile.ZipFile(recreated) as b:
                    self.assertEqual(a.namelist(), b.namelist())
                    for n in a.namelist(): self.assertEqual(a.read(n), b.read(n))
            if row['mode'] == 'baseline':
                native = PARENT / 'after/word-preview' / (stem + '.pdf')
                self.assertEqual(geometry(pdf), geometry(native)); self.assertEqual(raster_digest(pdf), raster_digest(native))
            soup = BeautifulSoup((PARENT / 'after/renders' / (stem + '.html')).read_text(), 'html.parser')
            raw = subprocess.check_output(['pdftotext', '-raw', str(pdf), '-'], text=True)
            bbox = subprocess.check_output(['pdftotext', '-bbox-layout', str(pdf), '-'])
            pages = word_pages(raw, bbox); self.assertEqual(len(pages), row['pages'])
            xml = etree.fromstring(bbox); headers = []
            for index, page in enumerate(xml.findall('.//{*}page'), 1):
                words = page.findall('.//{*}word')
                a = [w for w in words if w.text == 'Item']; b = [w for w in words if w.text == 'Value']
                if a or b:
                    self.assertEqual((len(a), len(b)), (1, 1))
                    self.assertAlmostEqual(float(a[0].get('yMin')), float(b[0].get('yMin')), places=2)
                    self.assertLess(float(a[0].get('xMax')), float(b[0].get('xMin'))); headers.append(index)
                for w in words:
                    self.assertGreaterEqual(float(w.get('xMin')), 0); self.assertGreaterEqual(float(w.get('yMin')), 0)
                    self.assertLessEqual(float(w.get('xMax')), float(page.get('width')))
                    self.assertLessEqual(float(w.get('yMax')), float(page.get('height')))
            self.assertEqual(headers, row['positions']['Item']); self.assertEqual(headers, row['positions']['Value'])
            text = ''.join(pages); expected = compact(soup.body.get_text())
            counts = Counter(c for c in text if c not in {'•', '◦', '\uf0b7', '\uf0a1'})
            counts.subtract({'o': generated_o_markers(Document(target), bbox)})
            self.assertIn(len(headers), [1, 2]); counts.subtract({c: n * (len(headers)-1) for c, n in Counter('ItemValue').items()})
            self.assertEqual(counts, Counter(expected), name)
            if row['mode'] == 'both':
                self.assertEqual(len(headers), 1); self.assertEqual(headers, row['positions']['Retained.'])
        by_mode = {r['mode']: r for r in report['rows'] if (r['language'], r['profile']) == ('chinese', 'review')}
        self.assertEqual(by_mode['style-both']['positions'], by_mode['baseline']['positions'])
        self.assertEqual(by_mode['both']['positions']['Item'], [8])
        self.assertEqual({r['pages'] for r in by_mode.values()}, {10})


if __name__ == '__main__': unittest.main()
