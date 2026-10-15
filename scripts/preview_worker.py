"""Container-only companion to preview_native.py; stock engine APIs only."""
import contextlib
import copy
import dataclasses
import gettext
import hashlib
import importlib.metadata as md
import io
import json
import os
from pathlib import Path
import site
import subprocess
import sys
from types import SimpleNamespace as NS
import uuid
import zipfile


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def value_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def formats(metadata, profile):
    selected = {}
    for item in metadata['formats']:
        steps = item['steps']
        jinja = [step.get('options', {}).get('template', '') for step in steps if step['name'] == 'jinja']
        if not jinja or any(name.startswith('src/submission/') for name in jinja) != (profile == 'submission'):
            continue
        kind = 'PDF' if steps[-1]['name'] == 'weasyprint' else 'Word' if any(step['name'] == 'pandoc' and step.get('options', {}).get('to') == 'docx' for step in steps) else None
        if kind:
            if kind in selected:
                raise ValueError('Ambiguous native format selection')
            selected[kind] = item['uuid']
    if set(selected) != {'PDF', 'Word'}:
        raise ValueError('Both native PDF and Word formats are required')
    return selected


def configure_python_site():
    # Host UID HOME may be /; Pandoc's Python filters also need this stock site.
    local = Path('/home/user/.local/lib') / f'python{sys.version_info.major}.{sys.version_info.minor}/site-packages'
    site.addsitedir(str(local))
    previous = os.environ.get('PYTHONPATH')
    os.environ['PYTHONPATH'] = str(local) + (os.pathsep + previous if previous else '')


def render():
    configure_python_site()
    job = read('/output/job.json')
    version, language = job['version'], job['language']
    if os.environ.get('WORKER_IMAGE') != job['worker_image'] or not md.version('dsw-document-worker').startswith(version + '.'):
        raise ValueError('Unexpected Worker runtime')
    if {line.split(':')[0].strip() for line in Path('/proc/net/dev').read_text().splitlines() if ':' in line} != {'lo'}:
        raise ValueError('Network isolation is required')
    if sha('/input/context.json') != job['context_sha256'] or sha('/input/worker.yml') != job['config_sha256']:
        raise ValueError('Mounted caller inputs differ from the plan')
    prepared = read('/input/context.json')
    from dsw.document_worker.cli import load_config_str
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        if version == '4.35':
            from dsw.config import read_config
            config = load_config_str(read_config(Path('/input/worker.yml'), encoding='utf-8'))
        else:
            config = load_config_str(Path('/input/worker.yml').read_text())
    package = Path('/build/translated' if version == '4.34' else '/build/en')
    metadata = read(package / 'template.json')
    identity = str(uuid.uuid5(uuid.NAMESPACE_URL, 'local-native-preview:' + sha(package / 'template.json')))
    coordinate = ':'.join(metadata[key] for key in ('organizationId', 'templateId', 'version'))
    if version == '4.34':
        from dsw.document_worker.context import Context
        from dsw.document_worker.templates.templates import Template, TemplateComposite
        from dsw.document_worker.worker import Job
        work = Path('/tmp/local-preview'); work.mkdir()
        Context.initialize(db=None, s3=None, config=config, workdir=work)
        with zipfile.ZipFile('/build/chinese.zip') as archive:
            bundled = json.loads(archive.read('template/template.json'))
        assets = {item['uuid']: NS(uuid=item['uuid'], file_name=item['fileName'], content_type=item['contentType']) for item in bundled['assets']}
    else:
        from dsw.document_worker.templates.templates import render_settings
        from dsw.models.document_context.wire import DocumentContext
        from dsw.models.strictness import UnknownKeys, load
        from dsw.templating import ContextDefaults, RenderContext, Template, TemplateLocale, enrich_context_config
    outputs = []
    for kind, format_id in formats(metadata, job['profile']).items():
        context = copy.deepcopy(prepared)
        bindings = []
        for key, value in [('formatUuid', format_id), ('documentTemplateUuid', identity)]:
            if context['document'].get(key) != value:
                bindings.append({'path': '/document/' + key, 'before': context['document'].get(key), 'after': value})
                context['document'][key] = value
        document = copy.deepcopy(context['document'])
        if version == '4.34':
            engine = Template('local-native-preview', package, TemplateComposite(NS(uuid=identity, coordinates=coordinate, formats=metadata['formats']), {}, assets))
        else:
            load(DocumentContext, context, unknown_keys=UnknownKeys.IGNORE)
            engine = Template.from_directory(package, template_uuid=identity, settings=render_settings(config, coordinate))
        if not engine.prepare_format(format_id):
            raise ValueError('Native format cannot be prepared')
        fmt = engine[format_id]
        if [step.NAME for step in fmt.steps[:3]] != ['jinja', 'pandoc', 'jinja']:
            raise ValueError('Unexpected native entry pipeline')
        if any(fmt.requires_via_extras(key) for key in ('project', 'questionnaire', 'submissions')):
            raise ValueError('Server-dependent template extras are not supported')
        context['extras'] = {}
        if version == '4.34':
            Job._enrich_context_config(NS(doc_context=context, ctx=Context.get()))
            Context.get().app.pm.hook.enrich_document_context(context=context)
            engine.project_uuid = context['project']['uuid']
        else:
            enrich_context_config(context, ContextDefaults(**dataclasses.asdict(config.context)))
            engine.plugins.hook.enrich_document_context(context=context)
            locale = TemplateLocale.load(document['locale'])
            catalog = gettext.GNUTranslations(Path('/build/zh-Hant.mo').open('rb')) if language == 'zh-Hant' else gettext.NullTranslations()
            engine.render_ctx = RenderContext(translations=catalog, language=language, locale=locale)
            for step in fmt.steps:
                step.before_render(engine.render_ctx)
        if context['project'] != prepared['project'] or context['knowledgeModel'] != prepared['knowledgeModel'] or context['document'] != document:
            raise ValueError('Runtime enrichment changed protected caller data')
        effective, result, entry_sha = copy.deepcopy(context), None, None
        for index, step in enumerate(fmt.steps):
            result = step.execute_first(context) if index == 0 else step.execute_follow(result, context)
            if context != effective:
                raise ValueError('Rendering changed the effective context')
            if index == 2:
                entry_sha = hashlib.sha256(result.content).hexdigest()
        extension = 'pdf' if kind == 'PDF' else 'docx'
        if result.file_format.file_extension != extension or not entry_sha:
            raise ValueError('Unexpected native output format')
        destination = Path('/output/document.' + extension)
        with destination.open('xb') as stream:
            stream.write(result.content)
        outputs.append({'path': destination.name, 'sha256': sha(destination), 'case': job['case'], 'group': job['group'], 'kind': kind,
            'context_sha256': job['context_sha256'], 'replies_sha256': value_sha(prepared['project']['replies']),
            'knowledge_model_sha256': value_sha(prepared['knowledgeModel']), 'entry_html_sha256': entry_sha, 'bindings': bindings})
    return {'render_passed': True, 'outputs': outputs, 'runtime': {name: md.version(name) for name in ('dsw-document-worker', 'Jinja2', 'WeasyPrint')} | {'pandoc': subprocess.check_output(['pandoc', '--version'], text=True).splitlines()[0]}}


if __name__ == '__main__':
    os.umask(0o077)
    try:
        receipt = render()
    except Exception as error:
        receipt = {'render_passed': False, 'error_type': type(error).__name__, 'outputs': []}
    with Path('/output/worker-receipt.json').open('x') as stream:
        json.dump(receipt, stream, indent=2)
    sys.exit(0 if receipt['render_passed'] else 1)
