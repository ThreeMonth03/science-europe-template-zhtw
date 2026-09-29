import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import submission_flow_integration as contract
from probe_personal_data_translation import project_submission_flow_translations,verify_submission_translation_chain
from probe_pdf_budget_translation import pair

class SubmissionFlowIntegrationTests(unittest.TestCase):
    def test_exact_current_tree_and_all_historical_stages(self):
        current=[pair(p.read_text()) for p in (ROOT/'translation/tree').rglob('translation.md')]
        old,delta=project_submission_flow_translations(current)
        self.assertEqual((len(old),len(current),len(delta['removed']),len(delta['added'])),(773,785,10,12))
        _,chain=verify_submission_translation_chain(current)
        self.assertEqual(chain['current_language_polish']['retained_units'],660)
        self.assertEqual(chain['submission_flow']['retained_units'],763)
        self.assertEqual(chain['full_km_followups']['retained_units'],767)
        for bad in [current[:-1],current+current[:1],current[1:]+[(current[0][0],current[0][1]+'!')]]:
            with self.assertRaises(AssertionError):project_submission_flow_translations(bad)
        for added in map(tuple,delta['added']):
            bad=list(current);bad.remove(added);bad.append((added[0],added[1]+'!'))
            with self.assertRaises(AssertionError):project_submission_flow_translations(bad)

    def test_sealed_fixture_files_and_metadata_are_not_guessed(self):
        for language in ['english','chinese']:
            for prototype in [False,True]:
                phase='prototype' if prototype else 'baseline';expected=contract.CONTRACT['languages'][language][phase]
                spec=contract.package(language,prototype)
                for item in spec['files']:
                    self.assertEqual(hashlib.sha256(item['content'].encode()).hexdigest(),expected['sources'][item['fileName']])
                for name,digest in expected['assets'].items():self.assertEqual(expected['sources'][name.removeprefix('template/assets/')],digest)

    def test_projection_rejects_any_missing_added_changed_or_unrelated_byte(self):
        before={'src/a.j2':b'old','src/font.ttf':b'font'}
        after={**before,'src/a.j2':b'new',**{n:b'helper' for n in contract.ADDED}}
        hashes=lambda values:{n:hashlib.sha256(v).hexdigest() for n,v in values.items()}
        record=dict(prototype=dict(sources=hashes(after)),baseline=dict(sources=hashes(before)),added=sorted(contract.ADDED))
        with patch.object(contract,'CONTRACT',{'languages':{'english':record}}),patch.object(contract,'package',return_value=dict(files=[dict(fileName='src/a.j2',content='old')])):
            self.assertEqual(contract.project_sources(after,'english'),before)
            for name in after:
                with self.assertRaises(AssertionError):contract.project_sources({**after,name:after[name]+b'!'},'english')
                with self.assertRaises(AssertionError):contract.project_sources({n:v for n,v in after.items() if n!=name},'english')
            with self.assertRaises(AssertionError):contract.project_sources({**after,'src/extra.xml':b''},'english')

    def test_identity_and_word_steps_checked_before_projection(self):
        timestamp='2026-09-22T00:00:00Z'
        for language in ['english','chinese']:
            candidate=contract.integrated_package(language,timestamp)
            self.assertEqual(contract.project_package(candidate,language,timestamp),contract.package(language))
            for mutate in [lambda v:v.update(version='0.3.48'),lambda v:v.update(name='wrong'),
                lambda v:v['files'][0].update(uuid='wrong'),lambda v:v['files'][0].update(content='wrong'),
                lambda v:v['assets'].pop(),lambda v:v['formats'][-1]['steps'].pop(),
                lambda v:v.update(updatedAt='wrong'),lambda v:v['allowedPackages'].clear()]:
                bad=copy.deepcopy(candidate);mutate(bad)
                with self.assertRaises(AssertionError):contract.project_package(bad,language,timestamp)

if __name__=='__main__':unittest.main()
