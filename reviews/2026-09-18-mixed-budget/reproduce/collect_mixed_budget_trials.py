"""Archive native inputs and explicitly non-native mixed-budget PDF rehearsals."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
from bs4 import BeautifulSoup
from artifact_utils import sha
from check_short_resources_outputs import fonts

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['source','trial','candidate','english','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();assert not a.output.exists()
    report=json.loads((a.trial/'report.json').read_text());assert report['completed'] and len(report['rows'])==8
    for key in ['template_modified','native_export','word_modified','release_acceptance','microsoft_word_acceptance']:assert report[key] is False
    assert report['checker_sha256']==sha(ROOT/'scripts/rehearse_mixed_budget.py')
    assert report['contract_sha256']==sha(ROOT/'scripts/mixed_budget_trial.py')
    state=json.loads((a.source/'worker-lifecycle.json').read_text())
    assert state['stock_worker_restored'] and state['deleted_owned_templates']==2 and all(v['status']=='exited' for v in state['after'])
    a.output.mkdir(parents=True)
    def keep(source,name):
        target=a.output/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    def questions(source,name):
        soup=BeautifulSoup(source.read_text(),'html.parser');values=soup.select('.question');assert len(values)==15
        target=a.output/name;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text('<!-- Full HTML SHA256: '+sha(source)+' -->\n'+'\n'.join(str(v) for v in values)+'\n')
    for name in ['manifest.json','missing-info-render-report.json','owned-test-template-cleanup.json','worker-lifecycle.json']:
        keep(a.source/name,'provenance/native-'+name)
    for path in a.source.glob('word-preview-*.json'):keep(path,'provenance/'+path.name)
    keep(a.trial/'report.json','provenance/trial-report.json')
    for name in ['manifest.json','structure-audit.json','translation-audit.json']:keep(a.candidate/name,'provenance/candidate-'+name)
    for name in ['generate_mixed_budget_fixtures.py','mixed_budget_trial.py','rehearse_mixed_budget.py','collect_mixed_budget_trials.py',
                 'run_missing_info.py','render.py','artifact_utils.py','rehearse_profile_pdf.py','rehearse_profile_pagination.py',
                 'check_short_resources_outputs.py','check_budget_spacing_outputs.py','check_word_short_budget_outputs.py']:
        keep(ROOT/'scripts'/name,'reproduce/'+name)
    for name in ['src/budget-reading.html.j2','src/pdf/short-resource-rows.html.j2','src/pdf/short-resources.html.j2','scripts/short_resource_rows_contract.py']:
        keep(a.english/name,'reproduce/english/'+name)
    keep(ROOT/'pipeline.yml','reproduce/pipeline.yml')
    fixtures=ROOT/'experiments/mixed-budget/fixtures';keep(fixtures/'provenance.json','fixtures/provenance.json')
    for locale in ['en','zh-Hant']:
        for case in ['mixed-long-last','mixed-gaps']:
            for suffix in ['.json','.events.json']:keep(fixtures/locale/(case+suffix),'fixtures/'+locale+'/'+case+suffix)
    diagnostics=[]
    for row in report['rows']:
        stem=row['stem'];native=a.source/'renders'/stem
        for fmt,digest in row['source_sha256'].items():
            path=native.with_suffix('.'+fmt);assert sha(path)==digest
            if fmt=='html':questions(path,'native/question-content/'+path.name)
            else:keep(path,'native/'+path.name)
            receipt=path.with_suffix(path.suffix+'.fixture.json');keep(receipt,'native/'+receipt.name)
        preview=a.source/'word-preview'/(stem+'.pdf');assert sha(preview)==row['word_preview_sha256'];keep(preview,'word-preview/'+preview.name)
        for name,digest in row['trial_sha256'].items():
            path=a.trial/name;assert sha(path)==digest;keep(path,'trials/'+name)
            questions(path.with_suffix('.html'),'trials/question-content/'+path.with_suffix('.html').name)
        paths=[native.with_suffix('.pdf'),*[a.trial/(stem+'-'+mode+'.pdf') for mode in ['baseline','keep-short-rows']]]
        diagnostics.append(dict(stem=stem,native_pages=row['native_pdf_pages'],offline_pages=row['pdf_pages'],
            native_fonts=fonts(paths[0]),baseline_fonts=fonts(paths[1]),trial_fonts=fonts(paths[2]),
            native_baseline_geometry_identical=row['native_baseline_geometry_identical']))
        if row['case']=='mixed-long-last' and (row['language']=='english' and row['profile']=='review' or row['language']=='chinese' and row['profile']=='submission'):
            for phase,path in [('native',paths[0]),('baseline',paths[1]),('trial',paths[2])]:
                for page in ([8,9] if row['language']=='english' else [7,8]):
                    target=a.output/'visual'/(stem+'-'+phase+'-p'+str(page));target.parent.mkdir(exist_ok=True)
                    subprocess.run(['pdftoppm','-f',str(page),'-l',str(page),'-scale-to','1500','-singlefile','-png',str(path),str(target)],check=True,capture_output=True)
    (a.output/'provenance/font-baseline-diagnostics.json').write_text(json.dumps(dict(rows=diagnostics),ensure_ascii=False,indent=2)+'\n')
    (a.output/'inventory.json').write_text(json.dumps(dict(template_version='0.3.42',template_modified=False,native_candidate_export=False,
        release_acceptance=False,microsoft_word_acceptance=False,native_baseline_sets=8,pdf_trial_pairs=8,
        all_native_baselines_reproduced=report['all_native_baselines_reproduced'],collector_sha256=sha(Path(__file__))),indent=2)+'\n')
    print(json.dumps(dict(native_baseline_sets=8,pdf_trial_pairs=8,all_native_baselines_reproduced=report['all_native_baselines_reproduced'])))


if __name__=='__main__':main()
