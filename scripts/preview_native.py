"""Render private local contexts with the pipeline-pinned stock Workers.

This creates native files and a provenance receipt, never visual acceptance or
pilot-report.json. Docker images must already be present; no Server is contacted.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import uuid
import zipfile

import yaml

from artifact_utils import PO_ARTIFACTS, PO_PROFILE

GROUPS = [('434-zh-Hant', '4.34', 'zh-Hant'), ('435-en', '4.35', 'en'), ('435-zh-Hant', '4.35', 'zh-Hant')]


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def value_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def save(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def verify_build(build, pipeline):
    manifest = read(build / 'manifest.json')
    if manifest.get('profile') != PO_PROFILE or pipeline.get('profile') != PO_PROFILE:
        raise ValueError('The current PO build profile is required')
    if manifest.get('status') not in ('candidate', 'preview'):
        raise ValueError('Only candidate or explicitly unaccepted preview builds are supported')
    if any(manifest.get(key) != pipeline.get(key) for key in ('source', 'tooling', 'translation', 'runtime')):
        raise ValueError('Build provenance differs from pipeline.yml')
    if set(manifest.get('sha256', {})) != set(PO_ARTIFACTS):
        raise ValueError('All five build artifacts are required')
    for name, expected in manifest['sha256'].items():
        if sha(build / name) != expected:
            raise ValueError('Build artifact hash mismatch')
    for version in ('4.34', '4.35'):
        if not re.fullmatch(r'datastewardshipwizard/document-worker@sha256:[0-9a-f]{64}', pipeline['runtime']['workers'][version]):
            raise ValueError('A digest-pinned stock Worker is required')
    for folder, inventory, archive_name in [('en', 'english', 'english.zip'), ('translated', 'compat434', 'chinese.zip')]:
        expected = manifest['rendering'][inventory]
        actual = {p.relative_to(build / folder).as_posix(): sha(p) for p in (build / folder / 'src').rglob('*') if p.is_file()}
        if actual != expected or any(p.is_symlink() for p in (build / folder).rglob('*')):
            raise ValueError('Prepared render files differ from build manifest')
        for name in expected:
            if PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts:
                raise ValueError('Unsafe rendering inventory path')
        with zipfile.ZipFile(build / archive_name) as archive:
            bundled = json.loads(archive.read('template/template.json'))
            packaged = {}
            for field in ('files', 'assets'):
                for item in bundled[field]:
                    name = item['fileName']
                    if not name.startswith('src/') or PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts or name in packaged:
                        raise ValueError('Unsafe or duplicate package rendering path')
                    content = item['content'].encode('utf-8') if field == 'files' else archive.read('template/assets/' + name)
                    packaged[name] = hashlib.sha256(content).hexdigest()
            if actual != packaged:
                raise ValueError('Prepared rendering bytes differ from the hashed package')
        prepared = read(build / folder / 'template.json')
        if any(prepared.get(key) != bundled.get(key) for key in ('organizationId', 'templateId', 'version', 'metamodelVersion', 'language', 'formats')):
            raise ValueError('Prepared template metadata differs from packaged artifact')
    return manifest


def plan(args):
    build = args.build.resolve()
    pipeline = yaml.safe_load(args.pipeline.read_text())
    manifest = verify_build(build, pipeline)
    contexts = [args.context_434_zh, args.context_435_en, args.context_435_zh]
    groups = list(GROUPS)
    if getattr(args, 'context_434_en', None):
        groups.append(('434-en', '4.34', 'en'))
        contexts.append(args.context_434_en)
    if len({len(items) for items in contexts}) != 1:
        raise ValueError('Provide the same number of contexts for all selected groups')
    jobs, replies = [], {}
    for (group, version, language), inputs in zip(groups, contexts):
        config = getattr(args, 'config_' + version.replace('.', '')).resolve()
        if not config.is_file() or config.stat().st_mode & 0o077:
            raise ValueError('Worker configuration must be a private readable file (mode 600)')
        for index, source in enumerate(inputs, 1):
            source = source.resolve()
            context = read(source)
            if context.get('metamodelVersion') != ('18.2' if version == '4.34' else '18.3'):
                raise ValueError('Context metamodel does not match the selected Worker')
            if version == '4.35' and (context['document'].get('language') != language or (context['document'].get('locale') or {}).get('code') != (None if language == 'en' else 'zh-Hant')):
                raise ValueError('Provide an English or Chinese 4.35 context with its original matching locale')
            reply_hash = value_sha(context['project']['replies'])
            if index in replies and replies[index] != reply_hash:
                raise ValueError('Paired contexts must contain identical project.replies')
            replies[index] = reply_hash
            jobs.append({'case': f'case-{index:03d}', 'group': group, 'version': version, 'language': language,
                'context': str(source), 'context_sha256': sha(source), 'replies_sha256': reply_hash,
                'knowledge_model_sha256': value_sha(context['knowledgeModel']), 'config': str(config), 'config_sha256': sha(config),
                'worker_image': pipeline['runtime']['workers'][version], 'profile': args.profile})
    return build, manifest, jobs


def run(args):
    build, manifest, jobs = plan(args)
    if args.plan_only:
        print(json.dumps({'planned_pdf': len(jobs), 'planned_docx': len(jobs), 'accepted': False, 'same_answer_comparison': True}))
        return
    output = args.output.absolute()
    if output.exists() or output.is_symlink():
        raise ValueError('A new output directory is required; existing evidence is never overwritten')
    output.mkdir(mode=0o700, parents=False)
    report = {'schema_version': 1, 'kind': 'local-native-preview', 'render_passed': False,
        'accepted': False, 'visual_accepted': False, 'release_acceptance': False, 'microsoft_word_tested': False,
        'manifest_sha256': sha(build / 'manifest.json'), 'package_sha256': manifest['sha256'],
        'build_status': manifest['status'],
        'pipeline_sha256': sha(args.pipeline), 'profile': args.profile,
        'same_answer_comparison': True, 'outputs': [], 'jobs': []}
    try:
        worker = Path(__file__).with_name('preview_worker.py').resolve()
        report['runner_sha256'] = {p.name: sha(p) for p in (Path(__file__), worker)}
        for job in jobs:
            destination = output / job['group'] / job['case']
            destination.mkdir(parents=True, mode=0o700)
            container = 'dsw-local-preview-' + uuid.uuid4().hex
            job['container_name'] = container
            save(destination / 'job.json', job)
            command = ['docker', 'run', '--name', container, '--rm', '--pull=never', '--network=none', '--read-only', '--cap-drop=ALL',
                '--security-opt=no-new-privileges', '--log-driver=none', '--tmpfs', '/tmp:rw,size=768m',
                '--user', f'{os.getuid()}:{os.getgid()}', '-e', 'PYTHONDONTWRITEBYTECODE=1', '-e', 'WORKER_IMAGE=' + job['worker_image'],
                '-v', f'{build}:/build:ro', '-v', f'{worker}:/preview_worker.py:ro', '-v', f'{destination}:/output:rw',
                '-v', f'{job["context"]}:/input/context.json:ro', '-v', f'{job["config"]}:/input/worker.yml:ro',
                job['worker_image'], 'python', '-B', '/preview_worker.py']
            with (destination / 'worker.log').open('xb') as log:
                try:
                    result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=300)
                except subprocess.TimeoutExpired:
                    subprocess.run(['docker', 'rm', '--force', container], stdout=log, stderr=subprocess.STDOUT, timeout=30)
                    raise
            child = read(destination / 'worker-receipt.json') if (destination / 'worker-receipt.json').exists() else {}
            report['jobs'].append({'case': job['case'], 'group': job['group'], 'exit_code': result.returncode, 'config_sha256': job['config_sha256'], 'worker_image': job['worker_image'], 'runtime': child.get('runtime')})
            if result.returncode or child.get('render_passed') is not True:
                raise RuntimeError('Stock Worker preview failed; inspect the private output directory')
            if sorted(item.get('kind', '') for item in child.get('outputs', [])) != ['PDF', 'Word']:
                raise ValueError('Worker must return exactly one PDF and one Word output')
            for item in child['outputs']:
                expected_name = 'document.pdf' if item['kind'] == 'PDF' else 'document.docx'
                if item.get('path') != expected_name or (destination / expected_name).is_symlink():
                    raise ValueError('Unsafe native output path')
                if any(item.get(key) != job[key] for key in ('group', 'case', 'context_sha256', 'replies_sha256', 'knowledge_model_sha256')):
                    raise ValueError('Native receipt differs from the planned input')
                item['path'] = str((destination / item['path']).relative_to(output))
                if sha(output / item['path']) != item['sha256']:
                    raise ValueError('Native output changed after rendering')
                report['outputs'].append(item)
            if sha(job['context']) != job['context_sha256'] or sha(job['config']) != job['config_sha256']:
                raise ValueError('Caller input changed during rendering')
        verify_build(build, yaml.safe_load(args.pipeline.read_text()))
        if sha(build / 'manifest.json') != report['manifest_sha256'] or sha(args.pipeline) != report['pipeline_sha256']:
            raise ValueError('Build or pipeline changed during rendering')
        report['render_passed'] = True
    except Exception as error:
        report['error_type'] = type(error).__name__
        raise
    finally:
        save(output / 'receipt.json', report)
    print(json.dumps({'render_passed': True, 'native_outputs': len(report['outputs']), 'accepted': False}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', required=True, type=Path)
    parser.add_argument('--pipeline', type=Path, default=Path(__file__).resolve().parents[1] / 'pipeline.yml')
    for flag in ('434-zh', '435-en', '435-zh'):
        parser.add_argument('--context-' + flag, required=True, action='append', type=Path)
    parser.add_argument('--context-434-en', action='append', type=Path,
                        help='Also verify the shared English ZIP with stock 4.34; pair with the other groups')
    for version in ('434', '435'):
        parser.add_argument('--config-' + version, required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--profile', choices=('submission', 'review'), default='submission')
    parser.add_argument('--plan-only', action='store_true', help='Validate inputs and print output counts without running Docker or creating artifacts')
    try:
        run(parser.parse_args())
    except Exception as error:
        print(json.dumps({'render_passed': False, 'error_type': type(error).__name__, 'error': 'Local preview failed; context and configuration details are suppressed.'}), file=sys.stderr)
        sys.exit(1)
