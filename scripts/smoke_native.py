"""Public empty-context package smoke; not answer or visual acceptance.

Exercise the exact built EN/Chinese packages with both stock Worker versions.
This fixture has no real project, answers, credentials, or Server connection.
"""
import argparse
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import uuid
import zipfile

from dsw.models.document_context.wire import DocumentContext

import preview_native


def synthetic_context():
    """Use the official 4.35 wire schema to fill an intentionally empty KM."""
    identifier = lambda name: str(uuid.uuid5(uuid.NAMESPACE_URL, 'public-native-smoke:' + name))
    timestamp = '2026-01-01T00:00:00Z'
    stamps = dict(createdAt=timestamp, updatedAt=timestamp)
    return DocumentContext.model_validate({
        'metamodelVersion': '18.3',
        'config': {'clientUrl': 'https://example.invalid', 'logoUrl': '',
                   'appTitle': 'Public native smoke', 'appTitleShort': 'Smoke',
                   'primaryColor': '#0033aa', 'illustrationsColor': '#0033aa'},
        'document': dict(uuid=identifier('document'), name='Public native package smoke',
                         documentTemplateUuid=identifier('template'), formatUuid=identifier('format'),
                         language='en', createdAt=timestamp),
        'project': dict(uuid=identifier('project'), name='Public synthetic project', replies={},
                        labels={}, versions=[], projectTags=[], files=[], **stamps),
        'knowledgeModel': {'uuid': identifier('km')},
        'knowledgeModelPackage': dict(uuid=identifier('package'), name='Empty synthetic KM',
                                      organizationId='example', kmId='empty-native-smoke', version='1.0.0',
                                      versions=['1.0.0'], description='Public package-entry smoke only',
                                      language='en', createdAt=timestamp),
        'report': dict(uuid=identifier('report'), totalReport={'indications': [], 'metrics': []},
                       chapterReports=[], chapters=[], metrics=[], **stamps),
        'organization': dict(tenantUuid=identifier('tenant'), name='Public synthetic organization',
                             description='Not a live organization', organizationId='example',
                             affiliations=[], **stamps),
    }).to_json_data()


def run(args):
    with tempfile.TemporaryDirectory(prefix='dsw-public-native-smoke-') as temporary:
        inputs = Path(temporary)
        config = inputs / 'offline-worker.yml'
        # Required parser value only: Context.initialize receives db=None and
        # the unchanged preview runner enforces --network=none.
        config.write_text('database:\n  connectionString: postgresql://example.invalid/unused\n')
        config.chmod(0o600)
        common = synthetic_context()
        selected = SimpleNamespace(build=args.build, pipeline=args.pipeline, output=args.output,
                                   config_434=config, config_435=config,
                                   profile='submission', plan_only=False)
        for suffix, version, language in [('434_en', '18.2', 'en'), ('434_zh', '18.2', 'zh-Hant'),
                                          ('435_en', '18.3', 'en'), ('435_zh', '18.3', 'zh-Hant')]:
            context = copy.deepcopy(common)
            context['metamodelVersion'] = version
            context['document']['language'] = language
            context['document']['locale'] = (dict(uuid=str(uuid.uuid5(uuid.NAMESPACE_URL, 'public-zh-locale')),
                name='Public synthetic Chinese locale', code='zh-Hant', createdAt='2026-01-01T00:00:00Z',
                updatedAt='2026-01-01T00:00:00Z') if language == 'zh-Hant' and version == '18.3' else None)
            source = inputs / (suffix + '.json')
            source.write_text(json.dumps(context))
            setattr(selected, 'context_' + suffix, [source])
        preview_native.run(selected)
        receipt = preview_native.read(args.output / 'receipt.json')
        if len(receipt['outputs']) != 8 or len({row['group'] for row in receipt['outputs']}) != 4:
            raise ValueError('The public smoke must export both formats in all four groups')
        for row in receipt['outputs']:
            path = args.output / row['path']
            if row['kind'] == 'PDF':
                if not path.read_bytes().startswith(b'%PDF-'):
                    raise ValueError('Native PDF header is missing')
            else:
                with zipfile.ZipFile(path) as archive:
                    if not archive.read('word/document.xml') or archive.testzip() is not None:
                        raise ValueError('Native Word package is invalid')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', required=True, type=Path)
    parser.add_argument('--pipeline', type=Path, default=Path(__file__).resolve().parents[1] / 'pipeline.yml')
    parser.add_argument('--output', required=True, type=Path)
    run(parser.parse_args())
