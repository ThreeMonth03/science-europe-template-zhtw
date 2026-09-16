"""Same-fixture native 0.3.25 -> 0.3.26 comparison, with exact width-only Word oracle."""
import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys
import zipfile
from lxml import etree
from bs4 import BeautifulSoup
from docx import Document
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from artifact_utils import sha
from check_budget_outputs import body
from check_budget_spacing_outputs import pdf_raw_page_texts
from check_short_budget_outputs import question_pages,prompt_lines
from check_word_rhythm_outputs import inspect_preview,assert_styles,compare_questions
from compare_runtime_outputs import markers

CASES=['partial','budget-mixed-gaps','empty','negative','personal-transfer-complete','budget-long-no-currency','budget-many']
AFFECTED={'partial','budget-mixed-gaps'}


def word_pages(raw,bbox):
    """LO paints footers before body text; remove only verified bottom footers."""
    compact=lambda s:''.join(s.split())
    pages=raw.split('\f')
    if not pages[-1].strip():pages.pop()
    geometry=etree.fromstring(bbox).findall('.//{*}page');assert len(pages)==len(geometry)
    result=[]
    for number,(text,page) in enumerate(zip(pages,geometry),1):
        footer=f'{number}/{len(pages)}'
        lines=[line for line in text.splitlines() if line.strip()]
        matches=[line for line in page.findall('.//{*}line') if compact(''.join(line.itertext()))==footer]
        if matches:
            assert len(matches)==1 and float(matches[0].get('yMin'))>float(page.get('height'))*.9
            assert sum(compact(line)==footer for line in lines)==1
            lines=[line for line in lines if compact(line)!=footer]
        else:
            assert number==1 and all(compact(line)!=footer for line in lines),'Only cover may omit its footer'
        result.append(compact(''.join(lines)))
    return result


def paragraph_texts(document,soup):
    """LO extracts U+2011 as '-'; authorize only complete owned date text runs."""
    dates=Counter(n.get_text() for n in soup.select('.date-value'))
    allowed={value.replace('-','\u2011'):value for value in dates}
    paragraphs=[Paragraph(p,document) for node in body(document) for p in node.iter(qn('w:p'))]
    actual=Counter(t.text for p in paragraphs for t in p._p.iter(qn('w:t')) if t.text in allowed)
    assert actual==Counter({date:dates[value] for date,value in allowed.items()}),'Owned date runs differ from HTML'
    values=[]
    for p in paragraphs:
        value=p.text
        runs=Counter(t.text for t in p._p.iter(qn('w:t')) if t.text in allowed)
        for date,count in runs.items():
            assert value.count(date)==count,'Date substring is also present in unrelated text'
            value=value.replace(date,allowed[date])
        values.append(value)
    return values


def verify_preview_paragraphs(document,preview,soup):
    compact=lambda s:''.join(s.split())
    counts=Counter(compact(text) for text in paragraph_texts(document,soup) if compact(text))
    raw=subprocess.check_output(['pdftotext','-raw',str(preview),'-'],text=True)
    bbox=subprocess.check_output(['pdftotext','-bbox-layout',str(preview),'-'])
    text=''.join(word_pages(raw,bbox))
    missing=[{'text':value,'expected':count,'actual':text.count(value)} for value,count in counts.items() if text.count(value)<count]
    assert not missing,('Word-preview paragraphs missing',missing)
    return sum(counts.values())


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['build','prior','english']:p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--cases',nargs='+',default=CASES);p.add_argument('--output',type=Path);a=p.parse_args()
    sys.path.insert(0,str(a.english.resolve()/'scripts'))
    from word_short_budget_contract import compare_blocks
    import check_missing_info_outputs as missing
    missing.HERE=a.english.resolve()
    target=a.output or a.build/'word-short-budget-report.json';assert not target.exists()
    report={'selected_checks_passed':False,'release_acceptance':False,'version':'0.3.26','rows':[],
        'checker_sha256':sha(Path(__file__)),'word_contract_sha256':sha(a.english/'scripts/word_short_budget_contract.py'),
        'package_sha256':{n:sha(a.build/n) for n in ['english.zip','chinese.zip']},
        'prior_package_sha256':{n:sha(a.prior/n) for n in ['english.zip','chinese.zip']},
        'limits':['Seven synthetic cases per language, not all possible questionnaires',
            'LibreOffice preview, not Microsoft Word acceptance','Tables-only worker; no experimental font patch']}
    try:
        for case in a.cases:
            soups=[]
            for language in ['english','chinese']:
                row,soup=missing.inspect(a.build,case,language);soups.append(soup)
                stem=case+'-'+language;old=a.prior/'renders'/stem;new=a.build/'renders'/stem
                left=BeautifulSoup(old.with_suffix('.html').read_text(),'html.parser')
                compare_questions(left,soup)
                assert not soup.select('.word-short-budget'),'Word-only hint leaked into HTML'
                for fmt in ['html','pdf','docx']:
                    before=json.loads(old.with_suffix('.'+fmt+'.fixture.json').read_text());after=json.loads(new.with_suffix('.'+fmt+'.fixture.json').read_text())
                    for key in ['recipe_sha256','events_sha256','km_sha256']:assert before[key]==after[key]
                    assert before['package_sha256']==report['prior_package_sha256'][language+'.zip']
                    assert after['package_sha256']==report['package_sha256'][language+'.zip']
                old_pages=pdf_raw_page_texts(old.with_suffix('.pdf'));new_pages=pdf_raw_page_texts(new.with_suffix('.pdf'))
                assert len(old_pages)==len(new_pages)==row['pages']
                assert question_pages(old_pages,left)==question_pages(new_pages,soup),'Native PDF question text/pagination changed'
                before_doc,after_doc=[Document(path.with_suffix('.docx')) for path in [old,new]]
                assert_styles(after_doc)
                changed=compare_blocks(body(before_doc),body(after_doc))
                assert changed==int(case in AFFECTED),(case,language,'Unexpected affected table count',changed)
                row['changed_word_column_grids']=changed
                links=lambda d:sorted(r.target_ref for r in d.part.rels.values() if r.is_external)
                assert links(before_doc)==links(after_doc)
                with zipfile.ZipFile(old.with_suffix('.docx')) as x,zipfile.ZipFile(new.with_suffix('.docx')) as y:
                    for name in ['word/styles.xml','word/numbering.xml','word/fontTable.xml']:
                        assert x.read(name)==y.read(name),(name,'Unexpected Word style/font/numbering edit')
                preview=a.build/'word-preview'/(stem+'.pdf');prior_preview=a.prior/'word-preview'/(stem+'.pdf')
                row['word_pages']=inspect_preview(preview);row['prior_word_pages']=inspect_preview(prior_preview)
                assert row['word_pages']==row['prior_word_pages'],'Unexpected Word pagination change'
                row['word_preview_paragraphs_checked']=verify_preview_paragraphs(after_doc,preview,soup)
                row['verified_owned_nonbreaking_dates']=len(soup.select('.date-value'))
                if case=='partial':
                    prompt=soup.select_one('[data-fact-id="resource-amount"]').get_text()
                    row['prompt_before']=prompt_lines(prior_preview,prompt);row['prompt_after']=prompt_lines(preview,prompt)
                    assert (row['prompt_before']['line_count'],row['prompt_after']['line_count'])==((3,2) if language=='english' else (2,1))
                row['prior_artifact_sha256']={str(f):sha(f) for f in [old.with_suffix('.'+fmt+extra) for fmt in ['html','pdf','docx'] for extra in ['','.fixture.json']]+[prior_preview]}
                for f in [new.with_suffix('.docx'),new.with_suffix('.docx.fixture.json'),preview]:row['artifact_sha256'][str(f.relative_to(a.build))]=sha(f)
                row['unchanged_question_html_pdf_and_word_text']=True
                report['rows'].append(row)
                print(json.dumps({k:row[k] for k in ['case','language','pages','word_pages','changed_word_column_grids','errors','reading_issues']}),flush=True)
            assert markers(soups[0])==markers(soups[1])
        report['selected_checks_passed']=len(report['rows'])==len(a.cases)*2 and all(not r['errors'] and not r['reading_issues'] for r in report['rows'])
    except Exception as error:
        report['failure']=str(error);raise
    finally:target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    assert report['selected_checks_passed'],'See preserved diagnostics'


if __name__=='__main__':main()
