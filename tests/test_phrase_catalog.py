import json
import unittest
from pathlib import Path


class PhraseCatalogTests(unittest.TestCase):
    def test_reviewed_phrases_have_unique_source_keys(self):
        path = Path(__file__).resolve().parents[1] / 'docs/readability-phrases.json'
        pairs = json.loads(path.read_text(), object_pairs_hook=list)
        self.assertEqual(len(pairs), len({key for key, value in pairs}))
        self.assertTrue(all(isinstance(value, str) and value.strip() for key, value in pairs))
