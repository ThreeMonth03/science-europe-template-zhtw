import copy
from pathlib import Path
import subprocess
import sys
import unittest
from bs4 import BeautifulSoup
from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from word_budget_geometry import inspect, read_rows, line_text

ARCHIVE = ROOT / 'reviews/2026-09-21-mixed-boundary-controls'


class WordBudgetGeometryTests(unittest.TestCase):
    def test_every_original_cell_in_all_forty_native_previews(self):
        for phase in ['before', 'after']:
            for pdf in sorted((ARCHIVE / phase / 'word-preview').glob('*.pdf')):
                stem = pdf.stem
                with self.subTest(phase=phase, stem=stem):
                    renders = ARCHIVE / phase / 'renders'
                    r = inspect(renders / (stem + '.docx'), pdf, (renders / (stem + '.html')).read_text())
                    self.assertTrue(r['all_original_budget_cells_verified'])
                    self.assertFalse(r['layout_acceptance'] or r['microsoft_word_acceptance'])

    def test_geometry_proof_rejects_missing_changed_and_cross_column_text(self):
        stem = 'mixed-bound-33-last-review-chinese'
        soup = BeautifulSoup((ARCHIVE / 'after/renders' / (stem + '.html')).read_text(), 'html.parser')
        pdf = ARCHIVE / 'after/word-preview' / (stem + '.pdf')
        original = etree.fromstring(subprocess.check_output(['pdftotext', '-bbox-layout', str(pdf), '-']))
        for mode in ['delete', 'duplicate', 'punctuation', 'column', 'header', 'resource_order']:
            root = copy.deepcopy(original)
            if mode == 'header':
                line = next(l for l in root.findall('.//{*}page')[12].findall('.//{*}line') if line_text(l) == '經費來源')
                line.getparent().remove(line)
            elif mode == 'resource_order':
                lines = [l for l in root.findall('.//{*}line') if line_text(l) in ['邊界測試資源29', '邊界測試資源30']]
                words = [l.findall('{*}word')[-1] for l in lines]
                self.assertEqual(len(words), 2)
                words[0].text, words[1].text = words[1].text, words[0].text
            elif mode == 'column':
                line = next(l for l in root.findall('.//{*}line') if line_text(l) == '900TWD')
                line.set('xMin', '60'); line.set('xMax', '104')
            else:
                line = next(l for l in root.findall('.//{*}line') if 'MIX-LONG-09-PARA-07:' in line_text(l))
                if mode == 'delete': line.getparent().remove(line)
                elif mode == 'duplicate': line.getparent().append(copy.deepcopy(line))
                else: line.findall('{*}word')[0].text += '!'
            with self.subTest(mode=mode), self.assertRaises(AssertionError):
                read_rows(soup, etree.tostring(root), set())


if __name__ == '__main__': unittest.main()
