"""Offline mixed-row A/B on native 0.3.42 inputs; no template or Word modification."""
import argparse
import base64
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys
from bs4 import BeautifulSoup
from docx import Document
from artifact_utils import sha
from mixed_budget_trial import pdf_baseline,trial,matrix
from rehearse_profile_pdf import IMAGE,snapshot,prefix_geometry
from rehearse_profile_pagination import geometry
from check_short_resources_outputs import fonts
from check_budget_spacing_outputs import line_box_overlaps
from check_word_short_budget_outputs import verify_preview_paragraphs

MARKERS={'•','◦','\uf0b7','\uf0a1'}
compact=lambda value:''.join(value.split())


def content(pages,source):
    """Fixture-specific oracle for eight ordinary rows followed by one long row."""
    soup=BeautifulSoup(source,'html.parser');assert not MARKERS.intersection(soup.get_text())
    tables=soup.select('#q-required-resources .resource-table');assert len(tables)==2
    ordinary,long=tables;assert long.get('class')==['resource-table','pdf-resource-reading']
    rows=ordinary.tbody.find_all('tr',recursive=False);assert len(rows)==8
    header=compact(ordinary.thead.get_text());assert header==compact(long.thead.tr.get_text())
    identity=compact(long.thead.find_all('tr',recursive=False)[1].get_text())
    assert all(header not in compact(n.get_text()) and identity not in compact(n.get_text()) for n in soup.select('.answer-detail'))
    values=[];seen_header=False;seen_long=False;repeated=[]
    for number,page in enumerate(pages,1):
        value=''.join(c for c in page if c not in MARKERS)
        if value.startswith(header+identity):
            if seen_long:value=value[len(header+identity):];repeated.append(dict(page=number,kind='long-identity'))
        elif value.startswith(header) and seen_header:
            value=value[len(header):];repeated.append(dict(page=number,kind='columns'))
        seen_header |= header in value;seen_long |= header+identity in value
        values.append(value)
    whole=''.join(values[1:]);location=[i for i,v in enumerate(values[1:],2) for _ in v]
    titles=[compact(r.td.p.get_text()) for r in rows]
    long_title=compact(long.thead.find_all('tr',recursive=False)[1].td.get_text());titles.append(long_title)
    assert len(set(titles))==9 and all(whole.count(t)==1 for t in titles),'Ambiguous row identity'
    positions=[whole.index(t) for t in titles];assert positions==sorted(positions)
    canonical=whole[:positions[0]];locations=[]
    for n,row in enumerate(rows):
        start=positions[n];stop=positions[n+1]
        value=whole[start:stop]
        if n==7:
            assert value.endswith(header);value=value[:-len(header)];stop-=len(header)
        tokens=[compact(p.get_text()) for p in row.find_all('p')]
        assert len(set(tokens))==len(tokens) and all(tokens)
        pending=list(tokens);found=[]
        while value:
            hits=[t for t in pending if value.startswith(t)]
            assert len(hits)==1,('Missing, changed, repeated or interleaved cell paragraph',n+1,value[:120])
            token=hits[0];pending.remove(token);value=value[len(token):];found.append(token)
        assert not pending
        purpose=[compact(p.get_text()) for p in row.td.find_all('p')]
        assert [t for t in found if t in purpose]==purpose,'Purpose order changed'
        canonical+=''.join(tokens)
        locations.append(dict(index=n+1,pages=sorted(set(location[start:stop]))))
    long_text=compact(long.get_text())[len(header):]
    assert whole[positions[8]:]==long_text,'Long row text or continuation identity changed'
    canonical+=header+long_text
    return dict(canonical=canonical,rows=locations,repeated_headers=repeated,
                long_pages=sorted(set(location[positions[8]:])))


RUNNER=r'''import base64,json,sys,subprocess
from pathlib import Path
p=json.load(sys.stdin)
code="""import base64,json,sys
from weasyprint import HTML
p=json.load(sys.stdin);h=HTML(string=p['source']);doc=h.render();ordinary={};long={}
for i,page in enumerate(doc.pages,1):
 for b in page._page_box.descendants():
  if type(b).__name__=='TableRowBox' and b.element.get('data-item-id'):
   ordinary.setdefault(b.element.get('data-item-id'),[]).append(dict(page=i,height=round(b.height,4)))
  if type(b).__name__=='TableBox' and b.element.get('data-item-id'):
   long.setdefault(b.element.get('data-item-id'),[]).append(i)
print(json.dumps(dict(pdf=base64.b64encode(doc.write_pdf()).decode(),rows=ordinary,long_tables=long)))
"""
for name in p['names']:
 source=Path('/input/'+name+'.html').read_text()
 value=json.loads(subprocess.check_output([sys.executable,'-c',code],input=json.dumps(dict(source=source)).encode()))
 print(json.dumps(dict(name=name,**value)),flush=True)
'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['source','english','output']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--cases',nargs='+',default=['mixed-long-last','mixed-gaps'])
    a=p.parse_args();sys.path.insert(0,str(a.english.resolve()/'scripts'));assert not a.output.exists();a.output.mkdir(parents=True)
    report=dict(completed=False,template_modified=False,native_export=False,word_modified=False,release_acceptance=False,
        microsoft_word_acceptance=False,source_template_version='0.3.42',worker_image=IMAGE,checker_sha256=sha(Path(__file__)),
        contract_sha256=sha(Path(__file__).with_name('mixed_budget_trial.py')),rows=[],
        limits=['Offline trials are not native candidate exports','Native baseline geometry/font agreement is checked explicitly',
                'Only two public mixed-budget fixtures receive native exports; position/count controls are structural probes',
                'Word is inspected but not modified','No new missing-notice suppression'])
    try:
        report['matrix']=[{k:v for k,v in r.items() if k not in ['before','after']} for r in matrix(a.english)]
        names=[];inputs=[]
        for case in a.cases:
            for profile in ['review','submission']:
                for language in ['english','chinese']:
                    stem='-'.join([case,profile,language]);native=a.source/'renders'/stem
                    original=native.with_suffix('.html').read_text();baseline=pdf_baseline(original,a.english);changed,selected=trial(baseline,a.english)
                    assert len(selected)==8
                    for mode,value in [('baseline',baseline),('keep-short-rows',changed)]:
                        name=stem+'-'+mode;names.append(name);(a.output/(name+'.html')).write_text(value)
                    inputs.append(dict(case=case,profile=profile,language=language,stem=stem,selected=selected))
        process=subprocess.run(['docker','run','--rm','--network','none','-i','-v',str(a.output.resolve())+':/input:ro',
            '--entrypoint','python',IMAGE,'-c',RUNNER],input=json.dumps(dict(names=names)).encode(),capture_output=True)
        report['engine_stderr']=process.stderr.decode();assert process.returncode==0,report['engine_stderr']
        metrics={}
        for line in process.stdout.splitlines():
            value=json.loads(line);name=value.pop('name');assert name in names
            (a.output/(name+'.pdf')).write_bytes(base64.b64decode(value.pop('pdf'),validate=True));metrics[name]=value
        for row in inputs:
            stem=row['stem'];paths=[a.output/(stem+'-'+mode+'.pdf') for mode in ['baseline','keep-short-rows']]
            source=a.source/'renders'/stem;native=source.with_suffix('.pdf');html=(a.output/(stem+'-baseline.html')).read_text()
            pairs=[snapshot(path) for path in paths];native_snapshot=snapshot(native)
            parsed=[content(v[0],html) for v in pairs];assert parsed[0]['canonical']==parsed[1]['canonical']
            native_content=content(native_snapshot[0],html);assert native_content['canonical']==parsed[0]['canonical']
            assert Counter(c for c in ''.join(pairs[0][0]) if c in MARKERS)==Counter(c for c in ''.join(pairs[1][0]) if c in MARKERS)
            assert prefix_geometry(pairs[0][1])==prefix_geometry(pairs[1][1])
            assert fonts(paths[0])==fonts(paths[1]);assert line_box_overlaps(pairs[0][1])==line_box_overlaps(pairs[1][1])
            ms=[metrics[stem+'-'+mode] for mode in ['baseline','keep-short-rows']]
            assert set(ms[0]['long_tables'])==set(ms[1]['long_tables']) and all(len(v)>1 for v in ms[1]['long_tables'].values())
            for identity in row['selected']:
                assert len(ms[1]['rows'][identity])==1 and ms[1]['rows'][identity][0]['height']<400
            preview=a.source/'word-preview'/(stem+'.pdf');doc=Document(source.with_suffix('.docx'))
            soup=BeautifulSoup(source.with_suffix('.html').read_text(),'html.parser')
            checked=verify_preview_paragraphs(doc,preview,soup)
            word_pages=snapshot(preview)[0]
            long_title=compact(soup.select_one('.resource-table tbody').find_all('tr',recursive=False)[8].td.p.get_text())
            purpose_pages=sorted({i for i,page in enumerate(word_pages,1) if 'MIX-LONG-09-PARA-' in page})
            identity_pages=[i for i,page in enumerate(word_pages,1) if long_title in page]
            row.update(pdf_pages=[len(v[0]) for v in pairs],native_pdf_pages=len(native_snapshot[0]),
                native_baseline_geometry_identical=native_snapshot[1]==pairs[0][1],native_baseline_fonts_identical=fonts(native)==fonts(paths[0]),
                prior_rows=parsed[0]['rows'],rows=parsed[1]['rows'],prior_repeated_headers=parsed[0]['repeated_headers'],repeated_headers=parsed[1]['repeated_headers'],
                engine_metrics=ms,word_pages=len(word_pages),word_preview_paragraphs_checked=checked,word_long_purpose_pages=purpose_pages,
                word_long_identity_pages=identity_pages,word_continuation_without_row_name=sorted(set(purpose_pages)-set(identity_pages)),
                source_sha256={fmt:sha(source.with_suffix('.'+fmt)) for fmt in ['html','pdf','docx']},word_preview_sha256=sha(preview),
                trial_sha256={p.name:sha(p) for p in paths},passed_content_checks=True)
            report['rows'].append(row);print(json.dumps(dict(stem=stem,pdf_pages=row['pdf_pages'],word_continuation_without_row_name=row['word_continuation_without_row_name'])),flush=True)
        report['completed']=True
        report['all_native_baselines_reproduced']=all(r['native_baseline_geometry_identical'] and r['native_baseline_fonts_identical'] for r in report['rows'])
        report['all_trial_page_counts_nonincreasing']=all(r['pdf_pages'][1]<=r['pdf_pages'][0] for r in report['rows'])
    except Exception as error:report['failure']=repr(error);raise
    finally:(a.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':main()
