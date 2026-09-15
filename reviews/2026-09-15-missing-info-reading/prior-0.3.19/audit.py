"""Read-only template QA: public synthetic projects on the existing local runtime."""
import argparse
import copy
import json
import subprocess
import sys
from pathlib import Path
from hashlib import sha256

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
EN = ROOT.parent / 'science-europe-template'
TOOL = ROOT.parent / 'dsw-document-template-tool'
sys.path.insert(0, str(EN / 'scripts'))
from generate_pilot_fixtures import generate, IDS, uid
from generate_preservation_fixtures import preservation_cases
from generate_budget_fixtures import budget_cases
from validate_pilot_fixtures import check
from dsw_document_template_tool.api import DSWApiClient


def digest(path): return sha256(path.read_bytes()).hexdigest()


def cases(locale):
    base = preservation_cases(locale)['preservation-complete']
    costs = next(p for p in base if p.endswith(IDS['costQUuid']))
    first, second = [costs + '.' + item for item in base[costs]['value']]
    def drop(row, prefix, field):
        key = prefix + '.' + IDS[field]
        for path in list(row):
            if path == key or path.startswith(key + '.'): row.pop(path)
    mixed = copy.deepcopy(base)
    drop(mixed, first, 'costDescriptionQUuid'); drop(mixed, first, 'costCurrencyQUuid')
    drop(mixed, second, 'costAmountQUuid')
    third = costs + '.' + uid('missing-info/third-resource')
    mixed[costs]['value'].append(third.rsplit('.', 1)[1])
    for path, value in base.items():
        if path.startswith(second + '.'):
            mixed[third + path[len(second):]] = copy.deepcopy(value)
    for field in ['costTitleQUuid', 'costAllocationQUuid', 'costCoverQUuid']:
        drop(mixed, third, field)
    result = {'empty': {}, 'negative': generate(locale)['negative'],
              'partial': generate(locale)['partial'],
              'preservation-partial': preservation_cases(locale)['preservation-partial'],
              'budget-mixed-gaps': mixed}
    for name, field in [('amount', 'costAmountQUuid'), ('currency', 'costCurrencyQUuid'), ('funding', 'costCoverQUuid')]:
        row = budget_cases(locale)['budget-long']; drop(row, first, field)
        result['budget-long-no-' + name] = row
    return result


def prepare():
    out = HERE / 'fixtures'; assert not out.exists(), 'Keep previous evidence'
    out.mkdir()
    client = DSWApiClient(api_url='http://localhost:13300/wizard-api', verify_ssl=True)
    project_uuid = None; report = []
    try:
        client.login(email='albert.einstein@example.com', password='password')
        for locale, model in [('en', 'root-2.7.0.km'), ('zh-Hant', 'root-zh-hant-2.7.0.km')]:
            bundle = EN / 'fixtures/knowledge-models' / model
            project = client.create_project_from_package(name='Synthetic missing-info QA validation',
                knowledge_model_package_id=str(bundle), question_tag_uuids=[],
                visibility='PrivateProjectVisibility', sharing='RestrictedProjectSharing')
            project_uuid = project['uuid']; km = client.get_project_questionnaire(project_uuid)['knowledgeModel']
            folder = out / locale; folder.mkdir()
            for name, replies in cases(locale).items():
                errors = check(km, replies); assert not errors, (name, locale, errors)
                events = [{'type': 'SetReplyEvent', 'uuid': uid('missing-info/' + name + '/' + p), 'path': p, 'value': v}
                          for p, v in sorted(replies.items(), key=lambda pair: (pair[0].count('.'), pair[0]))]
                recipe = {'name': 'Missing information QA / ' + name, 'events_file': name + '.events.json',
                          'knowledge_model_package_id': str(bundle), 'question_tag_uuids': [],
                          'visibility': 'PrivateProjectVisibility', 'sharing': 'RestrictedProjectSharing'}
                (folder / (name + '.events.json')).write_text(json.dumps(events, ensure_ascii=False, indent=2) + '\n')
                (folder / (name + '.json')).write_text(json.dumps(recipe, ensure_ascii=False, indent=2) + '\n')
                report.append({'case': name, 'locale': locale, 'reachable_replies': len(replies), 'km_sha256': digest(bundle), 'errors': errors})
            client.delete_project(project_uuid); project_uuid = None
    finally:
        if project_uuid: client.delete_project(project_uuid)
        client.close()
    (HERE / 'fixture-validation.json').write_text(json.dumps({'rows': report, 'script_sha256': digest(Path(__file__))}, indent=2) + '\n')
    print(json.dumps({'valid_case_language_pairs': len(report)}), flush=True)


def render(build):
    rows = []
    report = HERE / 'render-results.json'; assert not report.exists()
    for name in cases('en'):
        for language, locale in [('english', 'en'), ('chinese', 'zh-Hant')]:
            for fmt in ['html', 'pdf']:
                recipe = HERE / 'fixtures' / locale / (name + '.json')
                result = subprocess.run([sys.executable, str(ROOT / 'scripts/render.py'), '--build', str(build),
                    '--project', str(recipe), '--language', language, '--format', fmt, '--name', name, '--tooling', str(TOOL)],
                    capture_output=True, text=True)
                (HERE / f'render-{name}-{language}-{fmt}.log').write_text(result.stdout + result.stderr)
                row = {'case': name, 'language': language, 'format': fmt, 'rendered': result.returncode == 0}
                rows.append(row); print(json.dumps(row), flush=True)
                report.write_text(json.dumps({'build': str(build), 'release_acceptance': False, 'rows': rows}, indent=2) + '\n')
                assert result.returncode == 0, 'Rendering failed: see local log'


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('action', choices=['prepare', 'render']); p.add_argument('--build', type=Path); a = p.parse_args()
    if a.action == 'prepare': prepare()
    else:
        assert a.build; render(a.build.resolve())
