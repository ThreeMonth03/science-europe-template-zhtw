"""Capture actual before/after Q5 context pages, including continuation pages."""
import argparse
import json
from pathlib import Path
import subprocess
from bs4 import BeautifulSoup
from artifact_utils import sha
from check_narrative_outputs import compact
from check_storage_context_outputs import EXTRA


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['build','prior','prior-extra']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();out=a.build/'visual';out.mkdir(exist_ok=True);rows=[]
    for case in ['metadata-partial','metadata-private','metadata-private-text','metadata-complete','storage-sharing']:
        for language in ['english','chinese']:
            stem=case+'-'+language
            for label,root in [('before',a.prior_extra if case in EXTRA else a.prior),('after',a.build)]:
                soup=BeautifulSoup((root/'renders'/(stem+'.html')).read_text(),'html.parser');q=soup.select_one('#q-store-backup')
                labels=[compact(q.h3.get_text()),compact(q.select_one('.storage-detail-limits li:last-child').get_text())]
                for kind in ['pdf','word']:
                    pdf=root/('renders' if kind=='pdf' else 'word-preview')/(stem+'.pdf')
                    pages=[compact(t) for t in subprocess.check_output(['pdftotext','-layout',str(pdf),'-'],text=True).split('\f')[:-1]]
                    hits=[[i for i,t in enumerate(pages,1) if text in t] for text in labels];assert all(len(h)==1 for h in hits)
                    for number in range(hits[0][0],hits[1][0]+1):
                        target=out/(label+'-'+kind+'-'+stem+'-page'+str(number));assert not target.with_suffix('.png').exists()
                        subprocess.run(['pdftoppm','-f',str(number),'-l',str(number),'-scale-to','1400','-png','-singlefile',str(pdf),str(target)],check=True,capture_output=True)
                        rows.append(dict(image=target.name+'.png',image_sha256=sha(target.with_suffix('.png')),pdf_sha256=sha(pdf),page=number,total_pages=len(pages)))
    (out/'page-index.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps({'pages':len(rows)}))


if __name__=='__main__':main()
