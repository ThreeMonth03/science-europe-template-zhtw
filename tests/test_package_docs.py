import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from build import package_readme, package_timestamp


class PackageDocumentationTests(unittest.TestCase):
    def test_navigation_readme_is_not_used_as_package_readme(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'README.md').write_text('Navigation only')
            with self.assertRaises(ValueError): package_readme(root)
            (root / 'PACKAGE_README.md').write_text('Stable package description')
            before = package_readme(root).read_bytes()
            (root / 'README.md').write_text('New review links')
            self.assertEqual(before, package_readme(root).read_bytes())
            (root / 'PACKAGE_README.md').write_text(' ')
            with self.assertRaises(ValueError): package_readme(root)

    def test_only_package_input_commits_advance_timestamp(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            def git(*args, env=None):
                return subprocess.run(['git', '-C', str(root), *args], env=env, check=True, capture_output=True)
            git('init'); git('config', 'user.email', 'test@example.invalid'); git('config', 'user.name', 'Test')
            def commit(day):
                git('add', '.')
                env = os.environ.copy(); env.update(GIT_AUTHOR_DATE=f'2026-01-{day:02d}T00:00:00Z', GIT_COMMITTER_DATE=f'2026-01-{day:02d}T00:00:00Z')
                git('commit', '-m', 'test inputs', env=env)
            (root / 'template.json').write_text('{}'); commit(1)
            first = package_timestamp(root)
            (root / 'README.md').write_text('Changed navigation'); commit(2)
            self.assertEqual(first, package_timestamp(root))
            (root / 'src').mkdir(); (root / 'src/main.j2').write_text('New output'); commit(3)
            self.assertEqual('2026-01-03T00:00:00Z', package_timestamp(root))
            (root / 'PACKAGE_README.md').write_text('Changed package description'); commit(4)
            self.assertEqual('2026-01-04T00:00:00Z', package_timestamp(root))

    def test_shallow_checkout_fails_closed_until_history_is_fetched(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp); source = base/'source'; source.mkdir()
            def git(root, *args, env=None):
                return subprocess.check_output(['git', '-C', str(root), *args], env=env, stderr=subprocess.PIPE, text=True).strip()
            git(source, 'init', '--initial-branch=main')
            git(source, 'config', 'user.email', 'test@example.invalid'); git(source, 'config', 'user.name', 'Test')
            for day, name in [(1, 'template.json'), (2, 'test-only.txt')]:
                (source/name).write_text('{}'); git(source, 'add', name)
                env = os.environ.copy(); env.update(GIT_AUTHOR_DATE=f'2026-01-{day:02d}T00:00:00Z', GIT_COMMITTER_DATE=f'2026-01-{day:02d}T00:00:00Z')
                git(source, 'commit', '-m', name, env=env)
            clone = base/'shallow'
            subprocess.run(['git', 'clone', '--depth', '1', source.as_uri(), str(clone)], check=True, capture_output=True)
            self.assertEqual('true', git(clone, 'rev-parse', '--is-shallow-repository'))
            # This is the misleading value that the old build accepted.
            self.assertTrue(git(clone, 'log', '-1', '--format=%cI', 'HEAD', '--', 'template.json').startswith('2026-01-02'))
            with self.assertRaisesRegex(ValueError, 'Full English history required'): package_timestamp(clone)
            git(clone, 'fetch', '--unshallow')
            self.assertEqual(package_timestamp(source), package_timestamp(clone))
            self.assertEqual('2026-01-01T00:00:00Z', package_timestamp(clone))

    def test_ci_downloads_full_english_history(self):
        root = Path(__file__).resolve().parents[1]
        workflow = yaml.safe_load((root/'.github/workflows/pilot-checks.yml').read_text())
        checkouts = [step['with'] for step in workflow['jobs']['build']['steps']
                     if step.get('with', {}).get('repository') == 'ThreeMonth03/science-europe-template']
        self.assertEqual(len(checkouts), 1)
        self.assertEqual(checkouts[0]['fetch-depth'], 0)
