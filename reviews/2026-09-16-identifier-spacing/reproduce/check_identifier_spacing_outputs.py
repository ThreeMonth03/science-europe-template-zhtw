"""Only inserted Q13 Chinese separators may change in native bilingual outputs."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import zipfile
from bs4 import BeautifulSoup
from docx import Document
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from lxml import etree
from artifact_utils import sha
from check_budget_outputs import body,xml
from check_identifier_concise_outputs import formatted_characters,CASES
from check_identifier_followup_outputs import check_followup_page_text
from check_narrative_outputs import compact
from check_budget_spacing_outputs import pdf_raw_page_texts
from check_word_rhythm_outputs import assert_styles,compare_questions,inspect_preview
from check_word_short_budget_outputs import verify_preview_paragraphs
from compare_runtime_outputs import markers
from identifier_followup_contract import check_followups


def pairs(soup,language):
    if language=='english':return []
    result=[]
    for policy in soup.select('#q-persistent-identifier .identifier-arrangement.dataset-policy'):
        sentences=[p.get_text() for p in policy.find_all('p',recursive=False)]
        if len(sentences)<2:continue
        assert len(sentences)==2 and sentences[0].endswith('。')
        assert '\u4e00'<=sentences[1][0]<='\u9fff'
        result.append((' '.join(sentences),''.join(sentences),len(sentences[0])))
    return result


def word_delta(before,after,planned):
    old,new=body(before),body(after);assert len(old)==len(new)
    active=False;count=0
    for a,b in zip(old,new):
        assert a.tag==b.tag
        if a.tag==qn('w:p'):
            p,q=Paragraph(a,before),Paragraph(b,after)
            if p.style.name=='Heading 3' and p.text.startswith('13. '):active=True
            if p.style.name=='Heading 3' and p.text.startswith('14. '):active=False
        if xml(a)==xml(b):continue
        assert active and a.tag==qn('w:p') and count<len(planned),'Unexpected Word block change'
        left,right,index=planned[count]
        assert p.text==left and q.text==right,'Wrong paragraph or unapproved text change'
        assert left[index]==' ' and left[:index]+left[index+1:]==right
        props=lambda n:xml(n) if n is not None else None
        assert props(a.find(qn('w:pPr')))==props(b.find(qn('w:pPr')))
        chars=formatted_characters(a)
        assert chars[:index]+chars[index+1:]==formatted_characters(b),'Retained character formatting changed'
        count+=1
    assert count==len(planned)
    return count


def pdf_reading_text(pdf):
    """Remove only line/page separators and verified numeric footers, not spaces."""
    pages=subprocess.check_output(['pdftotext','-raw',str(pdf),'-'],text=True).split('\f')
    if not pages[-1].strip():pages.pop()
    clean=[]
    for number,page in enumerate(pages,1):
        lines=[line.strip() for line in page.splitlines() if line.strip()]
        assert compact(lines[-1])==f'{number}/{len(pages)}','Unexpected footer'
        clean.append(''.join(lines[:-1]))
    return clean


def pdf_delta(before,after,soup,planned):
    heading=soup.select_one('#q-persistent-identifier h3').get_text()
    # Compare complete QUESTION text. No punctuation or horizontal whitespace
    # normalization, no generic Chinese-space removal. Newlines may reflow.
    start=soup.select_one('.question h3').get_text()
    left=''.join(pdf_reading_text(before));right=''.join(pdf_reading_text(after))
    # Heading line wraps do not insert semantic spaces in these fixed fixtures.
    assert left.count(start)==right.count(start)==1
    left=left[left.index(start):];right=right[right.index(start):]
    if not planned:
        assert left==right,'Unchanged-control PDF text/space/punctuation changed'
        return
    assert left.count(heading)==right.count(heading)==1
    prefix,tail=left.split(heading,1)
    end=soup.select_one('#q-dm-responsible h3').get_text()
    middle,suffix=tail.split(end,1)
    cursor=0
    for old,new,_ in planned:
        index=middle.find(old,cursor);assert index>=0,('Owned separator missing from baseline',old)
        middle=middle[:index]+new+middle[index+len(old):];cursor=index+len(new)
    assert prefix+heading+middle+end+suffix==right,'Unexpected PDF text/space/punctuation change'


def geometry(pdf):
    doc=etree.fromstring(subprocess.check_output(['pdftotext','-bbox-layout',str(pdf),'-']))
    return [etree.tostring(page) for page in doc.findall('.//{*}page')]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['build','prior','english']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--cases',nargs='+',default=CASES);p.add_argument('--output',type=Path)
    a=p.parse_args();sys.path.insert(0,str(a.english.resolve()/'scripts'))
    from generate_pilot_fixtures import IDS
    import check_missing_info_outputs as missing
    missing.HERE=a.english.resolve()
    target=a.output or a.build/'identifier-spacing-report.json';assert not target.exists()
    report={'selected_checks_passed':False,'release_acceptance':False,'rows':[],
            'checker_sha256':sha(Path(__file__)),'package_sha256':{n:sha(a.build/n) for n in ['english.zip','chinese.zip']},
            'limits':['Eight synthetic cases per language; not all possible questionnaires',
                      'Only Q13 separator changes, not all Chinese sentence spacing',
                      'LibreOffice previews are not Microsoft Word acceptance']}
    try:
        for case in a.cases:
            for language in ['english','chinese']:
                stem=case+'-'+language;old=a.prior/'renders'/stem;new=a.build/'renders'/stem
                before=BeautifulSoup(old.with_suffix('.html').read_text(),'html.parser')
                row,soup=missing.inspect(a.build,case,language)
                assert markers(before)==markers(soup);compare_questions(before,soup)
                assert str(before.select_one('body'))==str(soup.select_one('body')),'HTML body changed'
                locale='en' if language=='english' else 'zh-Hant'
                events=json.loads((a.english/'fixtures/pilot'/locale/(case+'.events.json')).read_text())
                check_followups(soup,{e['path']:e['value']['value'] for e in events},IDS,language,concise=True)
                for fmt in ['html','pdf','docx']:
                    x,y=[json.loads(n.with_suffix('.'+fmt+'.fixture.json').read_text()) for n in [old,new]]
                    for key in ['recipe_sha256','events_sha256','km_sha256']:assert x[key]==y[key]
                    assert x['package_sha256']==sha(a.prior/(language+'.zip'))
                    assert y['package_sha256']==report['package_sha256'][language+'.zip']
                planned=pairs(soup,language)
                left,right=[Document(n.with_suffix('.docx')) for n in [old,new]]
                assert_styles(right);row['removed_word_separators']=word_delta(left,right,planned)
                links=lambda d:sorted(r.target_ref for r in d.part.rels.values() if r.is_external)
                assert links(left)==links(right)
                with zipfile.ZipFile(old.with_suffix('.docx')) as x,zipfile.ZipFile(new.with_suffix('.docx')) as y:
                    for part in ['word/styles.xml','word/fontTable.xml','word/numbering.xml']:assert x.read(part)==y.read(part)
                pdf_delta(old.with_suffix('.pdf'),new.with_suffix('.pdf'),soup,planned)
                row['removed_pdf_separators']=len(planned)
                row['prior_pages']=len(pdf_raw_page_texts(old.with_suffix('.pdf')))
                assert row['pages']<=row['prior_pages']
                preview=a.build/'word-preview'/(stem+'.pdf')
                row['word_pages']=inspect_preview(preview)
                row['prior_word_pages']=inspect_preview(a.prior/'word-preview'/(stem+'.pdf'))
                assert row['word_pages']<=row['prior_word_pages']
                if not planned:
                    assert geometry(old.with_suffix('.pdf'))==geometry(new.with_suffix('.pdf')),'Control PDF geometry changed'
                    assert geometry(a.prior/'word-preview'/(stem+'.pdf'))==geometry(preview),'Control Word preview geometry changed'
                    row['control_pdf_and_word_geometry_unchanged']=True
                row['preview_paragraphs_checked']=verify_preview_paragraphs(right,preview,soup)
                row['q13_units']={}
                for kind,file in [('pdf',new.with_suffix('.pdf')),('word',preview)]:
                    row['q13_units'][kind]=check_followup_page_text(subprocess.check_output(['pdftotext','-layout',str(file),'-'],text=True),soup)
                for f in [new.with_suffix('.docx'),new.with_suffix('.docx.fixture.json'),preview]:row['artifact_sha256'][str(f.relative_to(a.build))]=sha(f)
                row['prior_artifact_sha256']={str(f.relative_to(a.prior)):sha(f) for f in [old.with_suffix('.'+fmt+extra) for fmt in ['html','pdf','docx'] for extra in ['','.fixture.json']]+[a.prior/'word-preview'/(stem+'.pdf')]}
                assert not row['errors'] and not row['reading_issues'],row
                row['passed']=True;report['rows'].append(row)
                print(json.dumps({k:row[k] for k in ['case','language','pages','word_pages','removed_word_separators']}),flush=True)
        report['selected_checks_passed']=True
    except Exception as error:
        report['failure']=repr(error)
        raise
    finally:target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':main()
