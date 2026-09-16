"""Archive verified 0.3.29 native evidence and the four extra 0.3.28 controls."""
import argparse
import json
from pathlib import Path
import shutil
from bs4 import BeautifulSoup
from artifact_utils import sha
from check_archive_basis_outputs import CASES,EXTRA

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['build','prior','prior-extra','candidate','rebuild','english','readme','output']:
        p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.output.exists()
    report=json.loads((a.build/'archive-basis-report.json').read_text())
    assert report['selected_checks_passed'] and len(report['rows'])==16
    assert {(r['case'],r['language']) for r in report['rows']}=={(c,l) for c in CASES for l in ['english','chinese']}
    assert all(r['passed'] and not r['errors'] and not r['reading_issues'] for r in report['rows'])
    assert sha(ROOT/'scripts/check_archive_basis_outputs.py')==report['checker_sha256']
    assert sha(a.english/'scripts/archive_basis_contract.py')==report['contract_sha256']
    for name,digest in report['package_sha256'].items():assert sha(a.build/name)==sha(a.candidate/name)==sha(a.rebuild/name)==digest
    for root,count in [(a.build,48),(a.prior_extra,24)]:
        rendered=json.loads((root/'missing-info-render-report.json').read_text())
        assert rendered['all_renders_succeeded'] and len(rendered['renders'])==count
        assert all(r['rendered'] for r in rendered['renders'])
        clean=json.loads((root/'owned-test-template-cleanup.json').read_text())
        assert len(clean['deleted'])==2 and clean['project_references']==clean['document_references']==0
        for backup in clean['backups'].values():assert sha(Path(backup['path']))==backup['sha256']
    assert json.loads((a.build/'runtime-restoration.json').read_text())['restored_stock_and_stopped']
    for row in report['rows']:
        prior=a.prior_extra if row['case'] in EXTRA else a.prior
        for name,digest in row['artifact_sha256'].items():assert sha(a.build/name)==digest
        for name,digest in row['prior_artifact_sha256'].items():assert sha(prior/name)==digest
    def copy(source,name):
        dest=a.output/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
    def artifact(root,prefix,stem):
        for fmt in ['pdf','docx']:copy(root/'renders'/(stem+'.'+fmt),prefix+'/native/'+stem+'.'+fmt)
        for fmt in ['html','pdf','docx']:copy(root/'renders'/(stem+'.'+fmt+'.fixture.json'),prefix+'/native/'+stem+'.'+fmt+'.fixture.json')
        copy(root/'word-preview'/(stem+'.pdf'),prefix+'/word-preview/'+stem+'.pdf')
        html=root/'renders'/(stem+'.html');soup=BeautifulSoup(html.read_text(),'html.parser')
        dest=a.output/prefix/'question-content'/(stem+'.html');dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text('<!-- Native HTML SHA256: '+sha(html)+' -->\n'+str(soup.select_one('#dmp-content'))+'\n')
    for row in report['rows']:
        stem=row['case']+'-'+row['language'];artifact(a.build,'after',stem)
        if row['case'] in EXTRA:artifact(a.prior_extra,'before-extra',stem)
        locale='en' if row['language']=='english' else 'zh-Hant'
        for suffix in ['.json','.events.json']:copy(a.english/'fixtures/pilot'/locale/(row['case']+suffix),'fixtures/'+locale+'/'+row['case']+suffix)
    for name in ['manifest.json','archive-basis-report.json','missing-info-render-report.json','owned-test-template-cleanup.json',
                 'worker-start.json','worker-lifecycle.json','runtime-restoration.json']:
        copy(a.build/name,'after/'+name)
    for name in ['manifest.json','missing-info-render-report.json','owned-test-template-cleanup.json']:
        copy(a.prior_extra/name,'before-extra/'+name)
    for label,root in [('candidate',a.candidate),('rebuild',a.rebuild)]:copy(root/'manifest.json',label+'-manifest.json')
    for name in ['archive-basis-translation-proof.json','personal-data-translation-proof.json',
                 'preservation-translation-probe.json','missing-info-translation-proof.json']:
        copy(a.candidate/name,'probes/'+name)
    for folder in ['diagnostics-quota','diagnostics-checker','visual']:
        for f in sorted((a.build/folder).iterdir()):
            if f.is_file():copy(f,folder+'/'+f.name)
    for f in sorted(a.build.glob('archive-basis-first-three*.json')):copy(f,'diagnostics-checker/'+f.name)
    for name in ['check_archive_basis_outputs.py','probe_archive_basis_translation.py','probe_personal_data_translation.py',
                 'probe_missing_info_translation.py','collect_archive_basis_review.py']:
        copy(ROOT/'scripts'/name,'reproduce/'+name)
    copy(a.english/'scripts/archive_basis_contract.py','reproduce/archive_basis_contract.py')
    copy(ROOT/'pipeline.yml','reproduce/pipeline.yml')
    copy(ROOT/'docs/archive-basis-translation-delta.json','reproduce/archive-basis-translation-delta.json')
    for lang in ['en','translated']:copy(a.candidate/lang/'src/post-project-archive.html.j2','source/'+lang+'/post-project-archive.html.j2')
    copy(a.readme,'README.md')
    checks={str(f.relative_to(a.output)):sha(f) for f in sorted(a.output.rglob('*')) if f.is_file()}
    (a.output/'checksums.json').write_text(json.dumps(checks,indent=2)+'\n')
    print(json.dumps({'archived':str(a.output),'native_outputs':48,'word_previews':16,'extra_baseline_outputs':24,'files':len(checks)}))


if __name__=='__main__':main()
