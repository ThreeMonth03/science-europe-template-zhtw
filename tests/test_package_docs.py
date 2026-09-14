import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

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
