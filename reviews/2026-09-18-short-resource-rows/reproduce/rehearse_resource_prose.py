"""Bounded fixed-sentence Q15 rehearsal; never modifies a template or native export."""
import argparse
import base64
import copy
import json
from pathlib import Path
import re
import subprocess
import tempfile
import zipfile

from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from lxml import etree as E
from artifact_utils import sha
from check_short_resources_outputs import fonts,compare_text
from rehearse_profile_pdf import IMAGE,snapshot,prefix_geometry
from rehearse_profile_pagination import W,c14n,text,geometry
from check_budget_spacing_outputs import line_box_overlaps

SENTENCES = {
    'english': ('We do not require any hardware or software in addition to what is usually available in the institute.',
                ('No repository service charges are expected.', 'The selected repositories charge for their services.')),
    'chinese': ('除機構通常提供的資源外，我們不需要其他硬體或軟體。',
                ('預計使用的資料儲存庫不收取服務費。', '預計使用的資料儲存庫會收取服務費。')),
}
HARDWARE = '<p data-requirement-id="SE-6b" data-fact-id="hardware-software" data-status="explicit-no">'
Q15 = '<div id="q-required-resources" class="question" data-requirement-id="SE-6b">'


def join_html(source, language):
    """Two exact adjacent owned paragraphs only; preserve all other source bytes."""
    first, endings = SENTENCES[language]
    soup = BeautifulSoup(source, 'html.parser')
    questions = soup.select('#q-required-resources')
    if len(questions) != 1 or source.count(Q15) != 1:
        return source, False
    answer = questions[0].find('div', class_='answer', recursive=False)
    if answer is None:
        return source, False
    hardware = answer.find_all('p', attrs={'data-fact-id':'hardware-software'}, recursive=False)
    if len(hardware) != 1:
        return source, False
    node = hardware[0]
    attrs = {'data-requirement-id':'SE-6b', 'data-fact-id':'hardware-software', 'data-status':'explicit-no'}
    following = node.find_next_sibling()
    if (node.attrs != attrs or node.decode_contents() != first or following is None
            or following.name != 'p' or following.attrs or following.decode_contents() not in endings):
        return source, False
    last = following.get_text()
    old = HARDWARE + first + '</p>'
    pattern = re.compile(re.escape(old) + r'\s*' + re.escape('<p>'+last+'</p>'))
    matches = list(pattern.finditer(source))
    if len(matches) != 1 or matches[0].start() < source.index(Q15):
        return source, False
    # The second fact remains separately identifiable; no arbitrary text joining.
    joined = (HARDWARE+first+(' ' if language=='english' else '')
              +'<span data-fact-id="repository-charges" data-status="complete">'+last+'</span></p>')
    match=matches[0]
    result=source[:match.start()]+joined+source[match.end():]
    assert result[:match.start()] == source[:match.start()]
    assert result[match.start()+len(joined):] == source[match.end():]
    return result, True


def word_pair(document, language):
    body=document.find(W+'body'); nodes=list(body)
    headings=[i for i,n in enumerate(nodes) if n.tag==W+'p' and text(n).startswith('15. ')]
    if len(headings)!=1: return None
    first,endings=SENTENCES[language]; pairs=[]
    for i in range(headings[0]+1,len(nodes)-1):
        a,b=nodes[i:i+2]
        if a.tag!=W+'p' or b.tag!=W+'p' or text(a)!=first or text(b) not in endings: continue
        # No bookmarks, hyperlinks, fields, nested text or non-text runs to relocate.
        if any(n.tag not in (W+'pPr',W+'r') for p in (a,b) for n in p): continue
        if any(n.tag not in (W+'rPr',W+'t') for p in (a,b) for r in p.findall(W+'r') for n in r): continue
        props=[p.find(W+'pPr') for p in (a,b)]
        if any(p is None for p in props) or c14n(props[0])!=c14n(props[1]): continue
        if any(p.find(W+'pStyle') is None or p.find(W+'pStyle').get(W+'val') not in ('BodyText','FirstParagraph','Compact','PilotLead') for p in props):continue
        pairs.append((a,b))
    return pairs[0] if len(pairs)==1 else None


def join_word(document, language):
    revised=copy.deepcopy(document); pair=word_pair(revised,language)
    if pair is None:return revised,False
    a,b=pair; original_a=copy.deepcopy(a); original_b=copy.deepcopy(b)
    prefix=len(a)
    if language=='english':
        run=E.SubElement(a,W+'r'); E.SubElement(run,W+'t',{'{http://www.w3.org/XML/1998/namespace}space':'preserve'}).text=' '
    for child in list(b):
        if child.tag!=W+'pPr':a.append(child)
    b.getparent().remove(b)
    # Reversible exact delta, including every run property and second paragraph property.
    restored=copy.deepcopy(revised)
    candidates=[p for p in restored.find(W+'body') if p.tag==W+'p' and text(p)==text(a)]
    assert len(candidates)==1
    joined=candidates[0]
    assert [c14n(n) for n in list(joined)[:prefix]]==[c14n(n) for n in original_a]
    expected=[n for n in original_b if n.tag!=W+'pPr']
    assert [c14n(n) for n in list(joined)[prefix+(language=='english'):]]==[c14n(n) for n in expected]
    parent=joined.getparent();index=parent.index(joined);parent.remove(joined)
    parent.insert(index,original_a);parent.insert(index+1,original_b)
    assert c14n(restored)==c14n(document)
    assert [n.text for n in revised.iter(W+'t') if n.text!=' ']==[n.text for n in document.iter(W+'t') if n.text!=' ']
    return revised,True


def word_prefix_geometry(bbox):
    """Exact pre-Q15 words, allowing only the Word cover to omit its footer."""
    pages=E.fromstring(bbox).findall('.//{*}page');result=[];markers=0
    for index,page in enumerate(pages,1):
        footers=[]
        for line in page.findall('.//{*}line'):
            if ''.join(w.text or '' for w in line.findall('{*}word'))==f'{index}/{len(pages)}':footers.append(line)
        assert len(footers)<=1,'Ambiguous footer'
        if footers:assert float(footers[0].get('yMin'))>float(page.get('height'))*.9,'Misplaced footer'
        else:assert index==1,'Only Word cover may omit footer'
        excluded=set(footers[0].findall('{*}word')) if footers else set()
        for word in page.findall('.//{*}word'):
            if word in excluded:continue
            if word.text=='15.':markers+=1
            if markers==0:result.append((index,dict(word.attrib),word.text))
    assert markers==1,'Ambiguous Q15 anchor'
    return result


RUNNER='''import base64,json,sys,subprocess
from pathlib import Path
p=json.load(sys.stdin)
for name in p['names']:
 source=Path('/input/'+name+'.html').read_bytes()
 code="import sys; from weasyprint import HTML; sys.stdout.buffer.write(HTML(string=sys.stdin.read(),media_type='print').write_pdf())"
 pdf=subprocess.check_output([sys.executable,'-c',code],input=source)
 print(json.dumps(dict(name=name,pdf=base64.b64encode(pdf).decode())),flush=True)
'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source','english','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();assert not a.output.exists();a.output.mkdir(parents=True)
    report=dict(completed=False,native_export=False,template_modified=False,release_acceptance=False,
        microsoft_word_acceptance=False,worker_image=IMAGE,checker_sha256=sha(Path(__file__)),rows=[],
        limits=['Synthetic fixed Q15 pair only; not a template implementation',
                'Paired offline PDF rehearsal, not native DSW exports; native-baseline differences are reported explicitly',
                'LibreOffice previews do not establish Microsoft Word acceptance'])
    helper=Environment(loader=FileSystemLoader(a.english),extensions=['jinja2.ext.do']).get_template('src/pdf/short-resources.html.j2').module
    try:
        variants=[]
        for case in ('profile-partial','empty'):
            for profile in ('review','submission'):
                for language in ('english','chinese'):
                    stem=case+'-'+profile+'-'+language; original_html=(a.source/'renders'/(stem+'.html')).read_text()
                    changed_html,selected=join_html(original_html,language)
                    assert selected==(case=='profile-partial')
                    # Reproduce the existing PDF-entry-only keep before either trial.
                    baseline=helper.document(original_html)
                    # Joining changes grammar. Carry the proven original keep in this
                    # isolated trial only, not by weakening the production helper.
                    trial=changed_html
                    if baseline!=original_html:
                        from short_resources_contract import OPENING,HINT
                        assert baseline==original_html.replace(OPENING,HINT,1)
                        trial=trial.replace(OPENING,HINT,1)
                    source_docx=a.source/'renders'/(stem+'.docx')
                    with zipfile.ZipFile(source_docx) as archive:
                        original=E.fromstring(archive.read('word/document.xml'))
                        changed,word_selected=join_word(original,language)
                        assert word_selected==selected,(stem,'Word selector differs')
                        for mode,html,document in [('baseline',baseline,original),('joined',trial,changed)]:
                            name=stem+'-'+mode; (a.output/(name+'.html')).write_text(str(html))
                            target=a.output/(name+'.docx')
                            if mode=='baseline' or not selected:target.write_bytes(source_docx.read_bytes())
                            else:
                                with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED) as output:
                                    for part in archive.namelist():
                                        output.writestr(part,E.tostring(document,xml_declaration=True,encoding='UTF-8',standalone=True) if part=='word/document.xml' else archive.read(part))
                            with zipfile.ZipFile(target) as output:
                                assert output.namelist()==archive.namelist()
                                for part in archive.namelist():
                                    if part!='word/document.xml':assert output.read(part)==archive.read(part)
                            with tempfile.TemporaryDirectory(prefix='resource-prose-lo-') as temp:
                                dest=a.output/'word-preview';dest.mkdir(exist_ok=True)
                                r=subprocess.run(['libreoffice','-env:UserInstallation='+Path(temp).as_uri(),'--headless','--convert-to','pdf','--outdir',str(dest),str(target)],capture_output=True,text=True,timeout=120)
                                assert r.returncode==0 and (dest/(name+'.pdf')).exists(),r.stderr
                            variants.append(name)
                    report['rows'].append(dict(stem=stem,case=case,profile=profile,language=language,selected=selected,
                        source_html_sha256=sha(a.source/'renders'/(stem+'.html')),source_docx_sha256=sha(source_docx),source_pdf_sha256=sha(a.source/'renders'/(stem+'.pdf'))))
        r=subprocess.run(['docker','run','--rm','--network','none','-i','-v',str(a.output.resolve())+':/input:ro','--entrypoint','python',IMAGE,'-c',RUNNER],input=json.dumps(dict(names=variants)).encode(),capture_output=True)
        report['engine_stderr']=r.stderr.decode();assert r.returncode==0,report['engine_stderr']
        for line in r.stdout.splitlines():
            value=json.loads(line);assert value['name'] in variants
            (a.output/(value['name']+'.pdf')).write_bytes(base64.b64decode(value['pdf'],validate=True))
        for row in report['rows']:
            stem=row['stem']; old,new=[a.output/(stem+'-'+mode+'.pdf') for mode in ('baseline','joined')]
            before,after=snapshot(old),snapshot(new)
            soup=BeautifulSoup((a.source/'renders'/(stem+'.html')).read_text(),'html.parser')
            compare_text(before[0],after[0],soup)
            assert prefix_geometry(before[1])==prefix_geometry(after[1]),'Other PDF questions moved'
            assert fonts(old)==fonts(new),'Paired PDF font inventory changed'
            assert len(after[0])<=len(before[0]),'PDF grew'
            assert line_box_overlaps(before[1])==line_box_overlaps(after[1]),'New PDF line overlaps'
            native=a.source/'renders'/(stem+'.pdf');native_box=snapshot(native)[1]
            word_paths=[a.output/'word-preview'/(stem+'-'+mode+'.pdf') for mode in ('baseline','joined')]
            word_snapshots=[snapshot(path) for path in word_paths]
            compare_text(word_snapshots[0][0],word_snapshots[1][0],soup)
            assert word_prefix_geometry(word_snapshots[0][1])==word_prefix_geometry(word_snapshots[1][1]),'Other Word questions moved'
            assert len(word_snapshots[1][0])<=len(word_snapshots[0][0]),'Word grew'
            assert geometry(a.source/'word-preview'/(stem+'.pdf'))==geometry(word_paths[0]),'Native Word preview baseline drift'
            if not row['selected']:
                assert before[1]==after[1] and geometry(word_paths[0])==geometry(word_paths[1])
            row.update(pdf_pages=[len(before[0]),len(after[0])],word_pages=[len(s[0]) for s in word_snapshots],
                native_pdf_baseline_geometry_identical=native_box==before[1],native_pdf_fonts_identical=fonts(native)==fonts(old),
                paired_fonts_identical=True,paired_prefix_geometry_identical=True,
                native_word_baseline_geometry_identical=True,pdf_line_box_overlaps=line_box_overlaps(after[1]),
                artifact_sha256={str(path.relative_to(a.output)):sha(path) for mode in ('baseline','joined') for path in [a.output/(stem+'-'+mode+'.pdf'),a.output/(stem+'-'+mode+'.docx'),a.output/'word-preview'/(stem+'-'+mode+'.pdf')]})
            print(json.dumps(row),flush=True)
        report['completed']=True
    except Exception as error:report['failure']=repr(error);raise
    finally:(a.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':
    import sys
    # The baseline PDF helper is a locked English source, not a generated variant.
    early=argparse.ArgumentParser(add_help=False);early.add_argument('--english',type=Path,required=True)
    known,_=early.parse_known_args();sys.path.insert(0,str(known.english.resolve()/'scripts'))
    main()
