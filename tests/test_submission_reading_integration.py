import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import submission_reading_integration as contract
from probe_pdf_budget_translation import pair
from probe_personal_data_translation import project_submission_reading_translations, verify_submission_translation_chain
from check_budget_grouping_integration import project_metadata, asset_uuid


class SubmissionReadingIntegrationTests(unittest.TestCase):
    def test_exact_translation_delta_keeps_all_762_occurrences(self):
        current = [pair(p.read_text()) for p in (ROOT / 'translation/tree').rglob('translation.md')]
        previous, delta = project_submission_reading_translations(current)
        self.assertEqual((len(previous), len(current), len(delta['added'])), (762, 767, 5))
        self.assertEqual(delta['removed'], [])
        _, chain = verify_submission_translation_chain(current)
        self.assertEqual(chain['submission_preview']['retained_units'], 748)
        self.assertEqual(chain['submission_reading']['retained_units'], 762)
        for mutation in [current[:-1], current + [('extra', '額外')], [(s, t + '!') for s, t in current]]:
            with self.assertRaises(AssertionError): project_submission_reading_translations(mutation)
        for added in map(tuple, delta['added']):
            changed = list(current); changed.remove(added)
            changed.append((added[0], added[1] + '。'))
            with self.assertRaises(AssertionError): project_submission_reading_translations(changed)

    def test_frozen_full_source_packages_match_every_declared_jinja_and_asset(self):
        for language in ['english', 'chinese']:
            expected = contract.CONTRACT['languages'][language]
            self.assertEqual(len(expected['changed']), 5)
            self.assertEqual(set(expected['added']), contract.ADDED)
            for phase, prototype in [('before', False), ('after', True)]:
                for item in contract.frozen_package(language, prototype)['files']:
                    self.assertEqual(hashlib.sha256(item['content'].encode()).hexdigest(), expected[phase][item['fileName']])
            assets = contract.frozen('source-rehearsal/source-build.json')['packages'][language]['asset_sha256']
            for name, digest in assets.items():
                self.assertEqual(expected['after'][name.removeprefix('template/assets/')], digest)

    def test_projection_rejects_even_one_asset_or_source_byte_and_inventory_drift(self):
        from unittest.mock import patch
        before = {'src/question.j2': b'old', 'src/font.ttf': b'font'}
        for i in range(4): before[f'src/{i}.j2'] = b'old'
        after = {n: b'new' if n.endswith('.j2') else v for n, v in before.items()}
        after.update({n: b'helper' for n in contract.ADDED})
        hashes = lambda values: {n: hashlib.sha256(v).hexdigest() for n, v in values.items()}
        expected = dict(before=hashes(before), after=hashes(after),
                        changed=sorted(n for n in before if n.endswith('.j2')), added=sorted(contract.ADDED))
        baseline = {'files': [dict(fileName=n, content=v.decode()) for n, v in before.items() if n.endswith('.j2')]}
        with patch.object(contract, 'CONTRACT', {'languages': {'english': expected}}), patch.object(contract, 'frozen_package', return_value=baseline):
            self.assertEqual(contract.project_sources(after, 'english'), before)
            for name in after:
                with self.assertRaises(AssertionError): contract.project_sources({**after, name: after[name] + b'!'}, 'english')
                with self.assertRaises(AssertionError): contract.project_sources({n: v for n, v in after.items() if n != name}, 'english')
            with self.assertRaises(AssertionError): contract.project_sources({**after, 'src/extra.xml': b''}, 'english')

    def test_new_version_validates_canonical_ids_steps_and_entire_content(self):
        for language in ['english', 'chinese']:
            baseline = contract.frozen_package(language)
            candidate = copy.deepcopy(baseline); timestamp = '2026-09-22T00:00:00Z'
            candidate['version'] = '0.3.45'; candidate['id'] = baseline['id'].removesuffix('0.3.44') + '0.3.45'
            candidate['createdAt'] = candidate['updatedAt'] = timestamp
            for kind in ['files', 'assets']:
                for item in candidate[kind]: item['uuid'] = asset_uuid(candidate['id'], kind, item['fileName'])
            self.assertEqual(project_metadata(candidate, baseline, timestamp, versions=('0.3.44', '0.3.45')), baseline)
            mutations = [lambda v: v.update(updatedAt='wrong'),
                lambda v: v['assets'][0].update(uuid='wrong'),
                lambda v: v['files'][0].update(content=v['files'][0]['content'] + '!'),
                lambda v: next(f for f in v['formats'] if f['steps'][-1]['name'] == 'enrich-docx')['steps'].pop()]
            for mutate in mutations:
                value = copy.deepcopy(candidate); mutate(value)
                with self.assertRaises(AssertionError): project_metadata(value, baseline, timestamp, versions=('0.3.44', '0.3.45'))


if __name__ == '__main__': unittest.main()
