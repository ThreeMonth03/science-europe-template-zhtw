import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import submission_preview_integration as contract
from probe_pdf_budget_translation import pair
from probe_personal_data_translation import verify_submission_translation_chain
from check_budget_grouping_integration import project_metadata, asset_uuid


class SubmissionIntegrationTests(unittest.TestCase):
    def test_every_old_translation_survives_and_machine_kinds_are_not_translatable(self):
        pairs = [pair(p.read_text()) for p in (ROOT / 'translation/tree').rglob('translation.md')]
        _, chain = verify_submission_translation_chain(pairs)
        delta = chain['submission_preview']
        self.assertEqual((delta['baseline_units'], delta['current_units'], delta['retained_units']), (748, 762, 748))
        self.assertEqual(delta['removed'], [])
        self.assertFalse({'instrument', 'reference', 'non-reference', 'non-equipment', 'produced'} & {en for en, _ in pairs})
        self.assertEqual(len(delta['added']), 14)

    def test_prepared_projection_rejects_any_extra_missing_or_modified_byte(self):
        digest = lambda value: hashlib.sha256(value).hexdigest()
        before = {'src/question.j2': b'old', 'src/font.ttf': b'font'}
        after = {**before, 'src/question.j2': b'new'}
        expected = {'before': {n: digest(v) for n, v in before.items()},
                    'after': {n: digest(v) for n, v in after.items()}, 'changed': ['src/question.j2']}
        package = {'files': [{'fileName': 'src/question.j2', 'content': 'old'}]}
        with tempfile.TemporaryDirectory() as folder, patch.object(contract, 'CONTRACT', {'languages': {'english': expected}}), patch.object(contract, 'frozen_package', return_value=package):
            root = Path(folder); (root / 'src').mkdir()
            for name, value in after.items(): (root / name).write_bytes(value)
            self.assertEqual(contract.verified_sources(root, 'english'), (after, before))
            for name in after:
                (root / name).write_bytes(after[name] + b'!')
                with self.assertRaises(AssertionError): contract.verified_sources(root, 'english')
                (root / name).write_bytes(after[name])
            (root / 'src/unreviewed.j2').write_bytes(b'')
            with self.assertRaises(AssertionError): contract.verified_sources(root, 'english')
            (root / 'src/unreviewed.j2').unlink()
            (root / 'src/font.ttf').unlink()
            with self.assertRaises(AssertionError): contract.verified_sources(root, 'english')

    def test_new_version_does_not_exempt_format_timestamp_uuid_or_content(self):
        baseline = contract.frozen_package('english')
        candidate = copy.deepcopy(baseline); timestamp = '2026-09-21T00:00:00Z'
        candidate['version'] = '0.3.44'
        candidate['id'] = baseline['id'].removesuffix('0.3.43') + '0.3.44'
        candidate['createdAt'] = candidate['updatedAt'] = timestamp
        for kind in ['files', 'assets']:
            for item in candidate[kind]: item['uuid'] = asset_uuid(candidate['id'], kind, item['fileName'])
        self.assertEqual(project_metadata(candidate, baseline, timestamp, versions=('0.3.43', '0.3.44')), baseline)
        mutations = [lambda v: v.update(updatedAt='wrong'),
            lambda v: v['files'][0].update(uuid='wrong'),
            lambda v: v['files'][0].update(content=v['files'][0]['content'] + '!'),
            lambda v: v['formats'][0].update(name='wrong')]
        for mutate in mutations:
            value = copy.deepcopy(candidate); mutate(value)
            with self.assertRaises(AssertionError): project_metadata(value, baseline, timestamp, versions=('0.3.43', '0.3.44'))

    def test_prepared_baseline_matches_sealed_native_package(self):
        for language in ['english', 'chinese']:
            expected = contract.CONTRACT['languages'][language]
            self.assertEqual(len(expected['changed']), 21)
            for item in contract.frozen_package(language)['files']:
                self.assertEqual(hashlib.sha256(item['content'].encode()).hexdigest(), expected['before'][item['fileName']])
