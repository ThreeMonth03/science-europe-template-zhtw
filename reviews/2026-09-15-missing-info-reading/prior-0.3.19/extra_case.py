"""A native counterexample: answered Q7 legal basis with unanswered safeguards."""
import copy
import json
from pathlib import Path
import subprocess
import sys
from audit import HERE, ROOT, EN, TOOL, IDS, uid, preservation_cases, check, digest, DSWApiClient

NAME = 'personal-data-partial'
build = Path(sys.argv[1]).resolve()
client = DSWApiClient(api_url='http://localhost:13300/wizard-api', verify_ssl=True)
project_uuid = None; validation = []
try:
    client.login(email='albert.einstein@example.com', password='password')
    for locale, model in [('en', 'root-2.7.0.km'), ('zh-Hant', 'root-zh-hant-2.7.0.km')]:
        replies = copy.deepcopy(preservation_cases(locale)['preservation-complete'])
        parent = IDS['creatingCUuid'] + '.' + IDS['collectPersonalQUuid']
        for path in list(replies):
            if path == parent or path.startswith(parent + '.'): replies.pop(path)
        replies[parent] = {'type': 'AnswerReply', 'value': IDS['collectPersonalYesAUuid']}
        gdpr = parent + '.' + IDS['collectPersonalYesAUuid'] + '.' + IDS['cpersGdprQUuid']
        replies[gdpr] = {'type': 'AnswerReply', 'value': IDS['cpersGdprExploreAUuid']}
        followup = gdpr + '.' + IDS['cpersGdprExploreAUuid']
        replies[followup + '.' + IDS['cpersGdprLegalBasisQUuid']] = {'type': 'AnswerReply', 'value': IDS['cpersGdprLegalBasisPublicAUuid']}
        missing = [IDS['cpersGdprSafeguardsQUuid']]
        bundle = EN / 'fixtures/knowledge-models' / model
        project = client.create_project_from_package(name='Synthetic partial-Q7 QA validation', knowledge_model_package_id=str(bundle),
            question_tag_uuids=[], visibility='PrivateProjectVisibility', sharing='RestrictedProjectSharing')
        project_uuid = project['uuid']; km = client.get_project_questionnaire(project_uuid)['knowledgeModel']
        errors = check(km, replies); assert not errors, errors
        assert all(q in km['entities']['answers'][IDS['cpersGdprExploreAUuid']]['followUpUuids'] for q in missing)
        assert all(followup + '.' + q not in replies for q in missing)
        client.delete_project(project_uuid); project_uuid = None
        folder = HERE / 'fixtures' / locale; target = folder / (NAME + '.json'); assert not target.exists()
        events = [{'type': 'SetReplyEvent', 'uuid': uid(NAME + '/' + path), 'path': path, 'value': value}
                  for path, value in sorted(replies.items(), key=lambda item: (item[0].count('.'), item[0]))]
        (folder / (NAME + '.events.json')).write_text(json.dumps(events, ensure_ascii=False, indent=2) + '\n')
        target.write_text(json.dumps({'name': 'Missing information QA / ' + NAME, 'events_file': NAME + '.events.json',
            'knowledge_model_package_id': str(bundle), 'question_tag_uuids': [], 'visibility': 'PrivateProjectVisibility',
            'sharing': 'RestrictedProjectSharing'}, indent=2) + '\n')
        validation.append({'locale': locale, 'errors': errors, 'missing_reachable_questions': missing,
                           'missing_paths': [followup + '.' + q for q in missing], 'km_sha256': digest(bundle)})
finally:
    if project_uuid: client.delete_project(project_uuid)
    client.close()
(HERE / 'extra-fixture-validation.json').write_text(json.dumps({'script_sha256': digest(Path(__file__)), 'rows': validation}, indent=2) + '\n')
results = []
for language, locale in [('english', 'en'), ('chinese', 'zh-Hant')]:
    for fmt in ['html', 'pdf']:
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/render.py'), '--build', str(build), '--project',
            str(HERE / 'fixtures' / locale / (NAME + '.json')), '--language', language, '--format', fmt, '--name', NAME, '--tooling', str(TOOL)],
            capture_output=True, text=True)
        (HERE / f'render-{NAME}-{language}-{fmt}.log').write_text(result.stdout + result.stderr)
        row = {'case': NAME, 'language': language, 'format': fmt, 'rendered': result.returncode == 0}; results.append(row)
        (HERE / 'extra-render-results.json').write_text(json.dumps(results, indent=2) + '\n')
        print(json.dumps(row), flush=True); assert result.returncode == 0
