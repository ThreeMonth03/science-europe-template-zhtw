"""Clean only a finished synthetic run's two staged local templates with ZIP backups."""
import argparse
import json
from pathlib import Path
import re
import subprocess
from artifact_utils import sha
from dsw_document_template_tool.api import DSWApiClient

ROOT = Path(__file__).resolve().parents[1]


def validate_render_report(report, expected, allow_failed=False):
    rows = report['renders']
    assert len(rows) == expected and rows
    if allow_failed:
        assert not report['all_renders_succeeded']
        assert rows[-1]['rendered'] is False and all(r['rendered'] is True for r in rows[:-1])
    else:
        assert report['all_renders_succeeded'] and all(r['rendered'] is True for r in rows)


def validate_template_scope(report, expected_templates, expected_renders, allow_failed):
    assert expected_templates in [1, 2]
    validate_render_report(report, expected_renders, allow_failed)
    if expected_templates == 1:
        assert allow_failed and expected_renders == 1
        assert report['renders'][0]['language'] == 'english'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,required=True);p.add_argument('--version',required=True)
    p.add_argument('--expected-renders',type=int,required=True)
    p.add_argument('--expected-templates',type=int,choices=[1,2],default=2,
                   help='One is allowed only for a batch failing on its first English render')
    p.add_argument('--allow-failed-run',action='store_true',help='Explicitly clean a stopped batch ending in one failed render; never marks it passed')
    a=p.parse_args()
    if a.expected_templates == 1:
        assert a.allow_failed_run and a.expected_renders == 1
    root=a.build.resolve();assert root.is_relative_to(ROOT/'outputs')
    target=root/'owned-test-template-cleanup.json';assert not target.exists()
    manifest=json.loads((root/'manifest.json').read_text());assert manifest['status']=='runtime-experiment'
    assert manifest['source']['version']==a.version and manifest['translation']['version']==a.version
    renders=json.loads((root/'missing-info-render-report.json').read_text())
    validate_template_scope(renders, a.expected_templates, a.expected_renders, a.allow_failed_run)
    found=sorted({v for f in root.glob('render-*.log') for v in re.findall(r'with released template ([0-9a-f-]{36})',f.read_text())})
    assert len(found)==a.expected_templates and all(re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',v) for v in found)
    if a.expected_templates == 1: assert renders['renders'][0]['language'] == 'english'
    backups={}
    for file,digest in renders['package_sha256'].items():
        assert file in ['english.zip','chinese.zip'] and sha(root/file)==digest
        backups[file]={'path':str(root/file),'sha256':digest}
    assert len(backups)==2
    ids=','.join("'"+v+"'" for v in found)
    sql='SELECT count(*) FROM project WHERE document_template_uuid IN ('+ids+'); SELECT count(*) FROM document WHERE document_template_uuid IN ('+ids+');'
    counts=subprocess.check_output(['docker','exec','science-europe-pilot-postgres-1','sh','-c',
        'exec psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "$1"','local-owned-template-check',sql],text=True).splitlines()
    assert counts==['0','0']
    result={'scope':'Only this finished synthetic local run; no other template or volume',
            'run_completed_successfully':renders['all_renders_succeeded'], 'failed_run_explicitly_acknowledged':a.allow_failed_run,
            'project_references':0,'document_references':0,'backups':backups,'deleted':[]}
    client=DSWApiClient(api_url='http://localhost:13300/wizard-api',verify_ssl=True)
    try:
        client.login(email='albert.einstein@example.com',password='password')
        targets=[]
        for uid in found:
            data=client._request_json('GET','/document-templates/'+uid)
            assert data['uuid']==uid and data['organizationId']=='threemonth03' and data['version']==a.version
            assert re.fullmatch(r'science-europe-enhanced(?:-zhtw)?-local-[0-9a-f]{12}',data['templateId'])
            targets.append((uid,data['templateId']))
        assert sum('-zhtw-' in name for _,name in targets)==a.expected_templates - 1
        for uid,name in targets:
            response=client._request('DELETE','/document-templates/'+uid);assert response.status_code in [200,204]
            result['deleted'].append({'uuid':uid,'templateId':name,'version':a.version,'status_code':response.status_code})
    finally:
        client.close();target.write_text(json.dumps(result,indent=2)+'\n')
    assert len(result['deleted'])==a.expected_templates
    print(json.dumps({'deleted_owned_local_templates':a.expected_templates,'zip_backups_verified':True}))


if __name__=='__main__':main()
