"""Freeze paired 0.3.41/42 native short-row evidence, never overwrite an archive."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
from bs4 import BeautifulSoup
from artifact_utils import sha

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['build','prior','candidate','english','report','lifecycle','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();assert not a.output.exists()
    report=json.loads(a.report.read_text());assert report['selected_checks_passed'] and len(report['rows'])==16
    assert report['native_export'] and not report['release_acceptance'] and not report['microsoft_word_acceptance']
    assert report['checker_sha256']==sha(ROOT/'scripts/check_short_resource_rows_outputs.py')
    assert report['contract_sha256']==sha(a.english/'scripts/short_resource_rows_contract.py')
    state=json.loads(a.lifecycle.read_text());assert state['stock_worker_restored'] and state['deleted_owned_templates']==2
    assert len(state['after'])==4 and all(r['status']=='exited' for r in state['after'])
    a.output.mkdir(parents=True)
    def keep(source,name):
        target=a.output/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    keep(a.report,'provenance/native-comparison.json');keep(a.lifecycle,'provenance/worker-lifecycle.json')
    for name in ['manifest.json','short-resource-rows-scope.json','resource-prose-translation.json',
                 'short-resource-rows-engine-en.json','short-resource-rows-engine-zh.json','structure-audit.json','translation-audit.json']:
        keep(a.candidate/name,'provenance/candidate-'+name)
    for phase,folder in [('before',a.prior),('after',a.build)]:
        for name in ['manifest.json','missing-info-render-report.json','owned-test-template-cleanup.json']:keep(folder/name,'provenance/'+phase+'-'+name)
        for path in folder.glob('word-preview-*.json'):keep(path,'provenance/'+phase+'-'+path.name)
    for name in [*report['helper_sha256'],'check_short_resource_rows_outputs.py','collect_short_resource_rows.py']:
        keep(ROOT/'scripts'/name,'reproduce/'+name)
    for name in ['scripts/short_resource_rows_contract.py','scripts/probe_short_resource_rows.py','src/pdf/short-resource-rows.html.j2','src/budget-reading.html.j2']:
        keep(a.english/name,'reproduce/english/'+name)
    keep(ROOT/'pipeline.yml','reproduce/pipeline.yml')
    for row in report['rows']:
        stem='-'.join([row['case'],row['profile'],row['language']])
        for phase,folder,key in [('before',a.prior,'prior_artifact_sha256'),('after',a.build,'artifact_sha256')]:
            for name,digest in row[key].items():
                source=folder/name;assert sha(source)==digest
                if name.endswith('.html'):
                    soup=BeautifulSoup(source.read_text(),'html.parser');questions=soup.select('.question');assert len(questions)==15
                    target=a.output/phase/'question-content'/source.name;target.parent.mkdir(parents=True,exist_ok=True)
                    target.write_text('<!-- Native HTML SHA256: '+digest+' -->\n'+'\n'.join(str(q) for q in questions)+'\n')
                else:keep(source,phase+'/'+name.replace('renders/','native/',1))
        if row['case']=='budget-many' and row['profile']=='review':
            for phase,folder in [('before',a.prior),('after',a.build)]:
                for page in ([8,9] if row['language']=='english' else [7,8]):
                    target=a.output/'visual'/(phase+'-'+row['language']+'-p'+str(page));target.parent.mkdir(exist_ok=True)
                    subprocess.run(['pdftoppm','-f',str(page),'-l',str(page),'-scale-to','1600','-singlefile','-png',str(folder/'renders'/(stem+'.pdf')),str(target)],check=True,capture_output=True)
    (a.output/'inventory.json').write_text(json.dumps(dict(version='0.3.42',native_export=True,release_acceptance=False,
        microsoft_word_acceptance=False,collector_sha256=sha(Path(__file__)),pairs=16,native_pdf_docx=64,word_previews=32),indent=2)+'\n')
    print(json.dumps(dict(pairs=16,native_pdf_docx=64,word_previews=32)))


if __name__=='__main__':main()
