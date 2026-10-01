"""Paired Q3 integration must retain every unreviewed byte and older proof."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import q3_policy_prose_integration as contract
import word_empty_section_integration as previous
import current_source_repairs as current_contract
from check_budget_grouping_integration import asset_uuid

class Q3IntegrationTests(unittest.TestCase):
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
