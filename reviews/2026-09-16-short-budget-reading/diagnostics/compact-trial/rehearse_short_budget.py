"""Diagnostic column/prompt experiments on frozen HTML, not native acceptance."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from artifact_utils import sha

SELECTOR='html body #q-required-resources .resource-table:has(tbody > tr > td:nth-child(2) > .data-gap)'
VARIANTS={'baseline':''}
for name,widths in [('width-40-29-31',(40,29,31)),('width-49-25-26',(49,25,26)),('width-52-22-26',(52,22,26))]:
    VARIANTS[name]='\n'.join(SELECTOR+' col.resource-'+column+' { width: '+str(width)+'%; }' for column,width in zip(['purpose','budget','funding'],widths))
VARIANTS['unboxed-gap']=SELECTOR+' > tbody > tr > td:nth-child(2) > .data-gap { border: none; padding: 0; background: transparent; }'
VARIANTS['width-49-compact']=VARIANTS['width-49-25-26']+'\n'+SELECTOR+' th, '+SELECTOR+' td { padding-top: .25em; padding-bottom: .25em; }\n'+SELECTOR+' p { margin-bottom: .2em; }'
RUNNER='''import json,sys,re
from weasyprint import HTML,__version__
p=json.load(sys.stdin); rows=[]
for row in p['cases']:
    source=row['html'];assert source.count('</style>')==1
    doc=HTML(string=source.replace('</style>',row['css']+'</style>')).render()
    doc.write_pdf('/out/'+row['name']+'.pdf');gaps=[];tables=[]
    for number,page in enumerate(doc.pages,1):
        for b in page._page_box.descendants():
            if type(b).__name__=='BlockBox' and b.element.get('data-fact-id')=='resource-amount':
                lines=[''.join(n.text for n in line.descendants() if type(n).__name__=='TextBox') for line in b.children if type(line).__name__=='LineBox']
                gaps.append({'page':number,'lines':lines,'width':b.width,'height':b.height})
            if type(b).__name__=='TableBox' and 'resource-table' in b.element.get('class','').split():tables.append({'page':number,'y':b.position_y,'height':b.height})
    texts=[''.join(b.text for b in page._page_box.descendants() if type(b).__name__=='TextBox') for page in doc.pages]
    rows.append({'name':row['name'],'pages':len(doc.pages),'gaps':gaps,'tables':tables,'texts':texts})
print(json.dumps({'weasyprint':__version__,'rows':rows}))
'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['source','english','out']:p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();sys.path.insert(0,str(a.english.resolve()/'scripts'));from probe_budget_word import IMAGE
    a.out.mkdir(parents=True,exist_ok=False);a.out.chmod(0o777);cases=[];sources={}
    for lang in ['english','chinese']:
        source=a.source/f'partial-{lang}.html';sources[lang]=sha(source)
        for name,css in VARIANTS.items():cases.append({'name':name+'-'+lang,'css':css,'html':source.read_text()})
    result=json.loads(subprocess.check_output(['docker','run','--rm','--network','none','-i','-v',str(a.out.resolve())+':/out','--entrypoint','python',IMAGE,'-c',RUNNER],input=json.dumps({'cases':cases}).encode()))
    result.update(release_acceptance=False,sources=sources,variants=VARIANTS,worker_image=IMAGE,checker_sha256=sha(Path(__file__)))
    (a.out/'report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps([{k:v for k,v in r.items() if k!='texts'} for r in result['rows']],ensure_ascii=False))


if __name__=='__main__':main()
