"""Compare bounded empty-Q15 spacing in frozen native HTML (not DSW evidence)."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from artifact_utils import sha

FACTS = ('specialist-expertise', 'hardware-software', 'repository-charges', 'resources-costing')
SELECTOR = 'html body #q-required-resources > .answer' + ''.join(
    ':has(> p.data-gap[data-fact-id="'+fact+'"][data-status="missing"]:'+
    ('first-child' if i == 1 else f'nth-child({i})')+(':last-child' if i == 4 else '')+')'
    for i, fact in enumerate(FACTS, 1))
CSS = f'''
/* Exactly four fixed Q15 gaps share one panel; each fact keeps its own paragraph. */
{SELECTOR} {{ border: 1px solid #8a6d3b; border-left-width: 3px; background: #fff8e8; padding: .45em .65em; }}
{SELECTOR} > p.data-gap {{ border: 0; padding: 0; margin: 0 0 .35em; background: transparent; }}
{SELECTOR} > p.data-gap:last-child {{ margin-bottom: 0; }}
'''
RUNNER = '''import json,sys,re
from pathlib import Path
from weasyprint import HTML,__version__
p=json.load(sys.stdin); rows=[]
for row in p['cases']:
    source=row['html']; assert source.count('</style>')==1
    doc=HTML(string=source.replace('</style>',row['css']+'</style>')).render()
    texts=[''.join(b.text for b in page._page_box.descendants() if type(b).__name__=='TextBox') for page in doc.pages]
    doc.write_pdf('/out/'+row['name']+'.pdf')
    rows.append({'name':row['name'],'pages':len(doc.pages),'texts':texts})
print(json.dumps({'weasyprint':__version__,'rows':rows}))
'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--english',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    sys.path.insert(0,str(a.english.resolve()/'scripts'));from probe_budget_word import IMAGE
    a.out.mkdir(parents=True,exist_ok=False);a.out.chmod(0o777)
    cases=[];sources={}
    for lang in ['english','chinese']:
        f=a.source/f'empty-{lang}.html';sources[lang]=sha(f)
        for variant,css in [('baseline',''),('shared-panel',CSS)]:
            cases.append({'name':variant+'-'+lang,'html':f.read_text(),'css':css})
    result=json.loads(subprocess.check_output(['docker','run','--rm','--network','none','-i','-v',str(a.out.resolve())+':/out','--entrypoint','python',IMAGE,'-c',RUNNER],input=json.dumps({'cases':cases}).encode()))
    result.update(release_acceptance=False,sources=sources,css=CSS,worker_image=IMAGE,checker_sha256=sha(Path(__file__)))
    (a.out/'report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps([{k:v for k,v in r.items() if k!='texts'} for r in result['rows']]))


if __name__=='__main__':main()
