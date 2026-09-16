"""Archive verified 0.3.28 evidence without duplicating the frozen prior review."""
import argparse
import json
from pathlib import Path
import shutil
from bs4 import BeautifulSoup
from artifact_utils import sha
from check_identifier_spacing_outputs import CASES

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['build','prior','candidate','rebuild','english','readme','output']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.output.exists()
    report=json.loads((a.build/'identifier-spacing-report.json').read_text())
    assert report['selected_checks_passed'] and len(report['rows'])==16
    assert {(r['case'],r['language']) for r in report['rows']}=={(c,l) for c in CASES for l in ['english','chinese']}
    assert all(r['passed'] and not r['errors'] and not r['reading_issues'] for r in report['rows'])
    for file,digest in report['package_sha256'].items():
        assert sha(a.build/file)==sha(a.candidate/file)==sha(a.rebuild/file)==digest
    render=json.loads((a.build/'missing-info-render-report.json').read_text())
    assert render['all_renders_succeeded'] and len(render['renders'])==48
    assert all(r['rendered'] for r in render['renders'])
    clean=json.loads((a.build/'owned-test-template-cleanup.json').read_text())
    assert len(clean['deleted'])==2 and clean['project_references']==clean['document_references']==0
    assert json.loads((a.build/'runtime-restoration.json').read_text())['restored_stock_and_stopped']
    for row in report['rows']:
        for file,digest in row['artifact_sha256'].items():assert sha(a.build/file)==digest
        for file,digest in row['prior_artifact_sha256'].items():assert sha(a.prior/file)==digest
    def copy(source,name):
        dest=a.output/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
    for row in report['rows']:
        stem=row['case']+'-'+row['language']
        for fmt in ['pdf','docx']:copy(a.build/'renders'/(stem+'.'+fmt),'after/native/'+stem+'.'+fmt)
        for fmt in ['html','pdf','docx']:copy(a.build/'renders'/(stem+'.'+fmt+'.fixture.json'),'after/native/'+stem+'.'+fmt+'.fixture.json')
        copy(a.build/'word-preview'/(stem+'.pdf'),'after/word-preview/'+stem+'.pdf')
        html=a.build/'renders'/(stem+'.html');soup=BeautifulSoup(html.read_text(),'html.parser')
        dest=a.output/'after/question-content'/(stem+'.html');dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text('<!-- Native HTML SHA256: '+sha(html)+' -->\n'+str(soup.select_one('#dmp-content'))+'\n')
        locale='en' if row['language']=='english' else 'zh-Hant'
        for suffix in ['.json','.events.json']:copy(a.english/'fixtures/pilot'/locale/(row['case']+suffix),'fixtures/'+locale+'/'+row['case']+suffix)
    for name in ['manifest.json','identifier-spacing-report.json','missing-info-render-report.json',
                 'owned-test-template-cleanup.json','worker-start.json','worker-lifecycle.json','runtime-restoration.json']:
        copy(a.build/name,'after/'+name)
    for name in ['identifier-spacing-targets-v1.json','identifier-spacing-targets-v1-error.txt','check_identifier_spacing_outputs-v1.py','identifier-spacing-targets-v2.json']:
        copy(a.build/name,'diagnostics/'+name)
    for label,root in [('candidate',a.candidate),('rebuild',a.rebuild)]:copy(root/'manifest.json',label+'-manifest.json')
    for name in ['identifier-spacing-scope.json','identifier-translation-probe.json','identifier-spacing-engine.json']:
        copy(a.candidate/name,'probes/'+name)
    for name in ['check_identifier_spacing_outputs.py','probe_identifier_spacing_scope.py','collect_identifier_spacing_review.py']:
        copy(ROOT/'scripts'/name,'reproduce/'+name)
    copy(a.english/'scripts/probe_identifier_spacing.py','reproduce/probe_identifier_spacing.py')
    copy(ROOT/'pipeline.yml','reproduce/pipeline.yml')
    for lang in ['en','translated']:
        for name in ['layout.css','word/pilot.lua','questions/13-persistent-identifier.html.j2']:
            copy(a.candidate/lang/'src'/name,'source/'+lang+'/'+name)
    copy(a.readme,'README.md')
    checks={str(f.relative_to(a.output)):sha(f) for f in sorted(a.output.rglob('*')) if f.is_file()}
    (a.output/'checksums.json').write_text(json.dumps(checks,indent=2)+'\n')
    print(json.dumps({'archived':str(a.output),'verified_native_outputs':48,'verified_word_previews':16}))


if __name__=='__main__':main()
