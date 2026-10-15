import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from artifact_utils import PO_ARTIFACTS


class CandidateArtifactWorkflowTests(unittest.TestCase):
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
