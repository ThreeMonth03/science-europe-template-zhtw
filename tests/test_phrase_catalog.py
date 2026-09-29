import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from probe_pdf_budget_translation import pair


class PhraseCatalogTests(unittest.TestCase):
    def test_reviewed_phrases_have_unique_source_keys(self):
        path = Path(__file__).resolve().parents[1] / 'docs/readability-phrases.json'
        pairs = json.loads(path.read_text(), object_pairs_hook=list)
        self.assertEqual(len(pairs), len({key for key, value in pairs}))
        self.assertTrue(all(isinstance(value, str) and value.strip() for key, value in pairs))

    def test_risk_combinations_are_fully_localized(self):
        expected = {
            'data loss, data disclosure, and data tampering': '資訊遺失、資訊外洩與資訊遭竄改',
            'data loss and data disclosure': '資訊遺失與資訊外洩',
            'data loss and data tampering': '資訊遺失與資訊遭竄改',
            'data disclosure and data tampering': '資訊外洩與資訊遭竄改',
        }
        actual = {}
        root = ROOT / 'translation/tree/src/questions/06-access-security.html.j2'
        for path in root.rglob('translation.md'):
            source, target = pair(path.read_text())
            if source in expected:
                actual[source] = target
        self.assertEqual(expected, actual)
