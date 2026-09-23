"""New package validation must precede any historical source/translation view."""
from collections import Counter
import copy
import hashlib
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import reuse_preparation_integration as contract
import empty_section_spacing_integration as old
from probe_pdf_budget_translation import pair


class PreparationIntegrationTests(unittest.TestCase):
    def test_exact_translation_delta_and_mutations(self):
        current = [pair(p.read_text()) for p in (ROOT / 'translation/tree').rglob('translation.md')]
        previous, delta = contract.project_translations(current)
        self.assertEqual(len(previous), 775); self.assertEqual(delta['retained_units'], 766)
        self.assertTrue(contract.has_new_translations(current)); self.assertFalse(contract.has_new_translations(previous))
        for unit in contract.units():
            changed = list(current); changed.remove((unit['en'], unit['zh'])); changed.append((unit['en'], unit['zh'] + '!'))
            with self.assertRaises(AssertionError): contract.project_translations(changed)
        for changed in [current[:-1], current + current[:1], current[1:] + [(current[0][0], 'wrong')]]:
            with self.assertRaises(AssertionError): contract.project_translations(changed)

    def test_actual_fixture_and_full_metadata_before_old_projection(self):
        for language in ['english', 'chinese']:
            self.assertEqual(hashlib.sha256(contract.question(language)).hexdigest(), contract.CONTRACT['languages'][language]['after'][contract.QUESTION])
            timestamp = '2026-09-23T00:00:00Z'
            candidate = contract.integrated_package(language, timestamp)
            self.assertEqual(contract.project_package(candidate, language, timestamp), old.integrated_package(language, timestamp))
            for mutate in [lambda v: v.update(version='999.0.0'), lambda v: v.update(templateId='prototype'),
                lambda v: v['files'][0].update(content='wrong'), lambda v: v['files'][0].update(uuid='wrong'),
                lambda v: v['assets'].pop(), lambda v: v['formats'][-1]['steps'].pop(),
                lambda v: v.update(createdAt='wrong'), lambda v: v['allowedPackages'].clear()]:
                bad = copy.deepcopy(candidate); mutate(bad)
                with self.assertRaises(AssertionError): contract.project_package(bad, language, timestamp)

    def test_all_prepared_bytes_required_before_projection(self):
        before = {contract.QUESTION: b'old', 'src/layout.css': b'css', 'src/font.ttf': b'font'}
        after = {**before, contract.QUESTION: b'new'}
        hashes = lambda values: {n: hashlib.sha256(v).hexdigest() for n, v in values.items()}
        record = dict(languages=dict(english=dict(before=hashes(before), after=hashes(after))))
        with patch.object(contract, 'CONTRACT', record), patch.object(contract, 'question', return_value=b'new'), patch.object(
                old, 'integrated_package', return_value={'files': [dict(fileName=contract.QUESTION, content='old')]}):
            self.assertEqual(contract.project_sources(after, 'english'), before)
            for name in after:
                with self.assertRaises(AssertionError): contract.project_sources({**after, name: after[name] + b'!'}, 'english')
                with self.assertRaises(AssertionError): contract.project_sources({n: v for n, v in after.items() if n != name}, 'english')
            with self.assertRaises(AssertionError): contract.project_sources({**after, 'src/extra': b''}, 'english')


if __name__ == '__main__': unittest.main()
