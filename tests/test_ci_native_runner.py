"""Exercise the actual CI shell step without invoking Docker or old renderers."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]


class NativeRunnerTests(unittest.TestCase):
    def run_step(self, failure=''):
        workflow = yaml.safe_load((ROOT / '.github/workflows/pilot-checks.yml').read_text())
        step = next(s for s in workflow['jobs']['checks']['steps']
                    if s.get('name', '').startswith('Check all existing PDF and DOCX'))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'scripts').mkdir()
            shutil.copy2(ROOT / 'scripts/check_native_regressions.sh', root / 'scripts')
            fake = root / 'python-probe'
            fake.write_text(f'#!{sys.executable}\n'
                            'import os, sys\nfrom pathlib import Path\n'
                            'raise SystemExit(7 if Path(sys.argv[1]).name == '
                            'os.environ.get("SE_FAIL_PROBE") else 0)\n')
            fake.chmod(0o700)
            env = dict(os.environ, SE_PYTHON=str(fake), SE_FAIL_PROBE=failure,
                       SE_BUILD_DIR=str(root / 'prepared build'))
            result = subprocess.run(['bash', '-e', '-o', 'pipefail', '-c', step['run']],
                                    cwd=root, env=env, capture_output=True, text=True, timeout=20)
            rows = {language: (root / f'outputs/ci/native-{language}.tsv').read_text().splitlines()[1:]
                    for language in ('english', 'chinese')}
            return result, rows

    def test_both_lanes_complete(self):
        result, rows = self.run_step()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([len(rows[x]) for x in ('english', 'chinese')], [18, 13])
        self.assertTrue(all(row.endswith('\t0') for lane in rows.values() for row in lane))

    def test_english_failure_is_not_hidden_by_chinese_success(self):
        result, rows = self.run_step('probe_empty_section_spacing.py')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(rows['english']), 1)
        self.assertTrue(rows['english'][-1].endswith('\t7'))
        self.assertEqual(len(rows['chinese']), 13)  # Workflow awaited the other lane.

    def test_chinese_failure_is_not_hidden_by_english_success(self):
        result, rows = self.run_step('probe_identifier_spacing.py')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(rows['english']), 18)
        self.assertEqual(len(rows['chinese']), 9)
        self.assertTrue(rows['chinese'][-1].endswith('\t7'))

    def test_metadata_history_view_failure_stops_both_lanes(self):
        # The view command passes '-' as the Python stdin entry point.
        result, rows = self.run_step('-')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual([len(rows[x]) for x in ('english', 'chinese')], [10, 6])

    def test_unknown_lane_is_rejected(self):
        result = subprocess.run(['bash', str(ROOT / 'scripts/check_native_regressions.sh'),
                                 'typo', 'unused'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)

    def test_parallel_groups_keep_a_fail_closed_required_check(self):
        workflow = yaml.safe_load((ROOT / '.github/workflows/pilot-checks.yml').read_text())
        checks, gate = workflow['jobs']['checks'], workflow['jobs']['build']
        self.assertEqual(checks['strategy']['matrix']['group'],
                         ['english-unit', 'chinese-unit', 'integration', 'reading', 'native'])
        self.assertIs(checks['strategy']['fail-fast'], False)
        self.assertNotIn('needs', checks)
        self.assertEqual((gate['needs'], gate['if']), ('checks', 'always()'))
        step, = gate['steps']
        self.assertEqual(step['env']['CHECK_RESULT'], '${{ needs.checks.result }}')
        for result in ('success', 'failure', 'cancelled', 'skipped', ''):
            with self.subTest(result=result):
                run = subprocess.run(['bash', '-e', '-c', step['run']],
                                     env=dict(os.environ, CHECK_RESULT=result))
                self.assertEqual(run.returncode == 0, result == 'success')
