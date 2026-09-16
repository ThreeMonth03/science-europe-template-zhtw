"""Exact same-fixture Q11 delta in native HTML, PDF and editable DOCX."""
import argparse
import copy
import json
from pathlib import Path
import subprocess
import sys
import zipfile
from bs4 import BeautifulSoup
from docx import Document
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from artifact_utils import sha
from check_budget_outputs import body,xml
from check_budget_spacing_outputs import pdf_raw_page_texts
from check_identifier_concise_outputs import formatted_characters,verified_list_suffixes
from check_identifier_spacing_outputs import geometry
from check_narrative_outputs import compact
from check_short_budget_outputs import prompt_lines,question_pages
from check_word_rhythm_outputs import assert_styles,inspect_preview
from check_word_short_budget_outputs import verify_preview_paragraphs
from compare_runtime_outputs import markers

CASES=['personal-transfer-complete','archive-basis-single','archive-basis-pair','preservation-partial',
       'preservation-custom','empty','negative','budget-long-no-currency']
EXTRA={'archive-basis-single','archive-basis-pair','preservation-partial','preservation-custom'}


def planned(before,after,language):
    from archive_basis_contract import LEAD
    leads=[n for n in before.select('.post-project-archive .answer-lead') if n.get_text(strip=True)==LEAD[language]]
    new=after.select('.archive-extension-basis-summary p')
    assert len(leads)==len(new)<=1
    if not leads:return [],''
    return [LEAD[language]]+[n.get_text() for n in leads[0].find_next_sibling().select('li')],new[0].get_text()


def word_delta(before,after,old_texts,new_text):
    left,right=body(before),body(after);removed_id=None
    if old_texts:
        indexes=[i for i,n in enumerate(left) if n.tag==qn('w:p') and Paragraph(n,before).text==old_texts[0]]
        assert len(indexes)==1;index=indexes[0]
        group=left[index:index+len(old_texts)]
        assert [Paragraph(n,before).text for n in group]==old_texts
        assert Paragraph(group[0],before).style.name=='Pilot Lead'
        ids={n.get(qn('w:val')) for p in group[1:] for n in p.iter(qn('w:numId'))}
        assert len(ids)==1;removed_id=int(ids.pop())
        p=Paragraph(right[index],after)
        assert p.text==new_text and p.style.name=='Body Text'
        props=right[index].find(qn('w:pPr'))
        assert len(props)==1 and props[0].tag==qn('w:pStyle')
        assert all(style is None for _,style in formatted_characters(right[index])), 'New direct character formatting'
        left=left[:index]+[right[index]]+left[index+len(old_texts):]
    assert len(left)==len(right)
    remapped=0
    for a,b in zip(left,right):
        candidate=copy.deepcopy(a)
        if removed_id is not None:
            for n in candidate.iter(qn('w:numId')):
                value=int(n.get(qn('w:val')))
                assert value!=removed_id, 'Removed list shared with non-owned content'
                if value>removed_id:n.set(qn('w:val'),str(value-1));remapped+=1
        assert xml(candidate)==xml(b),'Non-owned Word paragraph, table, format or answer changed'
    numbering=copy.deepcopy(before.part.numbering_part.element)
    if removed_id is not None:
        matches=[n for n in numbering if n.tag==qn('w:num') and int(n.get(qn('w:numId')))==removed_id]
        assert len(matches)==1;numbering.remove(matches[0])
        for n in numbering:
            if n.tag==qn('w:num') and int(n.get(qn('w:numId')))>removed_id:
                n.set(qn('w:numId'),str(int(n.get(qn('w:numId')))-1))
    assert xml(numbering)==xml(after.part.numbering_part.element),'Unexpected numbering definition change'
    links=lambda d:sorted(r.target_ref for r in d.part.rels.values() if r.is_external)
    assert links(before)==links(after)
    return {'replaced_paragraphs':len(old_texts),'new_paragraphs':bool(new_text),'renumbered_unchanged_list_items':remapped}


def pdf_delta(old,new,before,after,old_texts,new_text):
    a,b=[pdf_raw_page_texts(p) for p in [old,new]]
    if old_texts:
        heading=compact(before.select_one('#q-data-preservation h3').get_text())
        starts=[next(i for i,t in enumerate(pages) if heading in t) for pages in [a,b]]
        assert starts[0]==starts[1], 'Unexpected earlier-page movement'
        old_clean,old_markers=verified_list_suffixes(a,subprocess.check_output(['pdftotext','-bbox-layout',str(old),'-']),before,starts[0])
        new_clean,new_markers=verified_list_suffixes(b,subprocess.check_output(['pdftotext','-bbox-layout',str(new),'-']),after,starts[1])
        removed=old_markers-new_markers
        assert not new_markers-old_markers
        assert sorted(text for (text,x),count in removed.items() for _ in range(count))==sorted('•'+compact(t) for t in old_texts[1:])
        left=''.join(question_pages(old_clean,before));right=''.join(question_pages(new_clean,after))
        prefix,tail=left.split(heading,1)
        next_heading=compact(before.select_one('#q-access-data h3').get_text())
        middle,suffix=tail.split(next_heading,1)
        previous=compact(''.join(old_texts));assert middle.count(previous)==1
        middle=middle.replace(previous,compact(new_text),1)
        assert prefix+heading+middle+next_heading+suffix==right,'Unexpected PDF body text/punctuation change'
        return {'removed_generated_bullets':sum(removed.values()),'remaining_bound_bullets':sum(new_markers.values())}
    assert question_pages(a,before)==question_pages(b,after),'Control PDF text changed'
    assert geometry(old)==geometry(new),'Control PDF geometry changed'
    return {'unchanged_control_geometry':True}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['build','prior','prior-extra','english']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--cases',nargs='+',default=CASES);p.add_argument('--output',type=Path)
    a=p.parse_args();sys.path[:0]=[str(a.english.resolve()/n) for n in ['scripts','tests']]
    from archive_basis_contract import compare
    import check_missing_info_outputs as missing
    missing.HERE=a.english.resolve()
    target=a.output or a.build/'archive-basis-report.json';assert not target.exists()
    helpers=['check_budget_outputs.py','check_budget_spacing_outputs.py','check_identifier_concise_outputs.py',
             'check_identifier_spacing_outputs.py','check_narrative_outputs.py','check_short_budget_outputs.py',
             'check_word_rhythm_outputs.py','check_word_short_budget_outputs.py','check_missing_info_outputs.py']
    report={'selected_checks_passed':False,'release_acceptance':False,'rows':[],
            'checker_sha256':sha(Path(__file__)),'contract_sha256':sha(a.english/'scripts/archive_basis_contract.py'),
            'helper_sha256':{n:sha(Path(__file__).with_name(n)) for n in helpers},
            'package_sha256':{n:sha(a.build/n) for n in ['english.zip','chinese.zip']},
            'limits':['Eight synthetic cases per language, not all questionnaires',
                      'PDF text comparison normalizes whitespace; exact HTML and DOCX separately preserve punctuation and spacing',
                      'Only geometrically verified generated bullet suffixes may be removed from PDF extraction',
                      'LibreOffice previews are not Microsoft Word acceptance']}
    try:
        for case in a.cases:
            prior=a.prior_extra if case in EXTRA else a.prior
            for language in ['english','chinese']:
                stem=case+'-'+language;old=prior/'renders'/stem;new=a.build/'renders'/stem
                before=BeautifulSoup(old.with_suffix('.html').read_text(),'html.parser')
                row,after=missing.inspect(a.build,case,language)
                assert markers(before)==markers(after)
                compare(before.select_one('#dmp-content'),after.select_one('#dmp-content'),language)
                old_texts,new_text=planned(before,after,language)
                for fmt in ['html','pdf','docx']:
                    x,y=[json.loads(n.with_suffix('.'+fmt+'.fixture.json').read_text()) for n in [old,new]]
                    for key in ['recipe_sha256','events_sha256','km_sha256']:assert x[key]==y[key]
                    assert x['package_sha256']==sha(prior/(language+'.zip'))
                    assert y['package_sha256']==report['package_sha256'][language+'.zip']
                left,right=[Document(n.with_suffix('.docx')) for n in [old,new]]
                assert_styles(right);row['word_delta']=word_delta(left,right,old_texts,new_text)
                with zipfile.ZipFile(old.with_suffix('.docx')) as x,zipfile.ZipFile(new.with_suffix('.docx')) as y:
                    for part in ['word/styles.xml','word/fontTable.xml']:assert x.read(part)==y.read(part)
                row['pdf_delta']=pdf_delta(old.with_suffix('.pdf'),new.with_suffix('.pdf'),before,after,old_texts,new_text)
                row['prior_pages']=len(pdf_raw_page_texts(old.with_suffix('.pdf')))
                assert row['pages']<=row['prior_pages'],'PDF page count increased'
                preview=a.build/'word-preview'/(stem+'.pdf');old_preview=prior/'word-preview'/(stem+'.pdf')
                row['word_pages']=inspect_preview(preview);row['prior_word_pages']=inspect_preview(old_preview)
                assert row['word_pages']<=row['prior_word_pages'],'Word page count increased'
                if not old_texts:assert geometry(old_preview)==geometry(preview),'Control Word preview geometry changed'
                row['preview_paragraphs_checked']=verify_preview_paragraphs(right,preview,after)
                if new_text:
                    row['summary_lines']={kind:prompt_lines(file,new_text) for kind,file in [('pdf',new.with_suffix('.pdf')),('word',preview)]}
                assert not row['errors'] and not row['reading_issues'],row
                for file in [new.with_suffix('.docx'),new.with_suffix('.docx.fixture.json'),preview]:row['artifact_sha256'][str(file.relative_to(a.build))]=sha(file)
                row['prior_root']=str(prior)
                row['prior_artifact_sha256']={str(f.relative_to(prior)):sha(f) for f in [old.with_suffix('.'+fmt+extra) for fmt in ['html','pdf','docx'] for extra in ['','.fixture.json']]+[old_preview]}
                row['passed']=True;report['rows'].append(row)
                print(json.dumps({k:row[k] for k in ['case','language','pages','word_pages','word_delta']}),flush=True)
        report['selected_checks_passed']=True
    except Exception as error:
        report['failure']=repr(error);raise
    finally:target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':main()
