"""Archive verified bilingual Q13 native comparisons and rejected extraction checks."""
import argparse
import json
from pathlib import Path
import shutil
from bs4 import BeautifulSoup
from artifact_utils import sha
from check_identifier_concise_outputs import CASES

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['build','candidate','rebuild','english','destination']:
        p.add_argument('--'+name,type=Path,required=True)
    a = p.parse_args(); assert not a.destination.exists()
    report = json.loads((a.build/'identifier-concise-report.json').read_text())
    assert report['selected_checks_passed'] and len(report['rows']) == 16
    assert {(r['case'],r['language']) for r in report['rows']} == {(c,l) for c in CASES for l in ['english','chinese']}
    assert all(not r['errors'] and not r['reading_issues'] for r in report['rows'])
    assert report['checker_sha256'] == sha(ROOT/'scripts/check_identifier_concise_outputs.py')
    for root in [a.build,a.candidate,a.rebuild]:
        assert {n:sha(root/n) for n in report['package_sha256']} == report['package_sha256']
    for root in [a.candidate,a.rebuild]:
        m=json.loads((root/'manifest.json').read_text())
        assert m['status']=='candidate' and all(not x['dirty'] for x in m['checkouts'].values())
    renders=json.loads((a.build/'missing-info-render-report.json').read_text())
    assert renders['all_renders_succeeded'] and len(renders['renders'])==48 and all(r['rendered'] for r in renders['renders'])
    lifecycle=json.loads((a.build/'worker-lifecycle.json').read_text())
    assert lifecycle['all_48_renders_completed'] and lifecycle['no_container_restart_during_run'] and not lifecycle['font_patch_applied']
    cleanup=json.loads((a.build/'owned-test-template-cleanup.json').read_text())
    assert len(cleanup['deleted'])==2 and cleanup['project_references']==cleanup['document_references']==0
    restored=json.loads((a.build/'runtime-restoration.json').read_text())
    assert restored['stock_worker_restored'] and len(restored['services'])==4 and all(not s['running'] for s in restored['services'])
    copies=[]; excerpts={}
    def keep(source,name):
        assert source.is_file(),source
        copies.append((source,Path(name)))
    for row in report['rows']:
        prior=Path(row['prior_root']); stem=row['case']+'-'+row['language']
        for root,hashes in [(prior,row['prior_artifact_sha256']),(a.build,row['artifact_sha256'])]:
            assert all(sha(root/name)==value for name,value in hashes.items())
        for side,root in [('before',prior),('after',a.build)]:
            for fmt in ['pdf','docx']:
                for extra in ['', '.fixture.json']:
                    keep(root/'renders'/(stem+'.'+fmt+extra),side+'/native/'+stem+'.'+fmt+extra)
            keep(root/'renders'/(stem+'.html.fixture.json'),side+'/native/'+stem+'.html.fixture.json')
            keep(root/'word-preview'/(stem+'.pdf'),side+'/word-preview/'+stem+'.pdf')
            source=root/'renders'/(stem+'.html'); soup=BeautifulSoup(source.read_text(),'html.parser')
            excerpts[side+'/question-content/'+stem+'.html']='<!-- Full HTML SHA256: '+sha(source)+' -->\n'+str(soup.select_one('#dmp-content'))+'\n'
        if row['case']=='identifier-followups' and row['language']=='english':
            for name in ['manifest.json','missing-info-render-report.json','owned-test-template-cleanup.json','worker-start.json']:
                keep(prior/name,'before/identifier-followups-'+name)
        locale='en' if row['language']=='english' else 'zh-Hant'
        for suffix in ['.json','.events.json']:
            keep(a.english/'fixtures/pilot'/locale/(row['case']+suffix),'fixtures/'+locale+'/'+row['case']+suffix)
    for name in ['identifier-concise-report.json','manifest.json','missing-info-render-report.json',
                 'worker-start.json','worker-lifecycle.json','owned-test-template-cleanup.json','runtime-restoration.json']:
        keep(a.build/name,'after/'+name)
    for file in a.build.glob('word-preview-*.json'):keep(file,'after/'+file.name)
    for name in ['identifier-concise-scope.json','identifier-translation-probe.json']:
        assert json.loads((a.candidate/name).read_text())['passed']
        keep(a.candidate/name,'probes/'+name)
    for label,root in [('candidate',a.candidate),('rebuild',a.rebuild)]:keep(root/'manifest.json',label+'-manifest.json')
    for suffix,script in [('', 'v1'),('-v2','v2'),('-v3','v3')]:
        name='identifier-concise-targets'+suffix+'.json'
        check=json.loads((a.build/name).read_text())
        code=a.build/('check_identifier_concise_outputs-'+script+'.py')
        assert sha(code)==check['checker_sha256']
        assert check['selected_checks_passed']==(script=='v3')
        keep(a.build/name,'diagnostics/'+name);keep(code,'diagnostics/'+code.name)
    for name in ['check_identifier_concise_outputs.py','collect_identifier_concise_review.py','probe_identifier_concise_scope.py',
                 'probe_identifier_translation.py','identifier_followup_contract.py']:
        keep(ROOT/'scripts'/name,'reproduce/'+name)
    keep(a.english/'scripts/identifier_concise_contract.py','reproduce/identifier_concise_contract.py')
    keep(ROOT/'pipeline.yml','reproduce/pipeline.yml')
    for locale,folder in [('en','en'),('zh-Hant','translated')]:
        keep(ROOT/'tests/fixtures'/('identifier-0.3.26.'+locale+'.html.j2'),'source/before-'+locale+'.html.j2')
        keep(a.candidate/folder/'src/questions/13-persistent-identifier.html.j2','source/after-'+locale+'.html.j2')
    for name in ['translation-audit.json','migration.json']:
        root=ROOT/'outputs'/('build-sbfie0al' if name=='translation-audit.json' else 'build-v5y3r07e')
        keep(root/name,'diagnostics/translation-refresh/'+name)
    a.destination.mkdir(parents=True)
    for source,name in copies:
        target=a.destination/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    for name,text in excerpts.items():
        target=a.destination/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(text)
    print(a.destination)


if __name__=='__main__': main()
