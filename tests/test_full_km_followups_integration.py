import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import full_km_followups_integration as contract
from probe_pdf_budget_translation import pair
from probe_personal_data_translation import project_full_km_followup_translations, verify_submission_translation_chain


class FullKmFollowupsIntegrationTests(unittest.TestCase):
    def test_current_translation_multiset_is_exactly_767_plus_six(self):
        current = [pair(p.read_text()) for p in (ROOT / 'translation/tree').rglob('translation.md')]
        previous, delta = project_full_km_followup_translations(current)
        self.assertEqual((len(previous), len(current), len(delta['added'])), (767, 773, 6))
        _, chain = verify_submission_translation_chain(current)
        self.assertEqual(chain['full_km_followups']['retained_units'], 767)
        self.assertEqual(chain['submission_reading']['retained_units'], 762)
        for mutation in [current[:-1], current + current[:1], current[1:] + [(current[0][0], 'WRONG')]]:
            with self.assertRaises(AssertionError): project_full_km_followup_translations(mutation)
        for added in map(tuple, delta['added']):
            mutation = list(current); mutation.remove(added); mutation.append((added[0], added[1] + '!'))
            with self.assertRaises(AssertionError): project_full_km_followup_translations(mutation)

    def test_public_fixtures_bind_every_file_to_sealed_prototype_receipts(self):
        for language in ['english', 'chinese']:
            expected = contract.CONTRACT['languages'][language]
            self.assertEqual(set(expected['added']), contract.ADDED)
            self.assertEqual(len(expected['changed']), 4)
            for phase, package in [('before', contract.baseline_package(language)),
                                    ('after', contract.prototype_package(language))]:
                for item in package['files']:
                    self.assertEqual(hashlib.sha256(item['content'].encode()).hexdigest(), expected[phase][item['fileName']])
                for name, digest in expected['asset_sha256'].items():
                    self.assertEqual(expected[phase][name.removeprefix('template/assets/')], digest)

    def test_projection_cannot_hide_unreviewed_files_assets_or_helpers(self):
        before = {'src/question.j2': b'old', 'src/font.ttf': b'font'}
        after = {**before, 'src/question.j2': b'new', **{n: b'helper' for n in contract.ADDED}}
        hashes = lambda values: {n: hashlib.sha256(v).hexdigest() for n, v in values.items()}
        expected = dict(before=hashes(before), after=hashes(after), changed=['src/question.j2'], added=sorted(contract.ADDED))
        old = dict(files=[dict(fileName='src/question.j2', content='old')])
        with patch.object(contract, 'CONTRACT', {'languages': {'english': expected}}), patch.object(contract, 'baseline_package', return_value=old):
            self.assertEqual(contract.project_sources(after, 'english'), before)
            for name in after:
                with self.assertRaises(AssertionError): contract.project_sources({**after, name: after[name] + b'!'}, 'english')
                with self.assertRaises(AssertionError): contract.project_sources({n: v for n, v in after.items() if n != name}, 'english')
            with self.assertRaises(AssertionError): contract.project_sources({**after, 'src/extra.j2': b''}, 'english')

    def test_actual_package_identity_is_not_discarded_by_projection(self):
        timestamp = '2026-09-22T00:00:00Z'
        for language in ['english', 'chinese']:
            candidate = contract.integrated_package(language, timestamp)
            self.assertEqual(contract.project_package(candidate, language, timestamp), contract.baseline_package(language))
            mutations = [lambda v: v.update(name='unexpected'), lambda v: v.update(version='0.3.47'),
                lambda v: v.update(updatedAt='wrong'), lambda v: v['assets'][0].update(uuid='wrong'),
                lambda v: v['files'][0].update(content=v['files'][0]['content'] + '!'),
                lambda v: v['files'][0].update(uuid='wrong'), lambda v: v['files'].pop(),
                lambda v: v['formats'][0]['steps'].pop(), lambda v: v['allowedPackages'].clear()]
            for mutate in mutations:
                value = copy.deepcopy(candidate); mutate(value)
                with self.assertRaises(AssertionError): contract.project_package(value, language, timestamp)


if __name__ == '__main__': unittest.main()
