"""Validate selected public synthetic replies, then render serially on local DSW."""
import argparse
import json
import subprocess
import sys
from pathlib import Path
from artifact_utils import sha
from dsw_document_template_tool.api import DSWApiClient

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['build', 'english', 'tooling']: p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--cases', nargs='+', required=True)
    p.add_argument('--profiles', nargs='+', choices=['review', 'submission'], default=['review'])
    p.add_argument('--fixtures', type=Path, help='Public synthetic fixture root containing en/ and zh-Hant/; default: locked English fixtures')
    a = p.parse_args()
    fixtures = a.fixtures.resolve() if a.fixtures else a.english.resolve()/'fixtures/pilot'
    assert len(set(a.profiles)) == len(a.profiles), 'Duplicate profiles'
    sys.path.insert(0, str(a.english.resolve()/'scripts'))
    from validate_pilot_fixtures import check
    from generate_pilot_fixtures import IDS
    report = {'all_renders_succeeded': False, 'release_acceptance': False, 'validation': [], 'renders': [],
              'checker_sha256': sha(Path(__file__)), 'package_sha256': {n: sha(a.build/n) for n in ['english.zip', 'chinese.zip']}}
    target = a.build/'missing-info-render-report.json'; assert not target.exists()
    client = DSWApiClient(api_url='http://localhost:13300/wizard-api', verify_ssl=True); project_id = None
    try:
        client.login(email='albert.einstein@example.com', password='password')
        for language, locale in [('english', 'en'), ('chinese', 'zh-Hant')]:
            folder = fixtures/locale
            recipe = json.loads((folder/(a.cases[0]+'.json')).read_text())
            bundle = (folder/recipe['knowledge_model_package_id']).resolve()
            project = client.create_project_from_package(name='Synthetic missing-info regression validation', knowledge_model_package_id=str(bundle),
                question_tag_uuids=[], visibility='PrivateProjectVisibility', sharing='RestrictedProjectSharing')
            project_id = project['uuid']; km = client.get_project_questionnaire(project_id)['knowledgeModel']
            for name in a.cases:
                recipe = json.loads((folder/(name+'.json')).read_text())
                assert (folder/recipe['knowledge_model_package_id']).resolve() == bundle
                events = folder/recipe['events_file']; replies = {e['path']: e['value'] for e in json.loads(events.read_text())}
                errors = check(km, replies); assert not errors, (name, locale, errors)
                if name == 'personal-data-partial':
                    assert IDS['cpersGdprSafeguardsQUuid'] in km['entities']['answers'][IDS['cpersGdprExploreAUuid']]['followUpUuids']
                    assert not any(path.endswith(IDS['cpersGdprSafeguardsQUuid']) for path in replies)
                report['validation'].append({'case': name, 'language': language, 'reachable_replies': len(replies),
                    'events_sha256': sha(events), 'km_sha256': sha(bundle), 'errors': errors})
            client.delete_project(project_id); project_id = None
    finally:
        if project_id: client.delete_project(project_id)
        client.close()
        target.write_text(json.dumps(report, indent=2)+'\n')
    for case, profile in [(case, profile) for case in a.cases for profile in a.profiles]:
        name = case if a.profiles == ['review'] else case+'-'+profile
        for language, locale in [('english', 'en'), ('chinese', 'zh-Hant')]:
            for fmt in ['html', 'pdf', 'docx']:
                result = subprocess.run([sys.executable, str(ROOT/'scripts/render.py'), '--build', str(a.build),
                    '--project', str(fixtures/locale/(case+'.json')), '--language', language,
                    '--format', fmt, '--profile', profile, '--name', name, '--tooling', str(a.tooling)], capture_output=True, text=True)
                (a.build/f'render-{name}-{language}-{fmt}.log').write_text(result.stdout+result.stderr)
                row = {'case': name, 'fixture_case': case, 'profile': profile, 'language': language, 'format': fmt, 'rendered': result.returncode == 0}
                report['renders'].append(row); target.write_text(json.dumps(report, indent=2)+'\n')
                print(json.dumps(row), flush=True); assert row['rendered'], 'See local render log'
    report['all_renders_succeeded'] = True
    target.write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__': main()
