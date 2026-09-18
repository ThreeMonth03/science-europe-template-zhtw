"""Freeze diagnostic prose trials and punctuation evidence without publishing a DT."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
from bs4 import BeautifulSoup
from artifact_utils import sha
from rehearse_resource_prose import SENTENCES
from rehearse_profile_pdf import snapshot
from check_budget_spacing_outputs import line_box_overlaps
from check_short_budget_outputs import prompt_lines
from collect_profile_pagination import contact
from rehearse_profile_pagination import locate

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('trial','inspection','source','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();assert not a.output.exists()
    report=json.loads((a.trial/'report.json').read_text());inspection=json.loads(a.inspection.read_text())
    assert report['completed'] and len(report['rows'])==8 and inspection['completed']
    assert report['checker_sha256']==sha(ROOT/'scripts/rehearse_resource_prose.py')
    assert inspection['checker_sha256']==sha(ROOT/'scripts/inspect_resource_punctuation.py')
    a.output.mkdir(parents=True)
    def keep(source,name):
        target=a.output/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    keep(a.trial/'report.json','provenance/trial-report.json');keep(a.inspection,'provenance/punctuation.json')
    for name in ('manifest.json','short-resources-report.json'):keep(a.source/name,'provenance/native-'+name)
    for name in ('rehearse_resource_prose.py','inspect_resource_punctuation.py','collect_resource_prose_trials.py'):
        keep(ROOT/'scripts'/name,'reproduce/'+name)
    keep(ROOT/'pipeline.yml','reproduce/pipeline.yml')
    metrics=[]
    for row in report['rows']:
        stem=row['stem']
        for name,digest in row['artifact_sha256'].items():
            assert sha(a.trial/name)==digest;keep(a.trial/name,'trials/'+name)
        for kind in ('html','pdf','docx'):
            source=a.source/'renders'/(stem+'.'+kind);assert sha(source)==row['source_'+kind+'_sha256']
            if kind=='html':
                soup=BeautifulSoup(source.read_text(),'html.parser');q=soup.select('.question');assert len(q)==15
                path=a.output/'native-question-content'/source.name;path.parent.mkdir(exist_ok=True)
                path.write_text('<!-- Native HTML SHA256: '+sha(source)+' -->\n'+'\n'.join(str(n) for n in q)+'\n')
            else:keep(source,'native-baseline/'+source.name)
            keep(source.with_suffix(source.suffix+'.fixture.json'),'native-baseline/'+source.name+'.fixture.json')
        keep(a.source/'word-preview'/(stem+'.pdf'),'native-word-preview/'+stem+'.pdf')
        for mode in ('baseline','joined'):
            source=a.trial/(stem+'-'+mode+'.html');soup=BeautifulSoup(source.read_text(),'html.parser')
            path=a.output/'trial-question-content'/source.name;path.parent.mkdir(exist_ok=True)
            path.write_text('<!-- Diagnostic HTML SHA256: '+sha(source)+' -->\n'+'\n'.join(str(q) for q in soup.select('.question'))+'\n')
        before,after=[a.trial/'word-preview'/(stem+'-'+mode+'.pdf') for mode in ('baseline','joined')]
        assert line_box_overlaps(snapshot(before)[1])==line_box_overlaps(snapshot(after)[1]),'Changed Word line-box overlap warnings'
        if not row['selected']:continue
        first,last=SENTENCES[row['language']];last=last[1]
        q=BeautifulSoup((a.source/'renders'/(stem+'.html')).read_text(),'html.parser').select_one('#q-required-resources')
        anchors=[q.h3.get_text(),q.h4.get_text()]
        for kind,folder in [('pdf',a.trial),('word',a.trial/'word-preview')]:
            old,new=[folder/(stem+'-'+mode+'.pdf') for mode in ('baseline','joined')]
            before=[prompt_lines(old,value) for value in (first,last)]
            after=prompt_lines(new,first+last)
            metrics.append(dict(stem=stem,kind=kind,before=before,after=after,
                before_line_count=sum(r['line_count'] for r in before),after_line_count=after['line_count'],
                before_q15_heading_budget_pages=locate(old,anchors)[1],after_q15_heading_budget_pages=locate(new,anchors)[1],
                before_pdf_sha256=sha(old),after_pdf_sha256=sha(new)))
            contact(new,a.output/'visual'/(stem+'-'+kind+'.png'),kind+' '+stem+' joined')
            if row['language']=='chinese' and row['profile']=='submission':
                for mode,pdf,page in [('before',old,before[0]['page']),('after',new,after['page'])]:
                    subprocess.run(['pdftoppm','-f',str(page),'-l',str(page),'-scale-to','1600','-singlefile','-png',str(pdf),str(a.output/'visual'/(kind+'-'+mode+'-chinese-submission-p'+str(page)))],check=True,capture_output=True)
    (a.output/'provenance/line-metrics.json').write_text(json.dumps(dict(rows=metrics,release_acceptance=False),indent=2)+'\n')
    print(json.dumps(dict(pairs=8,selected=4,metrics=metrics)))


if __name__=='__main__':main()
