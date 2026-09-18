"""PDF-only same-engine A/B rehearsal of a short Q15 keep, never a release rule."""
import argparse
import base64
from collections import Counter
import json
from pathlib import Path
import subprocess
from bs4 import BeautifulSoup
from lxml import etree as E
from artifact_utils import sha
from diagnose_word_import_layout import clean_pages, compact
from check_budget_spacing_outputs import line_box_overlaps

IMAGE = 'datastewardshipwizard/document-worker@sha256:5e5c5e1e436feb49fc4cbcd62c2e0ab2785db2141b0fe40d2926906bcfeaebfc'
RUNNER = '''import base64,json,sys,subprocess
from pathlib import Path
p=json.load(sys.stdin)
for row in p['rows']:
 source=Path('/input/'+row['stem']+'.html').read_text()
 for mode,css in [('baseline',''),('keep-short-q15','html body #q-required-resources { break-inside: avoid; }')]:
  pdf=subprocess.check_output([sys.executable,'-c',"import sys; from weasyprint import HTML; sys.stdout.buffer.write(HTML(string=sys.stdin.read()).write_pdf())"],input=source.replace('</style>',css+'</style>',1).encode())
  print(json.dumps(dict(stem=row['stem'],trial=mode,pdf=base64.b64encode(pdf).decode())),flush=True)
'''


def snapshot(pdf):
    raw = subprocess.check_output(['pdftotext', '-raw', str(pdf), '-'], text=True)
    bbox = subprocess.check_output(['pdftotext', '-bbox-layout', str(pdf), '-'])
    return clean_pages(raw, bbox), bbox


def prefix_geometry(bbox):
    """Exact word boxes before the unique Q15 marker, excluding proven footers."""
    pages=E.fromstring(bbox).findall('.//{*}page')
    result=[]; markers=0
    for index,page in enumerate(pages,1):
        footer_words=set()
        for line in page.findall('.//{*}line'):
            words=line.findall('{*}word')
            if ''.join(w.text or '' for w in words)==f'{index}/{len(pages)}' and float(line.get('yMin'))>float(page.get('height'))*.9:
                assert not footer_words,'Multiple footer candidates'
                footer_words.update(words)
        assert footer_words,'Missing proven footer'
        for word in page.findall('.//{*}word'):
            if word in footer_words: continue
            if word.text=='15.': markers+=1
            if markers==0: result.append((index,dict(word.attrib),word.text))
    assert markers==1,'Ambiguous Q15 anchor'
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=Path('outputs/runtime-tables-stkosfij/renders'))
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    assert not a.output.exists(); a.output.mkdir(parents=True)
    rows=[dict(stem='profile-partial-'+mode+'-'+lang,language=lang,mode=mode) for lang in ('english','chinese') for mode in ('review','submission')]
    report=dict(completed=False,release_acceptance=False,native_export=False,
        worker_image=IMAGE,rows=[],checker_sha256=sha(Path(__file__)),
        limits=['Only the existing short synthetic Q15; an unbounded keep rule is not suitable for release',
                'Native-baseline reproduction is recorded separately, never assumed from a successful paired comparison'])
    try:
        result=subprocess.run(['docker','run','--rm','--network','none','-i','--entrypoint','python',
            '-v',str(a.source.resolve())+':/input:ro',IMAGE,'-c',RUNNER],
            input=json.dumps(dict(rows=rows)).encode(),capture_output=True,check=True)
        for line in result.stdout.splitlines():
            artifact=json.loads(line)
            assert artifact['stem'] in {r['stem'] for r in rows}
            assert artifact['trial'] in {'baseline','keep-short-q15'}
            (a.output/(artifact['stem']+'-'+artifact['trial']+'.pdf')).write_bytes(base64.b64decode(artifact['pdf'],validate=True))
        for row in rows:
            stem=row['stem'];soup=BeautifulSoup((a.source/(stem+'.html')).read_text(),'html.parser')
            anchors=[soup.select_one('#q-required-resources h3').get_text(),soup.select_one('.resource-table tbody').get_text()]
            original,bbox=snapshot(a.source/(stem+'.pdf'))
            base,base_bbox=snapshot(a.output/(stem+'-baseline.pdf'))
            native_match=bbox==base_bbox
            base_prefix=prefix_geometry(base_bbox)
            for mode in ('baseline','keep-short-q15'):
                pdf=a.output/(stem+'-'+mode+'.pdf');pages,new_bbox=snapshot(pdf)
                assert prefix_geometry(new_bbox)==base_prefix,'Non-Q15 geometry changed in the paired rehearsal'
                assert line_box_overlaps(new_bbox)==line_box_overlaps(base_bbox),'New paired line-box overlaps'
                markers={'•','◦','\uf0b7','\uf0a1'}
                assert not markers.intersection(soup.get_text()),'Literal bullets need an independent oracle'
                assert Counter(c for c in ''.join(original) if c in markers)==Counter(c for c in ''.join(pages) if c in markers)
                assert ''.join(c for c in ''.join(original) if c not in markers)==''.join(c for c in ''.join(pages) if c not in markers),'Text changed'
                positions=[[i for i,page in enumerate(pages,1) if compact(v) in page] for v in anchors]
                assert all(len(v)==1 for v in positions),positions
                report['rows'].append(dict(**row,trial=mode,pages=len(pages),q15_heading_table_pages=positions,
                    together=positions[0]==positions[1],pdf_sha256=sha(pdf),source_html_sha256=sha(a.source/(stem+'.html'))))
                report['rows'][-1].update(native_baseline_geometry_identical=native_match,
                    paired_prefix_geometry_identical=True,source_pdf_sha256=sha(a.source/(stem+'.pdf')),
                    line_box_overlaps=line_box_overlaps(new_bbox))
        report['completed']=True
        report['all_native_baselines_reproduced']=all(r['native_baseline_geometry_identical'] for r in report['rows'])
    except Exception as error:
        report['failure']=repr(error)
        raise
    finally:(a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report['rows']))


if __name__=='__main__':main()
