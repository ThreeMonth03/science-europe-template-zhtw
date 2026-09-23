"""The two reviewed Word helpers never authorize unrelated source/package edits."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import word_empty_section_integration as contract
import reuse_preparation_integration as old

class WordSectionIntegrationTests(unittest.TestCase):
    def test_sealed_fixtures_and_unchanged_translation_tree(self):
        before, after = contract.helpers('before'), contract.helpers('after')
        self.assertEqual(set(before), {'src/word/question-spacing.lua', 'src/word/question-spacing.xml'})
        self.assertEqual(set(before), set(after)); self.assertTrue(all(before[n] != after[n] for n in before))
        for language in ['english', 'chinese']:
            for name, value in before.items():
                self.assertEqual(hashlib.sha256(value).hexdigest(), old.CONTRACT['languages'][language]['after'][name])
        manifest = json.loads((contract.archive('baseline') / 'build-manifest.json').read_text())
        tree = {str(p.relative_to(ROOT / 'translation')):contract.sha(p) for p in (ROOT / 'translation/tree').rglob('translation.md')}
        self.assertEqual(len(tree), 775); self.assertEqual(tree, manifest['translation_tree_sha256'])

    def test_metadata_projection_rejects_unreviewed_changes(self):
        timestamp = '2026-09-23T00:00:00Z'
        for language in ['english', 'chinese']:
            candidate = contract.integrated_package(language, timestamp)
            self.assertEqual(contract.project_package(candidate, language, timestamp), old.integrated_package(language, timestamp))
            for mutate in [lambda v:v.update(version='999.0.0'), lambda v:v.update(templateId='prototype'),
                lambda v:v['files'][0].update(content='wrong'), lambda v:v['assets'][0].update(uuid='wrong'),
                lambda v:v['assets'].pop(), lambda v:v['formats'][-1]['steps'].pop(),
                lambda v:v.update(createdAt='wrong'), lambda v:v['allowedPackages'].clear()]:
                bad=copy.deepcopy(candidate); mutate(bad)
                with self.assertRaises(AssertionError): contract.project_package(bad, language, timestamp)

    def test_all_prepared_bytes_checked_before_old_view(self):
        before={**contract.helpers('before'),'src/layout.css':b'css','src/font.ttf':b'font'}
        after={**before,**contract.helpers('after')}
        record={'languages':{'english':{'after':{n:hashlib.sha256(v).hexdigest() for n,v in before.items()}}}}
        with patch.object(old,'CONTRACT',record):
            self.assertEqual(contract.project_sources(after,'english'),before)
            self.assertTrue(contract.needs_projection(after)); self.assertFalse(contract.needs_projection(before))
            for name in after:
                with self.assertRaises(AssertionError): contract.project_sources({**after,name:after[name]+b'!'},'english')
                with self.assertRaises(AssertionError): contract.project_sources({n:v for n,v in after.items() if n!=name},'english')
            with self.assertRaises(AssertionError): contract.project_sources({**after,'src/extra':b''},'english')

if __name__ == '__main__': unittest.main()
