import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
import hashlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from check_budget_grouping_integration import ARCHIVE, asset_uuid, project_metadata, check_package


class BudgetGroupingIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.before = json.loads((ARCHIVE / 'package/after-chinese.json').read_text())
        self.after = copy.deepcopy(self.before)
        self.after['version'] = '0.3.43'
        self.after['id'] = self.after['id'].removesuffix('0.3.42') + '0.3.43'
        self.timestamp = '2026-09-21T00:00:00Z'
        self.after['createdAt'] = self.after['updatedAt'] = self.timestamp
        for kind in ['files', 'assets']:
            for item in self.after[kind]:
                item['uuid'] = asset_uuid(self.after['id'], kind, item['fileName'])

    def test_only_deterministic_revision_metadata_is_projected(self):
        self.assertEqual(project_metadata(self.after, self.before, self.timestamp), self.before)

    def test_content_format_and_identity_mutations_fail(self):
        def content(data): data['files'][0]['content'] += 'unexpected'
        def file_uuid(data): data['files'][0]['uuid'] = self.before['files'][0]['uuid']
        def asset(data): data['assets'][0]['uuid'] = self.before['assets'][0]['uuid']
        def format_uuid(data): data['formats'][0]['uuid'] = 'unreviewed'
        def timestamp(data): data['updatedAt'] = '2026-09-22T00:00:00Z'
        def duplicate(data): data['files'][1] = copy.deepcopy(data['files'][0])
        for mutation in [content, file_uuid, asset, format_uuid, timestamp, duplicate]:
            with self.subTest(mutation=mutation.__name__):
                candidate = copy.deepcopy(self.after); mutation(candidate)
                with self.assertRaises(AssertionError): project_metadata(candidate, self.before, self.timestamp)

    def test_asset_bytes_and_member_set_are_not_ignored(self):
        member = 'template/assets/frozen-font.ttf'
        members = {'template/template.json': 'metadata-is-checked-separately', member: hashlib.sha256(b'original').hexdigest()}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'package.zip'
            for font, extra, passed in [(b'original', False, True), (b'changed', False, False), (b'original', True, False)]:
                with zipfile.ZipFile(path, 'w') as package:
                    package.writestr('template/template.json', json.dumps(self.after))
                    package.writestr(member, font)
                    if extra: package.writestr('unexpected.txt', 'extra')
                if passed:
                    self.assertTrue(check_package(path, self.before, members, self.timestamp)['content_and_asset_bytes_identical'])
                else:
                    with self.assertRaises(AssertionError): check_package(path, self.before, members, self.timestamp)


if __name__ == '__main__': unittest.main()
