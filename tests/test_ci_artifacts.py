import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from artifact_utils import PO_ARTIFACTS


class CandidateArtifactWorkflowTests(unittest.TestCase):
    def test_ci_downloads_full_english_history(self):
        workflow = yaml.safe_load((ROOT / '.github/workflows/pilot-checks.yml').read_text())
        checkouts = [step['with'] for step in workflow['jobs']['checks']['steps']
                     if step.get('with', {}).get('repository') == 'ThreeMonth03/science-europe-template']
        self.assertEqual(1, len(checkouts))
        self.assertEqual(0, checkouts[0]['fetch-depth'])

    def test_ci_named_english_tests_can_import_shared_helpers(self):
        workflow = yaml.safe_load((ROOT / '.github/workflows/pilot-checks.yml').read_text())
        steps = [step for step in workflow['jobs']['checks']['steps']
                 if step.get('if') == "matrix.group == 'english-unit'"]
        self.assertEqual(1, len(steps))
        self.assertEqual('tests:scripts', steps[0]['env']['PYTHONPATH'])

    def test_custom_pipeline_has_no_tool_checkout_install_or_cli_dependency(self):
        workflow_path = ROOT / '.github/workflows/pilot-checks.yml'
        workflow = yaml.safe_load(workflow_path.read_text())
        steps = workflow['jobs']['checks']['steps']
        checkouts = [step for step in steps if step.get('uses', '').startswith('actions/checkout@')]
        self.assertEqual(2, len(checkouts))
        self.assertEqual(['ThreeMonth03/science-europe-template'],
                         [step['with']['repository'] for step in checkouts
                          if 'repository' in step.get('with', {})])
        text = workflow_path.read_text()
        for obsolete in ('dsw-document-template-tool', 'tooling/.venv', '--tooling', '[dev]', 'pip install -e'):
            with self.subTest(obsolete=obsolete):
                self.assertNotIn(obsolete, text)
        self.assertIn('english/requirements-dev.txt', text)
        self.assertIn('zh/requirements-dev.txt', text)
        pipeline = yaml.safe_load((ROOT / 'pipeline.yml').read_text())
        self.assertEqual(3, pipeline['schema_version'])
        self.assertNotIn('tooling', pipeline)

    def test_english_unit_lane_covers_reference_versions_and_primary_identifiers(self):
        workflow = yaml.safe_load((ROOT / '.github/workflows/pilot-checks.yml').read_text())
        steps = [step for step in workflow['jobs']['checks']['steps']
                 if step.get('if') == "matrix.group == 'english-unit'"
                 and '-m unittest -v' in step.get('run', '')]
        self.assertEqual(1, len(steps))
        self.assertEqual('english', steps[0]['working-directory'])
        for module in ('tests.test_catalog', 'tests.test_reference_versions', 'tests.test_primary_identifiers'):
            with self.subTest(module=module):
                self.assertIn(module, steps[0]['run'].split())

    def test_catalog_boundary_is_checked_before_package_build(self):
        workflow = yaml.safe_load((ROOT / '.github/workflows/pilot-checks.yml').read_text())
        steps = workflow['jobs']['checks']['steps']
        catalog_steps = [(index, step) for index, step in enumerate(steps)
                         if 'scripts/refresh_po.py' in step.get('run', '')]
        self.assertEqual(1, len(catalog_steps))
        index, step = catalog_steps[0]
        self.assertEqual("matrix.group == 'integration'", step['if'])
        self.assertEqual('zh', step['working-directory'])
        self.assertIn('../english/scripts/export_pot.py', step['run'])
        self.assertIn('--pot outputs/ci/template.pot', step['run'])
        self.assertNotIn('--english', step['run'])
        self.assertIn('../english/scripts/check_catalog.py --po locales/zh-Hant.po', step['run'],
                      'Keep strict runtime and Babel substitution checks before building')
        build_index = next(index for index, step in enumerate(steps)
                           if 'scripts/build.py' in step.get('run', ''))
        self.assertLess(index, build_index)

    def test_integration_smokes_the_built_packages_with_pipeline_worker_locks(self):
        workflow = yaml.safe_load((ROOT / '.github/workflows/pilot-checks.yml').read_text())
        steps = [step for step in workflow['jobs']['checks']['steps']
                 if 'scripts/smoke_native.py' in step.get('run', '')]
        self.assertEqual(1, len(steps))
        self.assertEqual("matrix.group == 'integration'", steps[0]['if'])
        self.assertIn("pipeline['runtime']['workers']", steps[0]['run'])
        self.assertIn('--build "$SE_BUILD_DIR"', steps[0]['run'])

    def test_candidate_upload_contains_all_five_build_assets(self):
        workflow = yaml.safe_load((ROOT / '.github/workflows/pilot-checks.yml').read_text())
        uploads = [step for step in workflow['jobs']['checks']['steps']
                   if step.get('uses', '').startswith('actions/upload-artifact@')
                   and step.get('with', {}).get('name') == 'current-candidate-not-a-release']
        self.assertEqual(len(uploads), 1)
        patterns = uploads[0]['with']['path'].splitlines()
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            build = workspace / 'zh/outputs/build-example'
            build.mkdir(parents=True)
            for name in (*PO_ARTIFACTS, 'manifest.json', 'private-config.yml'):
                (build / name).write_text('fixture')
            authoritative_po = workspace / 'zh/locales/zh-Hant.po'
            authoritative_po.parent.mkdir(parents=True)
            authoritative_po.write_text('source catalog, not the built candidate')
            selected = set()
            for pattern in patterns:
                for match in workspace.glob(pattern.strip()):
                    selected.update(path for path in (match.rglob('*') if match.is_dir() else [match])
                                    if path.is_file())
            required = {build / name for name in PO_ARTIFACTS}
            self.assertFalse(required - selected,
                             'Missing candidate build assets: ' + ', '.join(sorted(path.name for path in required - selected)))
            self.assertIn(build / 'manifest.json', selected)
            self.assertNotIn(build / 'private-config.yml', selected)
            self.assertNotIn(authoritative_po, selected)


if __name__ == '__main__':
    unittest.main()
