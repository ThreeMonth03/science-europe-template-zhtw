"""Capture actual Q3 start/continuation pages through Q4; no crops or image edits."""
import argparse
import json
from pathlib import Path
import subprocess
from bs4 import BeautifulSoup
from artifact_utils import sha
from check_narrative_outputs import compact
from check_metadata_followup_outputs import CASES


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for n in ['build','prior']: p.add_argument('--'+n,type=Path,required=True)
    a = p.parse_args(); out = a.build/'visual'; out.mkdir(exist_ok=True); rows = []
    for label, root in [('before',a.prior),('after',a.build)]:
        for case in CASES[:-2]:
            for language in ['english','chinese']:
                stem = case+'-'+language
                soup = BeautifulSoup((root/'renders'/(stem+'.html')).read_text(),'html.parser')
                headings = [compact(soup.select_one('#'+n+' h3').get_text()) for n in ['q-docs-metadata','q-quality-control']]
                for kind in ['pdf','word']:
                    pdf = root/('renders' if kind=='pdf' else 'word-preview')/(stem+'.pdf')
                    pages = [compact(t) for t in subprocess.check_output(['pdftotext','-layout',str(pdf),'-'],text=True).split('\f')[:-1]]
                    hits = [[i for i,t in enumerate(pages,1) if h in t] for h in headings]
                    assert all(len(v)==1 for v in hits)
                    for number in range(hits[0][0],hits[1][0]+1):
                        target = out/(label+'-'+kind+'-'+stem+'-page'+str(number))
                        assert not target.with_suffix('.png').exists()
                        subprocess.run(['pdftoppm','-f',str(number),'-l',str(number),'-scale-to','1400',
                                        '-png','-singlefile',str(pdf),str(target)],check=True,capture_output=True)
                        rows.append(dict(source=str(pdf),source_sha256=sha(pdf),page=number,total_pages=len(pages),
                                         image=target.name+'.png',image_sha256=sha(target.with_suffix('.png'))))
    (out/'page-index.json').write_text(json.dumps(rows,indent=2)+'\n')
    print(json.dumps({'captured_pages':len(rows)}))


if __name__=='__main__': main()
