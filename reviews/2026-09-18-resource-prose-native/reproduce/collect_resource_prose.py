"""Freeze native Q15 prose pairs separately from the earlier offline diagnostic."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
from bs4 import BeautifulSoup
from artifact_utils import sha
from collect_profile_pagination import contact
from rehearse_resource_prose import SENTENCES
from check_short_budget_outputs import prompt_lines

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('build','prior','candidate','english','report','lifecycle','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--diagnostics',nargs='*',type=Path,default=[])
    a=p.parse_args();assert not a.output.exists()
    report=json.loads(a.report.read_text());assert report['selected_checks_passed'] and len(report['rows'])==16
    assert report['native_export'] and not report['release_acceptance'] and not report['microsoft_word_acceptance']
    assert report['checker_sha256']==sha(ROOT/'scripts/check_resource_prose_outputs.py')
    assert report['contract_sha256']==sha(a.english/'scripts/resource_prose_contract.py')
    state=json.loads(a.lifecycle.read_text());assert state['stock_worker_restored'] and state['deleted_owned_templates']==2
    assert len(state['after'])==4 and all(r['status']=='exited' for r in state['after'])
    a.output.mkdir(parents=True)
    def keep(source,name):
        target=a.output/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    keep(a.report,'provenance/native-comparison.json');keep(a.lifecycle,'provenance/worker-lifecycle.json')
    for name in ('manifest.json','resource-prose-scope.json','resource-prose-translation.json',
                 'short-resources-engine-en.json','short-resources-engine-zh.json','structure-audit.json','translation-audit.json'):
        keep(a.candidate/name,'provenance/candidate-'+name)
    for phase,folder in [('before',a.prior),('after',a.build)]:
        for name in ('manifest.json','missing-info-render-report.json','owned-test-template-cleanup.json'):
            keep(folder/name,'provenance/'+phase+'-'+name)
        for path in folder.glob('word-preview-*.json'):keep(path,'provenance/'+phase+'-'+path.name)
    for name in (*report['helper_sha256'],'check_resource_prose_outputs.py','collect_resource_prose.py','probe_resource_prose_translation.py'):
        keep(ROOT/'scripts'/name,'reproduce/'+name)
    for name in ('scripts/resource_prose_contract.py','scripts/short_resources_contract.py','scripts/probe_short_resources.py',
                 'src/resource-prose.html.j2','src/questions/15-required-resources.html.j2','src/pdf/short-resources.html.j2'):
        keep(a.english/name,'reproduce/english/'+name)
    keep(ROOT/'pipeline.yml','reproduce/pipeline.yml')
    for path in a.diagnostics:keep(path,'diagnostics/'+path.name)
    metrics=[];inventory=[]
    for row in report['rows']:
        stem=row['case']+'-'+row['profile']+'-'+row['language']
        for phase,folder,key in [('before',a.prior,'prior_artifact_sha256'),('after',a.build,'artifact_sha256')]:
            for name,digest in row[key].items():
                source=folder/name;assert sha(source)==digest
                if name.endswith('.html'):
                    soup=BeautifulSoup(source.read_text(),'html.parser');questions=soup.select('.question');assert len(questions)==15
                    target=a.output/phase/'question-content'/source.name;target.parent.mkdir(parents=True,exist_ok=True)
                    target.write_text('<!-- Native HTML SHA256: '+digest+' -->\n'+'\n'.join(str(q) for q in questions)+'\n')
                else:keep(source,phase+'/'+name.replace('renders/','native/',1))
            inventory.append(dict(phase=phase,stem=stem,pdf_pages=row['formats']['pdf']['pages'],word_pages=row['formats']['word']['pages']))
        if row['case']!='profile-partial':continue
        first,endings=SENTENCES[row['language']]
        soup=BeautifulSoup((a.prior/'renders'/(stem+'.html')).read_text(),'html.parser')
        hardware=soup.select_one('#q-required-resources [data-fact-id="hardware-software"]')
        last=hardware.find_next_sibling().get_text();assert last in endings
        for kind,folder in [('pdf','renders'),('word','word-preview')]:
            old,new=[root/folder/(stem+'.pdf') for root in (a.prior,a.build)]
            before=[prompt_lines(old,s) for s in (first,last)];after=prompt_lines(new,first+last)
            metrics.append(dict(stem=stem,kind=kind,before=before,after=after,before_line_count=sum(r['line_count'] for r in before),
                after_line_count=after['line_count'],before_pdf_sha256=sha(old),after_pdf_sha256=sha(new)))
            contact(new,a.output/'visual'/(stem+'-'+kind+'.png'),stem+' native '+kind)
            if row['language']=='chinese' and row['profile']=='submission':
                for phase,pdf,pages in [('before',old,{5,6}),('after',new,{6})]:
                    for page in sorted(pages):
                        target=a.output/'visual'/(kind+'-'+phase+'-chinese-submission-p'+str(page))
                        subprocess.run(['pdftoppm','-f',str(page),'-l',str(page),'-scale-to','1600','-singlefile','-png',str(pdf),str(target)],check=True,capture_output=True)
    (a.output/'provenance/line-metrics.json').write_text(json.dumps(dict(rows=metrics,release_acceptance=False),indent=2)+'\n')
    (a.output/'inventory.json').write_text(json.dumps(dict(version='0.3.41',native_export=True,release_acceptance=False,
        microsoft_word_acceptance=False,collector_sha256=sha(Path(__file__)),rows=inventory),indent=2)+'\n')
    print(json.dumps(dict(pairs=16,native_pdf_docx=64,word_previews=32)))


if __name__=='__main__':main()
