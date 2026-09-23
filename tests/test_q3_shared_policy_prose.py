"""The new helper is the sole allowed package addition; all assets are frozen."""
import copy
import importlib.util
from pathlib import Path
import unittest
import uuid

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('q3_shared_build',ROOT/'experiments/q3-shared-policy-prose/build_prototype.py')
BUILD=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(BUILD)


class SharedPolicyPackageTests(unittest.TestCase):
    def sample(self,language='english'):
        before=dict(id='org:old:0.3.50',organizationId='org',templateId='old',version='0.3.50',name='Old',
            files=[dict(fileName=BUILD.QUESTION,uuid='q3',content='old'),dict(fileName='src/layout.css',uuid='css',content='unchanged')],
            assets=[dict(fileName='src/word/pilot.lua',uuid='lua',contentType='text/plain')],
            formats=[dict(name='PDF',steps=[dict(name='jinja',options={}),dict(name='weasyprint',options={})])])
        after=copy.deepcopy(before);tid=BUILD.IDENTITY+('-zhtw' if language=='chinese' else '')
        after.update(id='org:'+tid+':'+BUILD.VERSION,templateId=tid,version=BUILD.VERSION,name=BUILD.NAMES[language])
        after['files'][0]['content']='new'
        after['files'].append(dict(fileName=BUILD.HELPER,uuid='',content='helper'))
        for kind in ['files','assets']:
            for item in after[kind]:item['uuid']=str(uuid.uuid5(uuid.NAMESPACE_URL,f"dsw-template/{after['id']}/{kind}/{item['fileName']}"))
        return before,after

    def check(self,before,after,language='english'):
        BUILD.compare_package(before,after,{BUILD.QUESTION:b'new',BUILD.HELPER:b'helper'},language)

    def test_exact_addition_both_languages(self):
        for language in ['english','chinese']:self.check(*self.sample(language),language)

    def test_unrelated_asset_source_and_helper_mutations_rejected(self):
        before,after=self.sample();variants=[]
        for field,value in [('version','0.3.51'),('id',before['id']),('name','wrong')]:
            m=copy.deepcopy(after);m[field]=value;variants.append(m)
        for i in range(3):
            m=copy.deepcopy(after);m['files'][i]['content']+=' ';variants.append(m)
        m=copy.deepcopy(after);m['files'].pop();variants.append(m)
        m=copy.deepcopy(after);m['files'][-1]['extra']='unknown';variants.append(m)
        m=copy.deepcopy(after);m['files'].append(copy.deepcopy(m['files'][-1]));variants.append(m)
        m=copy.deepcopy(after);m['assets'][0]['contentType']='changed';variants.append(m)
        m=copy.deepcopy(after);m['formats'][0]['steps'][0]['options']['output_profile']='submission';variants.append(m)
        for m in variants:
            with self.assertRaises(AssertionError):self.check(before,m)


if __name__=='__main__':unittest.main()
