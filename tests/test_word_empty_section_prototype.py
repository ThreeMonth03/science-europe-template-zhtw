"""Prototype package identities cannot conceal unrelated Word/content changes."""
import copy,hashlib,importlib.util,json,sys,unittest,uuid
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[1]
def builder():
    path=ROOT/'experiments/word-empty-section-spacing/build_prototype.py'
    spec=importlib.util.spec_from_file_location('word_empty_sections_build',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

class WordEmptySectionPrototypeTests(unittest.TestCase):
    def test_package_identity_allowlist_rejects_other_edits(self):
        m=builder()
        before=dict(organizationId='org',templateId='base',id='org:base:0.3.49',version='0.3.49',name='Base',
            files=[dict(fileName='src/index.html.j2',uuid='old-file',content='original')],
            assets=[dict(fileName='src/word/question-spacing.lua',uuid='old-asset',contentType='application/octet-stream')],
            formats=[dict(uuid='same-format',steps=[dict(name='pandoc',options={'to':'docx'})])],createdAt='fixed')
        for language in ['english','chinese']:
            after=copy.deepcopy(before);after.update(templateId=m.IDENTITY+('-zhtw' if language=='chinese' else ''),name=m.NAMES[language])
            after['id']='org:'+after['templateId']+':0.3.49'
            for kind in ['files','assets']:
                for item in after[kind]:item['uuid']=str(uuid.uuid5(uuid.NAMESPACE_URL,f"dsw-template/{after['id']}/{kind}/{item['fileName']}"))
            m.compare_package(before,after,language)
            for mutate in [lambda v:v['files'][0].update(content='changed'),lambda v:v['assets'][0].update(contentType='text/plain'),
                lambda v:v['formats'][0]['steps'].clear(),lambda v:v.update(createdAt='changed'),
                lambda v:v.update(templateId='production'),lambda v:v['files'][0].update(uuid='arbitrary')]:
                bad=copy.deepcopy(after);mutate(bad)
                with self.assertRaises(AssertionError):m.compare_package(before,bad,language)

    def test_exact_sealed_baseline_and_separate_recipe_lock(self):
        config=yaml.safe_load((ROOT/'pipeline.yml').read_text())
        lock=json.loads((ROOT/'experiments/word-empty-section-spacing/lock.json').read_text())
        # The frozen prototype retains its historical source lock after integration.
        delta=json.loads((ROOT/'docs/word-empty-section-delta.json').read_text())
        self.assertEqual(delta['production_source_commit'],lock['production_source_commit'])
        self.assertEqual(delta['english_recipe_commit'],lock['english_recipe_commit'])
        self.assertEqual(config['source']['version'],delta['version'])
        self.assertEqual(config['tooling']['commit'],lock['tooling_commit'])
        self.assertTrue(lock['prototype_only'])
        self.assertRegex(lock['english_recipe_commit'],r'^[0-9a-f]{40}$')
        archive=ROOT/lock['baseline_review']
        digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        self.assertEqual(digest(archive/'checksums.json'),lock['baseline_review_seal'])
        for row in json.loads((archive/'checksums.json').read_text())['files']:
            self.assertEqual(digest(archive/row['path']),row['sha256'])
        m=builder();self.assertEqual(m.CHANGED,{'src/word/question-spacing.lua','src/word/question-spacing.xml'})

if __name__=='__main__':unittest.main()
