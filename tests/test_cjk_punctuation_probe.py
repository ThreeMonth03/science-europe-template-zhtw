"""Fail closed on anything outside the owned Q3 prototype scope."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('cjk_build', ROOT/'experiments/cjk-punctuation-probe/build_prototype.py')
BUILD = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(BUILD)


class CjkPrototypeTests(unittest.TestCase):
    def sample(self, language='english'):
        before = dict(id='org:old:0.3.50', organizationId='org', templateId='old', version='0.3.50', name='Old',
            files=[dict(fileName=BUILD.QUESTION, uuid='q3', content='old'),
                   dict(fileName='src/layout.css', uuid='css', content='unchanged')],
            assets=[dict(fileName='src/word/pilot.lua', uuid='lua', contentType='text/plain')],
            formats=[dict(name='PDF', steps=[dict(name='jinja', options={}), dict(name='weasyprint', options={})])])
        after = copy.deepcopy(before)
        tid = BUILD.IDENTITY + ('-zhtw' if language == 'chinese' else '')
        after.update(id='org:'+tid+':'+BUILD.VERSION, templateId=tid, version=BUILD.VERSION, name=BUILD.NAMES[language])
        after['files'][0]['content'] = 'new'
        for kind in ['files', 'assets']:
            for item in after[kind]:
                item['uuid'] = str(uuid.uuid5(uuid.NAMESPACE_URL, f"dsw-template/{after['id']}/{kind}/{item['fileName']}"))
        return before, after

    def test_exact_package_scope_both_languages(self):
        for language in ['english', 'chinese']:
            before, after = self.sample(language)
            BUILD.compare_package(before, after, b'new', language)

    def test_unrelated_mutations_are_rejected(self):
        before, after = self.sample()
        variants = []
        for field, value in [('id', before['id']), ('name', before['name']), ('version', '0.3.51')]:
            changed = copy.deepcopy(after); changed[field] = value; variants.append(changed)
        changed = copy.deepcopy(after); changed['files'][1]['content'] += ' '; variants.append(changed)
        changed = copy.deepcopy(after); changed['files'][0]['content'] += ' '; variants.append(changed)
        changed = copy.deepcopy(after); changed['assets'][0]['contentType'] = 'application/octet-stream'; variants.append(changed)
        changed = copy.deepcopy(after); changed['files'][0]['uuid'] = 'wrong'; variants.append(changed)
        changed = copy.deepcopy(after); changed['formats'][0]['steps'][0]['options']['output_profile'] = 'submission'; variants.append(changed)
        for changed in variants:
            with self.assertRaises(AssertionError): BUILD.compare_package(before, changed, b'new', 'english')

    def test_translation_files_are_exact_not_just_visible_words(self):
        with tempfile.TemporaryDirectory() as folder:
            roots = [Path(folder)/name for name in ['old', 'new']]
            for root in roots:
                for i in range(775):
                    p = root/str(i)/'translation.md'; p.parent.mkdir(parents=True); p.write_text('fixed\n')
            self.assertEqual(BUILD.translation_unchanged(*roots)['byte_identical'], 775)
            (roots[1]/'0/translation.md').write_text('fixed\n<!-- metadata drift -->\n')
            with self.assertRaises(AssertionError): BUILD.translation_unchanged(*roots)


if __name__ == '__main__': unittest.main()
