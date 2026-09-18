"""Freeze same-fixture native Q15 PDF comparisons and unchanged Word controls."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
from bs4 import BeautifulSoup
from artifact_utils import sha
from collect_profile_pagination import contact

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('build','prior-controls','prior-profile','candidate','english','report','lifecycle','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--diagnostics',type=Path,nargs='*',default=[])
    a=p.parse_args();assert not a.output.exists()
    report=json.loads(a.report.read_text());assert report['selected_checks_passed'] and len(report['rows'])==16
    assert not report['release_acceptance'] and not report['microsoft_word_acceptance']
    assert report['checker_sha256']==sha(ROOT/'scripts/check_short_resources_outputs.py')
    assert report['contract_sha256']==sha(a.english/'scripts/short_resources_contract.py')
    lifecycle=json.loads(a.lifecycle.read_text())
    assert lifecycle['stock_worker_restored'] and lifecycle['deleted_owned_templates']==4
    assert len(lifecycle['after'])==4 and all(r['status']=='exited' for r in lifecycle['after'])
    a.output.mkdir(parents=True)
    def keep(source,name):
        destination=a.output/name;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,destination)
    keep(a.report,'provenance/native-comparison.json')
    keep(a.lifecycle,'provenance/worker-lifecycle.json')
    for name in ('manifest.json','short-resources-scope.json','short-resources-engine-en.json','short-resources-engine-zh.json','structure-audit.json','translation-audit.json'):
        keep(a.candidate/name,'provenance/candidate-'+name)
    for phase,folder in [('before-controls',a.prior_controls),('before-profile',a.prior_profile),('after',a.build)]:
        for name in ('manifest.json','missing-info-render-report.json','owned-test-template-cleanup.json'):
            keep(folder/name,'provenance/'+phase+'-'+name)
        for path in folder.glob('word-preview-*.json'):keep(path,'provenance/'+phase+'-'+path.name)
    for name in (*report['helper_sha256'],'check_short_resources_outputs.py','collect_short_resources.py'):
        keep(ROOT/'scripts'/name,'reproduce/'+name)
    for name in ('short_resources_contract.py','probe_short_resources.py'):
        keep(a.english/'scripts'/name,'reproduce/'+name)
    for name in ('src/pdf/index.html.j2','src/pdf/short-resources.html.j2'):
        keep(a.english/name,'reproduce/'+name)
    keep(ROOT/'pipeline.yml','reproduce/pipeline.yml')
    for path in a.diagnostics:keep(path,'diagnostics/'+path.name)
    inventory=dict(version='0.3.40',native_export=True,release_acceptance=False,microsoft_word_acceptance=False,
        collector_sha256=sha(Path(__file__)),rows=[])
    for row in report['rows']:
        stem=row['case']+'-'+row['profile']+'-'+row['language']
        prior=a.prior_profile if row['case'] in ('profile-partial','empty') else a.prior_controls
        for phase,folder,key in [('before',prior,'prior_artifact_sha256'),('after',a.build,'artifact_sha256')]:
            for name,digest in row[key].items():
                source=folder/name;assert sha(source)==digest
                if name.endswith('.html'):
                    soup=BeautifulSoup(source.read_text(),'html.parser');questions=soup.select('.question');assert len(questions)==15
                    destination=a.output/phase/'question-content'/source.name;destination.parent.mkdir(parents=True,exist_ok=True)
                    destination.write_text('<!-- Native HTML SHA256: '+digest+' -->\n'+'\n'.join(str(q) for q in questions)+'\n')
                else:keep(source,phase+'/'+name.replace('renders/','native/',1))
            inventory['rows'].append(dict(phase=phase,stem=stem,pdf_pages=row['pdf_pages'],word_pages=row['word_pages']))
        if row['selected']:
            contact(a.build/'renders'/(stem+'.pdf'),a.output/'visual'/(stem+'-pdf.png'),stem)
    for phase,page in [('before',5),('before',6),('after',6)]:
        source=a.output/phase/'native/profile-partial-submission-chinese.pdf'
        subprocess.run(['pdftoppm','-f',str(page),'-l',str(page),'-scale-to','1600','-singlefile','-png',str(source),
            str(a.output/'visual'/(phase+'-chinese-submission-p'+str(page)))],check=True,capture_output=True)
    (a.output/'inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
    print(json.dumps(dict(pairs=16,native_pdf_docx=64,word_previews=32)))


if __name__=='__main__':main()
