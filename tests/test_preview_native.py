"""Host-only preview guards; no Docker, real configuration, or native files."""
import copy
import io
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from artifact_utils import PO_ARTIFACTS, stage_candidate
import preview_native
import preview_worker

sys.path.insert(0, str(ROOT / 'tests'))
from test_artifact_lifecycle import POCandidateFixture


class NativePreviewTests(POCandidateFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        for folder, archive_name, identity, language in [
                ('en', 'english.zip', self.manifest['source'], 'en'),
                ('translated', 'chinese.zip', self.manifest['translation'], 'zh-Hant')]:
            target = self.build / folder
            (target / 'src').mkdir(parents=True)
            text = 'Template-owned English source' if language == 'en' else 'Template-owned Chinese-compatible source'
            descriptor = dict(organizationId=identity['organization_id'], templateId=identity['template_id'],
                              version=identity['version'], metamodelVersion=12, language=language,
                              id=':'.join(identity[k] for k in ('organization_id', 'template_id', 'version')),
                              formats=[], files=[dict(uuid='file-1', fileName='src/index.html.j2', content=text)],
                              assets=[dict(uuid='asset-1', fileName='src/helper.lua', contentType='text/plain')])
            (target / 'src/index.html.j2').write_text(text)
            (target / 'src/helper.lua').write_bytes(b'-- synthetic helper')
            if language == 'zh-Hant':
                mo = target / 'src/i18n/zh-Hant/LC_MESSAGES/dsw.mo'
                mo.parent.mkdir(parents=True)
                mo.write_bytes((self.build / 'zh-Hant.mo').read_bytes())
                descriptor['assets'].append(dict(uuid='asset-mo', fileName='src/i18n/zh-Hant/LC_MESSAGES/dsw.mo', contentType='application/octet-stream'))
            (target / 'template.json').write_text(json.dumps(descriptor))
            with zipfile.ZipFile(self.build / archive_name, 'w') as archive:
                archive.writestr('template/template.json', json.dumps(descriptor))
                for asset in descriptor['assets']:
                    archive.writestr('template/assets/' + asset['fileName'], (target / asset['fileName']).read_bytes())
        self.sidecar.update(source_zip_sha256=preview_native.sha(self.build / 'english.zip'),
                            output_zip_sha256=preview_native.sha(self.build / 'chinese.zip'))
        (self.build / 'chinese.zip.json').write_text(json.dumps(self.sidecar))
        self.manifest['sha256'] = {name: preview_native.sha(self.build / name) for name in PO_ARTIFACTS}
        self.manifest['runtime'] = {'workers': {
            '4.34': 'datastewardshipwizard/document-worker@sha256:' + 'd'*64,
            '4.35': 'datastewardshipwizard/document-worker@sha256:' + 'e'*64}}
        self.manifest['rendering'] = {}
        for folder, inventory in [('en', 'english'), ('translated', 'compat434')]:
            base = self.build / folder
            self.manifest['rendering'][inventory] = {
                p.relative_to(base).as_posix(): preview_native.sha(p)
                for p in (base / 'src').rglob('*') if p.is_file()}
        self.report['package_sha256'] = dict(self.manifest['sha256'])
        self.save()
        self.pipeline = {k: copy.deepcopy(self.manifest[k]) for k in ['profile', 'source', 'tooling', 'translation', 'runtime']}
        self.pipeline_path = self.root / 'pipeline.yml'
        self.pipeline_path.write_text(yaml.safe_dump(self.pipeline))
        self.args = SimpleNamespace(build=self.build, pipeline=self.pipeline_path,
                                    output=self.root / 'preview', profile='submission',
                                    plan_only=False)
        for version in ['434', '435']:
            config = self.root / (version + '-synthetic.yml')
            config.write_text('{}\n')
            config.chmod(0o600)
            setattr(self.args, 'config_' + version, config)
        for suffix, version, language in [('434_zh', '18.2', 'zh-Hant'), ('435_en', '18.3', 'en'), ('435_zh', '18.3', 'zh-Hant')]:
            context = {'metamodelVersion': version,
                       'document': {'language': language, 'locale': {'code': None if language == 'en' else 'zh-Hant'}},
                       'project': {'replies': {'synthetic-question': 'synthetic-answer'}},
                       'knowledgeModel': {'synthetic': True}}
            path = self.root / (suffix + '.json')
            path.write_text(json.dumps(context))
            setattr(self.args, 'context_' + suffix, [path])

    def test_all_five_artifacts_and_prepared_source_are_checked(self):
        preview_native.verify_build(self.build, self.pipeline)
        for name in PO_ARTIFACTS:
            with self.subTest(artifact=name):
                path = self.build / name
                original = path.read_bytes()
                path.write_bytes(original + b'tamper')
                with self.assertRaises(ValueError):
                    preview_native.verify_build(self.build, self.pipeline)
                path.write_bytes(original)

    def test_rehashed_prepared_source_cannot_differ_from_packaged_zip(self):
        file = self.build / 'en/src/index.html.j2'
        file.write_text('Unpackaged Jinja change')
        self.manifest['rendering']['english']['src/index.html.j2'] = preview_native.sha(file)
        self.save()
        with self.assertRaises(ValueError):
            preview_native.verify_build(self.build, self.pipeline)

    def test_paired_contexts_must_have_identical_replies(self):
        target = self.args.context_435_zh[0]
        context = preview_native.read(target)
        context['project']['replies']['synthetic-question'] = 'different-answer'
        target.write_text(json.dumps(context))
        with self.assertRaisesRegex(ValueError, 'identical project.replies'):
            preview_native.plan(self.args)
        context['project']['replies']['synthetic-question'] = 'synthetic-answer'
        target.write_text(json.dumps(context))
        _, _, jobs = preview_native.plan(self.args)
        self.assertEqual(3, len(jobs))
        self.assertEqual(1, len({job['replies_sha256'] for job in jobs}))

    def test_plan_only_never_starts_docker_or_creates_artifacts(self):
        self.args.plan_only = True
        with patch.object(preview_native.subprocess, 'run') as docker, patch('sys.stdout', new_callable=io.StringIO) as output:
            preview_native.run(self.args)
        docker.assert_not_called()
        result = json.loads(output.getvalue())
        self.assertEqual((3, 3), (result['planned_pdf'], result['planned_docx']))
        self.assertIs(result['accepted'], False)
        self.assertIs(result['same_answer_comparison'], True)
        self.assertFalse(self.args.output.exists())

    def test_existing_evidence_directory_is_never_overwritten(self):
        self.args.output.mkdir()
        sentinel = self.args.output / 'sentinel.txt'
        sentinel.write_text('Retain earlier evidence')
        with patch.object(preview_native.subprocess, 'run') as docker, self.assertRaises(ValueError):
            preview_native.run(self.args)
        docker.assert_not_called()
        self.assertEqual('Retain earlier evidence', sentinel.read_text())
        self.assertEqual([sentinel], list(self.args.output.iterdir()))

    def test_exclusive_receipt_write_preserves_existing_file(self):
        path = self.root / 'existing-receipt.json'
        preview_native.save(path, {'accepted': False})
        before = path.read_bytes()
        with self.assertRaises(FileExistsError):
            preview_native.save(path, {'accepted': True})
        self.assertEqual(before, path.read_bytes())

    def test_worker_failure_stays_unaccepted_and_cannot_stage(self):
        with patch.object(preview_native.subprocess, 'run', return_value=SimpleNamespace(returncode=7)), self.assertRaises(RuntimeError):
            preview_native.run(self.args)
        receipt = preview_native.read(self.args.output / 'receipt.json')
        self.assertIs(receipt['render_passed'], False)
        for flag in ['accepted', 'visual_accepted', 'release_acceptance', 'microsoft_word_tested']:
            self.assertIs(receipt[flag], False)
        self.assertNotIn('passed', receipt)
        self.assertEqual([], receipt['outputs'])
        self.assertFalse(list(self.args.output.rglob('*.pdf')))
        self.assertFalse(list(self.args.output.rglob('*.docx')))
        # Even a fully hash-bound preview receipt is not a staging approval.
        (self.build / 'pilot-report.json').write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError, 'declared acceptance scope'):
            stage_candidate(self.build, self.root / 'store')
        self.assertFalse((self.root / 'store').exists())

    def test_child_success_without_both_formats_is_not_a_successful_preview(self):
        def missing_outputs(*args, **kwargs):
            destination = self.args.output / '434-zh-Hant/case-001'
            (destination / 'worker-receipt.json').write_text(json.dumps({'render_passed': True, 'outputs': []}))
            return SimpleNamespace(returncode=0)
        with patch.object(preview_native.subprocess, 'run', side_effect=missing_outputs), self.assertRaisesRegex(ValueError, 'exactly one PDF and one Word'):
            preview_native.run(self.args)
        receipt = preview_native.read(self.args.output / 'receipt.json')
        self.assertIs(receipt['render_passed'], False)
        self.assertIs(receipt['accepted'], False)
        self.assertEqual([], receipt['outputs'])

    def test_timeout_cleanup_targets_only_this_run_container(self):
        timeout = preview_native.subprocess.TimeoutExpired('docker', 300)
        with patch.object(preview_native.subprocess, 'run', side_effect=[timeout, SimpleNamespace(returncode=0)]) as docker, self.assertRaises(preview_native.subprocess.TimeoutExpired):
            preview_native.run(self.args)
        run_command = docker.call_args_list[0].args[0]
        container = run_command[run_command.index('--name') + 1]
        self.assertRegex(container, '^dsw-local-preview-[0-9a-f]{32}$')
        self.assertEqual(['docker', 'rm', '--force', container], docker.call_args_list[1].args[0])
        receipt = preview_native.read(self.args.output / 'receipt.json')
        self.assertIs(receipt['render_passed'], False)
        self.assertIs(receipt['accepted'], False)


class StockWorkerPythonPathTests(unittest.TestCase):
    def test_stock_user_site_is_available_to_parent_and_filter_subprocesses(self):
        for minor in (12, 13):
            with self.subTest(python_minor=minor), \
                    patch.object(preview_worker.sys, 'version_info', SimpleNamespace(major=3, minor=minor)), \
                    patch.object(preview_worker.Path, 'home', side_effect=AssertionError('Do not infer the stock installation from host HOME')), \
                    patch.object(preview_worker.site, 'addsitedir') as addsitedir, \
                    patch.dict(preview_worker.os.environ, {'PYTHONPATH': '/existing'}, clear=True):
                preview_worker.configure_python_site()
                stock_site = f'/home/user/.local/lib/python3.{minor}/site-packages'
                addsitedir.assert_called_once_with(stock_site)
                self.assertEqual(stock_site + os.pathsep + '/existing', preview_worker.os.environ['PYTHONPATH'])
                self.assertNotIn('HOME', preview_worker.os.environ)


if __name__ == '__main__':
    unittest.main()
