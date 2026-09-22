import copy,importlib.util,uuid
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('empty_section_builder',ROOT/'experiments/empty-section-spacing/build_prototype.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)

class EmptySectionBuilderTests(unittest.TestCase):
    def test_only_css_and_prototype_identity_are_allowed(self):
        for language in ['english','chinese']:
            old={
                'organizationId':'threemonth03','templateId':'science-europe-enhanced'+('-zhtw' if language=='chinese' else ''),
                'name':'baseline','version':'0.3.47','id':'baseline-id','createdAt':'fixed','updatedAt':'fixed',
                'files':[{'fileName':'src/layout.css','content':'old CSS','uuid':'css-id'},
                         {'fileName':'src/content.html.j2','content':'original questions','uuid':'jinja-id'}],
                'assets':[{'fileName':'src/font.ttf','uuid':'font-id'}],
                'formats':[{'uuid':'original-format','steps':[{'name':'original-step'}]}]}
            new=copy.deepcopy(old)
            new.update(templateId='science-europe-empty-section-prototype'+('-zhtw' if language=='chinese' else ''),
                version='0.3.48',name='Science Europe 空節間距原型（非提交版）' if language=='chinese' else 'Science Europe — empty section spacing prototype (not for submission)')
            new['id']='threemonth03:'+new['templateId']+':0.3.48';new['files'][0]['content']+='\nnew CSS'
            for kind in ['files','assets']:
                for item in new[kind]:item['uuid']=str(uuid.uuid5(uuid.NAMESPACE_URL,f"dsw-template/{new['id']}/{kind}/{item['fileName']}"))
            builder.compare_package(old,new,b'\nnew CSS')
            for mutate in [lambda x:x['files'][0].update(content='wrong'),lambda x:x['files'][1].update(content='missing question'),
                lambda x:x['formats'][0]['steps'].append({'name':'unapproved'}),lambda x:x['assets'].clear(),
                lambda x:x.update(name='production'),lambda x:x.update(updatedAt='different'),
                lambda x:x['files'][0].update(uuid='wrong')]:
                bad=copy.deepcopy(new);mutate(bad)
                with self.assertRaises(AssertionError):builder.compare_package(old,bad,b'\nnew CSS')

if __name__=='__main__':unittest.main()
