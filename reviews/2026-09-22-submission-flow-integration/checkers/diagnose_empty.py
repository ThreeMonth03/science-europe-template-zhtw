"""Separate next-step diagnostic, not an integrated template or acceptance gate."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
import check
os.umask(0o077)
ROOT=Path(__file__).resolve().parent
IMAGE='sha256:6d3cbcab3294e760a4d92e27bec72d4fb23a0adb2cc1734d981478688741ab11'
WORKER=r'''
import json
from pathlib import Path
from weasyprint import HTML
root=Path('/audit');out=root/'next-empty-diagnostic';out.mkdir()
heading='html body #dmp-content > .dmp-section > .question.compact-empty-question > h3 { page-break-after:auto !important; }'
selector='html body #dmp-content:has(> .dmp-section > .compact-empty-question):not(:has(> .dmp-section > .question:not(.compact-empty-question))) > .dmp-section'
spacing=selector+' { margin-bottom:.8em; } '+selector+' > h2 { margin-top:.9em; margin-bottom:.4em; }'
rows=[]
for locale in ['en','zh-Hant']:
 source=(root/'candidate/renders'/('EMPTY-'+locale+'-submission')/'pdf-entry.html').read_text()
 assert source.count('</head>')==1
 for name,css in [('control',''),('empty-heading-break',heading),('empty-section-spacing',spacing),('combined',heading+spacing)]:
  document=HTML(string=source.replace('</head>','<style>'+css+'</style></head>')).render()
  boxes=[b for page in document.pages for b in page._page_box.descendants() if type(b).__name__=='BlockBox' and b.element is not None and b.element.tag in ['h2','h3']]
  titles=[b for b in boxes if b.element.tag=='h3'];assert len(titles)==15
  path=out/(locale+'-'+name+'.pdf');document.write_pdf(path)
  rows.append(dict(locale=locale,variant=name,css=css,pdf=path.name,pages=len(document.pages),
    heading_break_after=[str(b.style['break_after']) for b in titles],question_heading_count=len(titles)))
(out/'engine.json').write_text(json.dumps(dict(rows=rows),indent=2)+'\n')
'''
def main():
    command=['docker','run','--rm','--network','none','--log-driver','none','--cap-drop','ALL',
        '--security-opt','no-new-privileges','--user','1000:1000',
        '-e','PYTHONPATH=/home/user/.local/lib/python3.13/site-packages','-e','XDG_CACHE_HOME=/tmp/private-cache',
        '--entrypoint','python','-v',str(ROOT)+':/audit',IMAGE,'-c',WORKER]
    subprocess.run(command,check=True,timeout=300)
    directory=ROOT/'next-empty-diagnostic';result=json.loads((directory/'engine.json').read_text())
    for locale in ['en','zh-Hant']:
        actual,_=check.pdf(ROOT/'candidate/renders'/('EMPTY-'+locale+'-submission')/'document.pdf')
        control,text=check.pdf(directory/(locale+'-control.pdf'))
        assert actual==control,'Diagnostic control does not reproduce actual package geometry'
        for row in result['rows']:
            if row['locale']!=locale:continue
            _,parts=check.pdf(directory/row['pdf'])
            # Strip only each exact generated page counter from the end.
            def without_page_counters(pages):
                import re
                return ''.join(re.sub(r'\d+/\d+$','',p) for p in pages)
            assert without_page_counters(text)==without_page_counters(parts),'Diagnostic changed document text'
            row['all_original_text_retained']=True
            row['control_geometry_matches_actual_package']=True
    result.update(diagnostic_only=True,source_integrated=False,release_acceptance=False,
        mixed_or_long_document_cases_checked=False,native_ms_word=False,worker_image=IMAGE,
        checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    with (directory/'checks.json').open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps([dict(locale=r['locale'],variant=r['variant'],pages=r['pages'],heading_break_after=sorted(set(r['heading_break_after']))) for r in result['rows']]))
if __name__=='__main__':main()
