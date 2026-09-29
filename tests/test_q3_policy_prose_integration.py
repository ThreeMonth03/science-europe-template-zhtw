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

class Q3IntegrationTests(unittest.TestCase):
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
