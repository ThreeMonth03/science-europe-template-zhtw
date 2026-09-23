"""The prototype permits exactly nine reviewed pairs, never bulk retranslation."""
from collections import Counter
import copy
import importlib.util
import json
from pathlib import Path
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('preparation_builder', ROOT / 'experiments/reuse-preparation-prose/build_prototype.py')
builder = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(builder)


class PreparationBuilderTests(unittest.TestCase):
    def setUp(self):
        self.units = json.loads((ROOT / 'experiments/reuse-preparation-prose/units.json').read_text())
        retained = Counter({('keep ' + str(i), '保留 ' + str(i)): 1 for i in range(766)})
        self.old = retained + Counter((u['old_en'], u['old_zh']) for u in self.units)
        self.new = retained + Counter((u['en'], u['zh']) for u in self.units)

    def test_reviewed_delta(self):
        self.assertEqual(builder.translation_delta(self.old, self.new, self.units)['retained'], 766)

    def test_unrelated_translation_and_duplicate_rejected(self):
        for change in ['unrelated', 'duplicate', 'missing']:
            new = self.new.copy()
            if change == 'unrelated':
                new[('keep 0', '保留 0')] -= 1; new[('keep 0', '改掉')] += 1
            elif change == 'duplicate':
                new[(self.units[0]['en'], self.units[0]['zh'])] += 1
            else:
                new[(self.units[0]['en'], self.units[0]['zh'])] -= 1
            with self.subTest(change=change), self.assertRaises(AssertionError):
                builder.translation_delta(self.old, new, self.units)

    def packages(self):
        before = dict(organizationId='test', templateId='original', id='test:original:0.3.48', version='0.3.48',
                      name='Baseline', formats=[{'steps': ['unchanged']}], assets=[],
                      files=[dict(fileName=builder.QUESTION, content='before', uuid='baseline')])
        after = copy.deepcopy(before)
        after.update(templateId=builder.IDENTITY, id='test:' + builder.IDENTITY + ':' + builder.VERSION,
                     name=builder.NAMES['english'], version=builder.VERSION)
        after['files'][0].update(content='after', uuid=str(uuid.uuid5(uuid.NAMESPACE_URL,
            'dsw-template/' + after['id'] + '/files/' + builder.QUESTION)))
        return before, after

    def test_package_scope(self):
        before, after = self.packages()
        builder.compare_package(before, after, b'after', 'english')
        for key in ['formats', 'name', 'version']:
            changed = copy.deepcopy(after); changed[key] = [] if key == 'formats' else 'unexpected'
            with self.subTest(key=key), self.assertRaises(AssertionError):
                builder.compare_package(before, changed, b'after', 'english')
        with self.assertRaises(AssertionError):
            builder.compare_package(before, after, b'wrong packaged source', 'english')


if __name__ == '__main__': unittest.main()
