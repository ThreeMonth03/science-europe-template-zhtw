"""Additional read-only pixel comparison of unchanged control body pages."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from bs4 import BeautifulSoup
from lxml import etree

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--build',type=Path,required=True)
parser.add_argument('--prior',type=Path,required=True)
args=parser.parse_args()
ROOT=args.build
BEFORE=args.prior
TARGET=ROOT/'unchanged-control-pixels.json'
assert not TARGET.exists()
rows=[]
for case in ['empty','negative']:
    for language in ['english','chinese']:
        stem=case+'-'+language
        heading=''.join(BeautifulSoup((ROOT/'renders'/(stem+'.html')).read_text(),'html.parser').select_one('.question h3').get_text().split())
        for kind in ['renders','word-preview']:
            files=[root/kind/(stem+'.pdf') for root in [BEFORE,ROOT]]
            starts=[]
            for f in files:
                bbox=etree.fromstring(subprocess.check_output(['pdftotext','-bbox-layout',str(f),'-']))
                pages=[''.join(''.join(p.itertext()).split()) for p in bbox.findall('.//{*}page')]
                assert sum(t.count(heading) for t in pages)==1
                starts.append(next(i+1 for i,t in enumerate(pages) if heading in t))
            assert starts[0]==starts[1]
            with tempfile.TemporaryDirectory(prefix='se-control-pixels-') as folder:
                hashes=[]
                for index,f in enumerate(files):
                    prefix=Path(folder)/str(index)
                    subprocess.run(['pdftoppm','-f',str(starts[index]),'-r','100','-png',str(f),str(prefix)],check=True)
                    images=sorted(Path(folder).glob(str(index)+'-*.png'))
                    assert images
                    hashes.append([hashlib.sha256(p.read_bytes()).hexdigest() for p in images])
                assert hashes[0]==hashes[1],(stem,kind)
                rows.append({'case':case,'language':language,'format':kind,'first_body_page':starts[0],
                    'identical_body_pages':len(hashes[1]),'png_sha256':hashes[1],
                    'before_pdf_sha256':hashlib.sha256(files[0].read_bytes()).hexdigest(),
                    'after_pdf_sha256':hashlib.sha256(files[1].read_bytes()).hexdigest()})
report={'passed':True,'release_acceptance':False,'checker_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'rows':rows,'identical_body_pages':sum(r['identical_body_pages'] for r in rows),
        'limits':['Control fixtures only; cover excluded based on unique first-question heading','100 dpi raster equality, not Microsoft Word execution']}
TARGET.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'passed':True,'documents':len(rows),'identical_body_pages':report['identical_body_pages']}))
