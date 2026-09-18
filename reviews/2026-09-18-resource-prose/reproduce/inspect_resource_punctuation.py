"""Separate real whitespace from source-font punctuation positioning on frozen Q15."""
import argparse
import json
from pathlib import Path
import re
import subprocess
from bs4 import BeautifulSoup
from docx import Document
from lxml import etree as E
from artifact_utils import sha
from rehearse_profile_pdf import IMAGE
from rehearse_resource_prose import SENTENCES

RUNNER='''import json
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
f=TTFont('/font/source.ttf');cmap=f.getBestCmap();glyphs=f.getGlyphSet();rows=[]
for c in '。，、？：培訓':
 g=cmap[ord(c)];pen=BoundsPen(glyphs);glyphs[g].draw(pen)
 rows.append(dict(character=c,codepoint=f'U+{ord(c):04X}',advance=f['hmtx'].metrics[g][0],ink_bounds=pen.bounds))
print(json.dumps(dict(units_per_em=f['head'].unitsPerEm,default_axes={a.axisTag:a.defaultValue for a in f['fvar'].axes},glyphs=rows)))
'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source','font','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();assert not a.output.exists()
    report=dict(completed=False,template_modified=False,release_acceptance=False,rows=[],
        checker_sha256=sha(Path(__file__)),font_sha256=sha(a.font),worker_image=IMAGE,
        source_font_measurement='Default-axis source glyphs, not a reconstruction of the embedded native PDF outlines',
        reference='https://www.w3.org/International/clreq/#positioning_of_punctuation_marks')
    try:
        metrics=subprocess.check_output(['docker','run','--rm','--network','none','-v',str(a.font.resolve())+':/font/source.ttf:ro','--entrypoint','python',IMAGE,'-c',RUNNER],text=True)
        report['source_font_metrics']=json.loads(metrics)
        first,last=SENTENCES['chinese'];expected=[first,last[1]]
        for profile in ('review','submission'):
            stem='profile-partial-'+profile+'-chinese'
            paths={fmt:a.source/'renders'/(stem+'.'+fmt) for fmt in ('html','pdf','docx')}
            soup=BeautifulSoup(paths['html'].read_text(),'html.parser')
            html=[p.get_text() for p in soup.select('#q-required-resources .answer > p') if p.get_text() in expected]
            word=[p.text for p in Document(paths['docx']).paragraphs if p.text in expected]
            extracted=subprocess.check_output(['pdftotext','-layout',str(paths['pdf']),'-'],text=True)
            pdf=[line.strip() for line in extracted.splitlines() if line.strip() in expected]
            assert html==word==pdf==expected
            assert not any(re.search(r'[\s\u3000]+[。？，、：；！]',value) for value in expected)
            xml=E.fromstring(subprocess.check_output(['pdftohtml','-xml','-stdout','-hidden',str(paths['pdf'])]))
            runs=[];families={}
            for f in xml.findall('.//fontspec'):
                if f.get('id') in families:assert families[f.get('id')]==f.get('family')
                families[f.get('id')]=f.get('family')
            for page in xml.findall('page'):
                for node in page.findall('text'):
                    if ''.join(node.itertext()) in expected:
                        family=families[node.get('font')]
                        assert 'Pilot-CJK' in family
                        runs.append(dict(text=''.join(node.itertext()),page=int(page.get('number')),font=family))
            assert len(runs)==2
            report['rows'].append(dict(profile=profile,html_word_pdf_text=expected,
                real_whitespace_before_punctuation=False,pdf_font_runs=runs,
                input_sha256={fmt:sha(path) for fmt,path in paths.items()}))
        report['completed']=True
    except Exception as error:report['failure']=repr(error);raise
    finally:a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(completed=True,profiles=len(report['rows']))))


if __name__=='__main__':main()
