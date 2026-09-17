"""Exact Q2-only before/after contract across native HTML, PDF and editable Word."""
import argparse
import difflib
import json
from pathlib import Path
import subprocess
import sys
import zipfile
from collections import Counter
from bs4 import BeautifulSoup
from docx import Document
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from lxml import etree
from artifact_utils import sha
from check_budget_outputs import body,xml
from check_budget_spacing_outputs import pdf_raw_page_texts,line_box_overlaps
from check_identifier_concise_outputs import formatted_characters
from check_archive_gap_outputs import body_geometry
from check_narrative_outputs import compact
from check_short_budget_outputs import question_pages
from check_word_rhythm_outputs import assert_styles,inspect_preview
from check_word_short_budget_outputs import verify_preview_paragraphs
from compare_runtime_outputs import markers
import check_format_outputs as formats

CASES=['format-rich','format-partial','format-reading','empty','negative']
PLAIN_CJK=b'<w:rPr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:rFonts w:hint="eastAsia"></w:rFonts></w:rPr>'


def verified_format_markers(pages,bbox,soup,start):
    """Permit only mixed •/◦ page suffixes bound to actual list text and indents."""
    glyphs='•◦'
    assert not any(c in soup.get_text() for c in glyphs),'Authored marker characters need a different oracle'
    nodes=etree.fromstring(bbox).findall('.//{*}page');assert len(nodes)==len(pages)
    assert 0<=start<len(pages)
    clean=[];signatures=Counter()
    for index,(page,node) in enumerate(zip(pages,nodes)):
        if index<start:clean.append(page);continue
        text=page.rstrip(glyphs);suffix=page[len(text):]
        assert not any(c in text for c in glyphs),'Only generated page suffixes are admitted'
        words=[w for w in node.findall('.//{*}word') if w.text in glyphs]
        assert Counter(suffix)==Counter(w.text for w in words),'Marker count/type changed'
        for word in words:
            line=word.getparent();assert etree.QName(line).localname=='line'
            value=compact(''.join(line.itertext()))
            assert value.startswith(word.text) and len(value)>1 and sum(value.count(c) for c in glyphs)==1
            signatures[(value,round(float(word.get('xMin')),3))]+=1
        clean.append(text)
    return clean,signatures


def word_delta(before,after,pairs):
    left,right=body(before),body(after);assert len(left)==len(right)
    active=False;changed=0
    for a,b in zip(left,right):
        if a.tag==qn('w:p'):
            p=Paragraph(a,before)
            if p.style.name=='Heading 3' and p.text.startswith('2. '):active=True
            if p.style.name=='Heading 3' and p.text.startswith('3. '):active=False
        if xml(a)==xml(b):continue
        assert active and a.tag==b.tag==qn('w:p') and changed<len(pairs),'Unexpected Word block change'
        q=Paragraph(b,after);old,new=pairs[changed]
        assert p.text==old and q.text==new,(p.text,old,q.text,new)
        props=lambda node:xml(node) if node is not None else None
        assert props(a.find(qn('w:pPr')))==props(b.find(qn('w:pPr')))
        x,y=formatted_characters(a),formatted_characters(b)
        for op,i,j,k,l in difflib.SequenceMatcher(a=p.text,b=q.text,autojunk=False).get_opcodes():
            if op=='equal':assert x[i:j]==y[k:l], 'Retained character formatting changed'
            else:assert all(style in {None,PLAIN_CJK} for _,style in x[i:j]+y[k:l]), 'Changed styled text'
        changed+=1
    assert changed==len(pairs)
    assert xml(before.part.numbering_part.element)==xml(after.part.numbering_part.element)
    links=lambda doc:sorted(r.target_ref for r in doc.part.rels.values() if r.is_external)
    assert links(before)==links(after)
    return changed


def pdf_delta(old,new,before,after,pairs):
    sources=[old,new];soups=[before,after]
    pages=[pdf_raw_page_texts(f) for f in sources]
    boxes=[subprocess.check_output(['pdftotext','-bbox-layout',str(f),'-']) for f in sources]
    if not pairs:
        assert question_pages(pages[0],before)==question_pages(pages[1],after)
        assert body_geometry(boxes[0],before)==body_geometry(boxes[1],after)
        return {'unchanged_control_geometry':True}
    cleaned=[];bullets=[]
    for texts,bbox,soup in zip(pages,boxes,soups):
        heading=compact(soup.select_one('#q-what-data h3').get_text())
        start=next(i for i,t in enumerate(texts) if heading in t)
        clean,markers=verified_format_markers(texts,bbox,soup,start)
        cleaned.append(''.join(question_pages(clean,soup)));bullets.append(markers)
    assert bullets[0]==bullets[1],'Generated list marker text or indent changed'
    h2=compact(before.select_one('#q-what-data h3').get_text())
    h3=compact(before.select_one('#q-docs-metadata h3').get_text())
    prefix,tail=cleaned[0].split(h2,1);middle,suffix=tail.split(h3,1)
    cursor=0
    for old_text,new_text in pairs:
        old_text,new_text=compact(old_text),compact(new_text)
        index=middle.find(old_text,cursor);assert index>=0
        middle=middle[:index]+new_text+middle[index+len(old_text):];cursor=index+len(new_text)
    assert prefix+h2+middle+h3+suffix==cleaned[1],'Unexpected PDF body text or punctuation change'
    return {'changed_format_summaries':len(pairs),'verified_generated_markers':sum(bullets[1].values())}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['build','prior','english']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--output',type=Path);a=p.parse_args()
    sys.path[:0]=[str(a.english.resolve()/n) for n in ['scripts','tests']]
    from format_reading_contract import compare
    import check_missing_info_outputs as missing
    missing.HERE=a.english.resolve()
    report={'selected_checks_passed':False,'release_acceptance':False,'rows':[],
        'checker_sha256':sha(Path(__file__)),'contract_sha256':sha(a.english/'scripts/format_reading_contract.py'),
        'helper_sha256':{n:sha(Path(__file__).with_name(n)) for n in ['check_budget_outputs.py','check_budget_spacing_outputs.py',
            'check_identifier_concise_outputs.py','check_archive_gap_outputs.py','check_narrative_outputs.py','check_short_budget_outputs.py',
            'check_word_rhythm_outputs.py','check_word_short_budget_outputs.py','compare_runtime_outputs.py','check_format_outputs.py','check_missing_info_outputs.py']},
        'package_sha256':{n:sha(a.build/n) for n in ['english.zip','chinese.zip']},
        'limits':['Five synthetic cases per language, not all questionnaire combinations',
                  'PDF comparison normalizes whitespace; exact HTML and editable Word separately preserve punctuation and authored spacing',
                  'LibreOffice preview is not Microsoft Word acceptance']}
    target=a.output or a.build/'format-reading-report.json';assert not target.exists()
    try:
        for case in CASES:
            for language in ['english','chinese']:
                stem=case+'-'+language;old=a.prior/'renders'/stem;new=a.build/'renders'/stem
                before=BeautifulSoup(old.with_suffix('.html').read_text(),'html.parser')
                row,after=missing.inspect(a.build,case,language)
                assert markers(before)==markers(after)
                pairs=compare(*[BeautifulSoup(str(s.select_one('#dmp-content')),'html.parser') for s in [before,after]],language)
                row['formats']=formats.inspect(a.build,case,language)
                for fmt in ['html','pdf','docx']:
                    x,y=[json.loads(f.with_suffix('.'+fmt+'.fixture.json').read_text()) for f in [old,new]]
                    for key in ['recipe_sha256','events_sha256','km_sha256']:assert x[key]==y[key]
                    assert x['package_sha256']==sha(a.prior/(language+'.zip'))
                    assert y['package_sha256']==report['package_sha256'][language+'.zip']
                left,right=[Document(f.with_suffix('.docx')) for f in [old,new]]
                assert_styles(right);row['changed_word_summaries']=word_delta(left,right,pairs)
                with zipfile.ZipFile(old.with_suffix('.docx')) as x,zipfile.ZipFile(new.with_suffix('.docx')) as y:
                    for part in ['word/styles.xml','word/fontTable.xml']:assert x.read(part)==y.read(part)
                row['pdf_delta']=pdf_delta(old.with_suffix('.pdf'),new.with_suffix('.pdf'),before,after,pairs)
                row['prior_pages']=len(pdf_raw_page_texts(old.with_suffix('.pdf')))
                assert row['pages']<=row['prior_pages'],'PDF page count increased'
                preview=a.build/'word-preview'/(stem+'.pdf');old_preview=a.prior/'word-preview'/(stem+'.pdf')
                row['word_pages']=inspect_preview(preview);row['prior_word_pages']=inspect_preview(old_preview)
                assert row['word_pages']<=row['prior_word_pages'],'Word page count increased'
                row['preview_paragraphs_checked']=verify_preview_paragraphs(right,preview,after)
                # Font-metric rectangles are not ink bounds. Preserve diagnostics;
                # page bounds/paragraph retention and visual review are separate.
                row['font_box_overlaps']={}
                for kind,files in [('pdf',[old.with_suffix('.pdf'),new.with_suffix('.pdf')]),('word',[old_preview,preview])]:
                    overlaps=[line_box_overlaps(subprocess.check_output(['pdftotext','-bbox-layout',str(f),'-'])) for f in files]
                    row['font_box_overlaps'][kind]={'before':overlaps[0],'after':overlaps[1]}
                    if not pairs:assert overlaps[0]==overlaps[1]
                if not pairs:
                    boxes=[subprocess.check_output(['pdftotext','-bbox-layout',str(f),'-']) for f in [old_preview,preview]]
                    assert body_geometry(boxes[0],before)==body_geometry(boxes[1],after)
                assert not row['errors'] and not row['reading_issues'],row
                row['summary_changes']=pairs;row['passed']=True
                row['artifact_sha256']={str(f.relative_to(a.build)):sha(f) for f in [new.with_suffix('.'+fmt+extra) for fmt in ['html','pdf','docx'] for extra in ['','.fixture.json']]+[preview]}
                row['prior_artifact_sha256']={str(f.relative_to(a.prior)):sha(f) for f in [old.with_suffix('.'+fmt+extra) for fmt in ['html','pdf','docx'] for extra in ['','.fixture.json']]+[old_preview]}
                report['rows'].append(row);print(json.dumps({k:row[k] for k in ['case','language','pages','word_pages','changed_word_summaries']}),flush=True)
        report['selected_checks_passed']=True
    except Exception as error:report['failure']=repr(error);raise
    finally:target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':main()
