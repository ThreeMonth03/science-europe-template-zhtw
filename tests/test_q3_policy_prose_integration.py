"""Paired Q3 integration must retain every unreviewed byte and older proof."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import q3_policy_prose_integration as contract
import word_empty_section_integration as previous
import current_source_repairs as current_contract
from check_budget_grouping_integration import asset_uuid

class Q3IntegrationTests(unittest.TestCase):
    def test_locale_only_source_scope_is_explicit_and_does_not_expand_english(self):
        delta = dict(changed=['src/questions/02-what-data.html.j2'], languages={
            'english': {}, 'chinese': {'additional_changed': ['src/style.css']}})
        with patch.object(current_contract, 'CONTRACT', delta):
            self.assertEqual(current_contract.changed_sources('english'), delta['changed'])
            self.assertEqual(current_contract.changed_sources('chinese'),
                             ['src/questions/02-what-data.html.j2', 'src/style.css'])
            for invalid in [['src/style.css', 'src/style.css'], delta['changed'],
                            ['src/z.css', 'src/a.css']]:
                delta['languages']['chinese']['additional_changed'] = invalid
                with self.assertRaises(AssertionError):
                    current_contract.changed_sources('chinese')

    def test_metadata_gap_view_changes_only_verified_question_and_rejects_drift(self):
        from submission_flow_integration import sources
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'current'
            question=source/contract.QUESTION;question.parent.mkdir(parents=True)
            question.write_text('current wording')
            (source/'src/style.css').write_text('current style')
            original=sources(source)
            historical={**original,contract.QUESTION:b'frozen wording'}
            view=Path(folder)/'view'
            with patch.object(contract,'current_q3_sources',return_value=historical) as verifier:
                proof=current_contract.metadata_gap_view(source,'chinese',view)
            verifier.assert_called_once_with(original,'chinese')
            self.assertEqual(sources(view),historical)
            self.assertEqual(sources(source),original)
            self.assertTrue(proof['historical_scope'])
            self.assertFalse(proof['view_is_package'])
            rejected=Path(folder)/'rejected'
            with patch.object(contract,'current_q3_sources',side_effect=AssertionError('source drift')):
                with self.assertRaises(AssertionError):current_contract.metadata_gap_view(source,'chinese',rejected)
            self.assertFalse(rejected.exists())

    def current_candidate(self,language,timestamp):
        historical=contract.integrated_package(language,timestamp)
        candidate=copy.deepcopy(historical)
        candidate['version']='0.3.52'
        candidate['id']=historical['id'].removesuffix('0.3.51')+'0.3.52'
        changed=candidate['files'][0]['fileName']
        candidate['files'][0]['content']+='\ncurrent candidate content'
        added='src/current-version-test.j2'
        candidate['files'].append(dict(fileName=added,content='current helper',uuid=''))
        for kind in ['files','assets']:
            for item in candidate[kind]:item['uuid']=asset_uuid(candidate['id'],kind,item['fileName'])
        delta=dict(candidate_version='0.3.52',baseline_version='0.3.51',release_approved=False,
            added=[added],changed=[changed],languages={language:{}})
        delta['languages'][language]['candidate_metadata_sha256']=self.metadata_seal(candidate)
        return historical,candidate,delta

    def metadata_seal(self,value):
        normalized=copy.deepcopy(value)
        normalized['createdAt']=normalized['updatedAt']='<timestamp>'
        return hashlib.sha256(json.dumps(normalized,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

    def test_435_language_requires_a_separate_complete_seal(self):
        timestamp = '2000-01-01T00:00:00Z'
        for language, code in [('english', 'en'), ('chinese', 'zh-Hant')]:
            historical, candidate, delta = self.current_candidate(language, timestamp)
            candidate['language'] = code
            with patch.object(current_contract, 'CONTRACT', delta), self.assertRaises(AssertionError):
                current_contract.project_package(candidate, language, timestamp, historical)
            delta['languages'][language]['candidate_metadata_435_sha256'] = self.metadata_seal(candidate)
            with patch.object(current_contract, 'CONTRACT', delta):
                self.assertEqual(current_contract.project_package(candidate, language, timestamp, historical)[0], historical)
                for key, value in [('language', 'wrong'), ('readme', 'unreviewed content')]:
                    bad = copy.deepcopy(candidate); bad[key] = value
                    with self.assertRaises(AssertionError):
                        current_contract.project_package(bad, language, timestamp, historical)
            bad = copy.deepcopy(candidate); bad['language'] = 'wrong'
            delta['languages'][language]['candidate_metadata_435_sha256'] = self.metadata_seal(bad)
            with patch.object(current_contract, 'CONTRACT', delta), self.assertRaises(AssertionError):
                current_contract.project_package(bad, language, timestamp, historical)

    def test_registered_lua_asset_and_exact_prefix_project_without_hiding_drift(self):
        timestamp='2000-01-01T00:00:00Z'
        steps=[{'name':'jinja','options':{'template':'src/answer-markdown-inputs.html.j2',
            'content-type':'text/html','extension':'html'}},
            {'name':'pandoc','options':{'from':'html','to':'html',
                'args':'--lua-filter=src/answer-markdown.lua --wrap=none'}}]
        english=SimpleNamespace(answer_markdown_steps=lambda:copy.deepcopy(steps))
        for language in ['english','chinese']:
            historical,candidate,delta=self.current_candidate(language,timestamp)
            name='src/answer-markdown.lua'
            candidate['assets'].append(dict(fileName=name,contentType='text/x-lua',
                uuid=asset_uuid(candidate['id'],'assets',name)))
            candidate['assets'].sort(key=lambda item:item['fileName'])
            delta['added']=sorted(delta['added']+[name]);delta['added_assets']=[name]
            delta['answer_markdown_prefix']=True
            for fmt in candidate['formats']:fmt['steps'][:0]=copy.deepcopy(steps)
            delta['languages'][language]['candidate_metadata_sha256']=self.metadata_seal(candidate)
            original=copy.deepcopy(candidate)
            with patch.dict(sys.modules,{'current_repairs_contract':english}),patch.object(current_contract,'CONTRACT',delta):
                self.assertEqual(current_contract.project_package(candidate,language,timestamp,historical)[0],historical)
            self.assertEqual(candidate,original)
            for change in ['added_asset','old_asset','asset_uuid','suffix']:
                bad=copy.deepcopy(candidate)
                asset=next(item for item in bad['assets'] if item['fileName']==name)
                if change=='added_asset':
                    asset['fileName']='src/unreviewed.lua'
                    asset['uuid']=asset_uuid(bad['id'],'assets',asset['fileName'])
                elif change=='old_asset':
                    next(item for item in bad['assets'] if item['fileName']!=name)['contentType']='unreviewed/type'
                elif change=='asset_uuid':asset['uuid']='wrong'
                else:bad['formats'][0]['steps'][2]['options']['template']='src/unreviewed-entry.j2'
                sealed=copy.deepcopy(delta)
                sealed['languages'][language]['candidate_metadata_sha256']=self.metadata_seal(bad)
                with self.subTest(language=language,change=change),patch.dict(sys.modules,{'current_repairs_contract':english}),\
                     patch.object(current_contract,'CONTRACT',sealed),self.assertRaises(AssertionError):
                    current_contract.project_package(bad,language,timestamp,historical)

    def test_zip_members_and_asset_bytes_follow_only_sealed_current_metadata(self):
        timestamp='2000-01-01T00:00:00Z'
        for language in ['english','chinese']:
            historical,candidate,delta=self.current_candidate(language,timestamp)
            name='src/answer-markdown.lua'
            candidate['assets'].append(dict(fileName=name,contentType='text/x-lua',
                uuid=asset_uuid(candidate['id'],'assets',name)))
            delta['added']=sorted(delta['added']+[name]);delta['added_assets']=[name]
            delta['languages'][language]['candidate_metadata_sha256']=self.metadata_seal(candidate)
            current={item['fileName']:item['content'].encode() for item in candidate['files']}
            current.update({item['fileName']:b'sealed fixture asset' for item in candidate['assets']})
            with tempfile.TemporaryDirectory() as folder:
                path=Path(folder)/'candidate.zip'
                with zipfile.ZipFile(path,'w') as package:
                    package.writestr('template/template.json',json.dumps(candidate))
                    for item in candidate['assets']:
                        package.writestr('template/assets/'+item['fileName'],current[item['fileName']])
                with patch.object(current_contract,'CONTRACT',delta),patch.object(contract,'project_sources') as verify_sources,\
                     patch('submission_flow_integration.sources',return_value=current):
                    self.assertTrue(contract.check_package(path,Path(folder),language,timestamp)['historical_projection_verified'])
                    verify_sources.assert_called_once_with(current,language)
                with zipfile.ZipFile(path,'a') as package:
                    package.writestr('template/assets/unreviewed.lua',b'unreviewed')
                with patch.object(current_contract,'CONTRACT',delta),patch.object(contract,'project_sources'),\
                     patch('submission_flow_integration.sources',return_value=current),self.assertRaises(AssertionError):
                    contract.check_package(path,Path(folder),language,timestamp)

    def test_registered_current_identity_composes_without_changing_frozen_packages(self):
        from submission_flow_integration import project_package,package
        timestamp='2000-01-01T00:00:00Z'
        for language in ['english','chinese']:
            historical,candidate,delta=self.current_candidate(language,timestamp)
            with patch.object(current_contract,'CONTRACT',delta):
                restored,proof=current_contract.project_package(candidate,language,timestamp,historical)
                self.assertEqual(restored,historical)
                self.assertEqual((proof['candidate_version'],proof['historical_version']),('0.3.52','0.3.51'))
                self.assertTrue(current_contract.is_q3_version('0.3.51'))
                self.assertTrue(current_contract.is_q3_version('0.3.52'))
                self.assertFalse(current_contract.is_q3_version('0.3.53'))
                self.assertEqual(contract.project_package(candidate,language,timestamp),previous.integrated_package(language,timestamp))
                self.assertEqual(project_package(candidate,language,timestamp),package(language))
            self.assertEqual(candidate['version'],'0.3.52')

    def test_current_identity_projection_rejects_sealed_version_id_uuid_and_format_drift(self):
        timestamp='2000-01-01T00:00:00Z'
        for language in ['english','chinese']:
            historical,candidate,delta=self.current_candidate(language,timestamp)
            for mutate in [lambda v:v.update(version='0.3.53'),lambda v:v.update(id='wrong:identity:0.3.52'),
                lambda v:v['files'][0].update(uuid='wrong'),lambda v:v['assets'][0].update(uuid='wrong'),
                lambda v:v['formats'][-1]['steps'].pop()]:
                bad=copy.deepcopy(candidate);mutate(bad)
                altered_delta=copy.deepcopy(delta)
                altered_delta['languages'][language]['candidate_metadata_sha256']=self.metadata_seal(bad)
                with patch.object(current_contract,'CONTRACT',altered_delta),self.assertRaises(AssertionError):
                    current_contract.project_package(bad,language,timestamp,historical)
            bad=copy.deepcopy(candidate);bad['files'][0]['content']+='unreviewed'
            with patch.object(current_contract,'CONTRACT',delta),self.assertRaises(AssertionError):
                current_contract.project_package(bad,language,timestamp,historical)

    def test_current_readme_is_sealed_before_restoring_only_the_historical_view(self):
        timestamp='2000-01-01T00:00:00Z'
        for language in ['english','chinese']:
            historical,candidate,delta=self.current_candidate(language,timestamp)
            candidate['readme']='Reviewed current package instructions.'
            delta['languages'][language]['candidate_metadata_sha256']=self.metadata_seal(candidate)
            original=copy.deepcopy(candidate)
            with patch.object(current_contract,'CONTRACT',delta):
                restored,_=current_contract.project_package(candidate,language,timestamp,historical)
                self.assertEqual(restored,historical)
                self.assertEqual(candidate,original)
                altered=copy.deepcopy(candidate);altered['readme']+=' Unreviewed instructions.'
                with self.assertRaises(AssertionError):
                    current_contract.project_package(altered,language,timestamp,historical)

    def test_frozen_prototype_and_unchanged_translation_tree(self):
        for language in ['english','chinese']:
            values=contract.fixtures(language);record=contract.CONTRACT['languages'][language]
            self.assertEqual(set(record['after'])-set(record['before']),{contract.HELPER})
            self.assertEqual({n for n in record['before'] if record['before'][n]!=record['after'][n]},{contract.QUESTION})
            self.assertEqual(set(values),{contract.QUESTION,contract.HELPER})
        manifest=json.loads((contract.archive('baseline')/'build-manifest.json').read_text())
        files=list((ROOT/'translation').rglob('translation.md'))
        from probe_pdf_budget_translation import pair
        from probe_personal_data_translation import project_current_language_polish_translations
        previous,delta=project_current_language_polish_translations([pair(p.read_text()) for p in files])
        self.assertEqual((len(files),len(previous)),(delta['current_units'],775))
        self.assertEqual(len(manifest['translation_tree_sha256']),775)

    def test_package_metadata_projection_and_mutations(self):
        timestamp='2026-09-23T00:00:00Z'
        for language in ['english','chinese']:
            candidate=contract.integrated_package(language,timestamp)
            self.assertEqual(contract.project_package(candidate,language,timestamp),previous.integrated_package(language,timestamp))
            self.assertEqual(candidate['version'],'0.3.51')
            for mutate in [lambda v:v.update(version='0.3.52'),lambda v:v.update(templateId='prototype'),
                lambda v:v['files'][0].update(content='wrong'),lambda v:v['assets'][0].update(uuid='wrong'),
                lambda v:v['files'].pop(),lambda v:v['assets'].pop(),lambda v:v['formats'][-1]['steps'].pop(),
                lambda v:v.update(createdAt='wrong'),lambda v:v['allowedPackages'].clear()]:
                bad=copy.deepcopy(candidate);mutate(bad)
                with self.assertRaises(AssertionError):contract.project_package(bad,language,timestamp)

    def test_every_prepared_byte_and_inventory_is_checked(self):
        before={contract.QUESTION:b'old','src/layout.css':b'css','src/font.ttf':b'font'}
        changed={contract.QUESTION:b'new',contract.HELPER:b'helper'};after={**before,**changed}
        hashes=lambda data:{n:hashlib.sha256(v).hexdigest() for n,v in data.items()}
        record=dict(languages=dict(english=dict(before=hashes(before),after=hashes(after))))
        with patch.object(contract,'CONTRACT',record),patch.object(contract,'fixtures',return_value=changed),\
             patch.object(previous,'integrated_package',return_value=dict(files=[dict(fileName=contract.QUESTION,content='old')])),\
             patch.object(previous,'project_sources') as verify_previous:
            self.assertEqual(contract.project_sources(after,'english'),before)
            verify_previous.assert_called_once_with(before,'english')
            for name in after:
                with self.assertRaises(AssertionError):contract.project_sources({**after,name:after[name]+b'!'},'english')
                with self.assertRaises(AssertionError):contract.project_sources({n:v for n,v in after.items() if n!=name},'english')
            with self.assertRaises(AssertionError):contract.project_sources({**after,'src/extra':b''},'english')

    def test_new_package_composes_through_all_historical_versions(self):
        from submission_flow_integration import project_package,package
        for language in ['english','chinese']:
            current=contract.integrated_package(language,'2000-01-01T00:00:00Z')
            self.assertEqual(project_package(current,language,'2000-01-01T00:00:00Z'),package(language))

if __name__=='__main__':unittest.main()
