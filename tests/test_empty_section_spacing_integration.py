import copy,hashlib,json
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import empty_section_spacing_integration as contract
import submission_flow_integration as old

class EmptySectionIntegrationTests(unittest.TestCase):
    def test_seals_and_unchanged_translation_tree(self):
        self.assertEqual(len(contract.css()),len(contract.CONTRACT['css'].encode()))
        files=list((ROOT/'translation/tree').rglob('translation.md'))
        from probe_pdf_budget_translation import pair
        from probe_personal_data_translation import project_current_language_polish_translations
        current,polish=project_current_language_polish_translations([pair(p.read_text()) for p in files])
        self.assertEqual(len(files),polish['current_units'])
        from reuse_preparation_integration import project_translations
        old,delta=project_translations(current)
        from probe_personal_data_translation import archived_pairs
        from collections import Counter
        self.assertEqual(Counter(old),Counter(archived_pairs('f610bb2')))
        self.assertEqual(delta['retained_units'],766)

    def test_complete_metadata_checked_before_old_view(self):
        for language in ['english','chinese']:
            timestamp='2026-09-23T00:00:00Z';candidate=contract.integrated_package(language,timestamp)
            self.assertEqual(contract.project_package(candidate,language,timestamp),old.integrated_package(language,timestamp))
            self.assertEqual(old.project_package(candidate,language,timestamp),old.package(language))
            for mutate in [lambda v:v.update(version='0.3.49'),lambda v:v.update(templateId='wrong'),
                lambda v:v['files'][0].update(content='wrong'),lambda v:v['files'][0].update(uuid='wrong'),
                lambda v:v['assets'].pop(),lambda v:v['formats'][-1]['steps'].pop(),
                lambda v:v['allowedPackages'].clear(),lambda v:v.update(createdAt='wrong')]:
                bad=copy.deepcopy(candidate);mutate(bad)
                with self.assertRaises(AssertionError):contract.project_package(bad,language,timestamp)

    def test_strict_prepared_source_projection_without_binary_fixtures(self):
        from unittest.mock import patch
        before={'src/layout.css':b'old','src/content.html.j2':b'answers','src/font.ttf':b'font'}
        after={**before,'src/layout.css':b'old'+contract.css()}
        record={'languages':{'english':{'prototype':{'sources':{n:hashlib.sha256(v).hexdigest() for n,v in before.items()}}}}}
        with patch.object(old,'CONTRACT',record):
            self.assertEqual(contract.project_sources(after,'english'),before)
            for name in after:
                with self.assertRaises(AssertionError):contract.project_sources({**after,name:after[name]+b'!'},'english')
            with self.assertRaises(AssertionError):contract.project_sources({**after,'src/extra':b''},'english')
            with self.assertRaises(AssertionError):contract.project_sources({**after,'src/layout.css':after['src/layout.css']+contract.css()},'english')

if __name__=='__main__':unittest.main()
