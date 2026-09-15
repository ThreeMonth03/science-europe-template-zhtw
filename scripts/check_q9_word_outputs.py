"""Compare genuine 0.3.22/0.3.23 exports: only bounded Q9 label styles change."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import zipfile
from bs4 import BeautifulSoup
from docx import Document
from artifact_utils import sha
from check_budget_outputs import question_body,body
from check_word_rhythm_outputs import inspect_preview
from probe_q8_list_continuity import locations
from check_narrative_outputs import compact

CASES=['personal-transfer-complete','empty','negative','q9-partial-flags','q9-many-datasets','q9-long-purpose']
EXPECTED={'personal-transfer-complete':1,'empty':0,'negative':0,'q9-partial-flags':2,'q9-many-datasets':7,'q9-long-purpose':1}


def groups(soup):
    result=[]
    width=lambda s:sum(2 if ord(c)>=0x2E80 else 1 for c in s)
    for item in soup.select('#q-ethical-issues > .answer > ul > li'):
        if len(item.parent.find_all('li',recursive=False))>32:continue
        children=item.find_all(recursive=False)
        if len(children)!=2 or children[0].name!='strong' or children[1].name!='ul':continue
        name,flags=children
        if name.find(True) or not 0<width(name.get_text())<=80:continue
        entries=flags.find_all('li',recursive=False)
        if not 1<=len(entries)<=2 or any(e.find(True) or not 0<width(e.get_text())<=160 for e in entries):continue
        result.append((name.get_text(),[e.get_text() for e in entries]))
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['build','prior','new-case-prior','english']:p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--cases',nargs='+',default=CASES);p.add_argument('--output',type=Path);a=p.parse_args()
    sys.path.insert(0,str(a.english.resolve()/'scripts'));import check_missing_info_outputs as missing
    missing.HERE=a.english.resolve()
    from compare_runtime_outputs import markers
    from check_budget_spacing_outputs import pdf_raw_page_texts
    from q9_word_contract import expected_blocks,xml
    target=a.output or a.build/'q9-word-report.json';assert not target.exists()
    report={'selected_checks_passed':False,'release_acceptance':False,'version':'0.3.23','rows':[],
        'checker_sha256':sha(Path(__file__)),'word_oracle_sha256':sha(a.english/'scripts/q9_word_contract.py'),
        'package_sha256':{n:sha(a.build/n) for n in ['english.zip','chinese.zip']},
        'limits':['Only bounded Q9 produced-data names are restyled','LibreOffice preview, not Microsoft Word acceptance','No claim of whole-document visual acceptance']}
    try:
        for case in a.cases:
            soups=[]
            for lang in ['english','chinese']:
                row,soup=missing.inspect(a.build,case,lang);soups.append(soup)
                prior=a.new_case_prior if case.startswith('q9-') else a.prior
                stem=case+'-'+lang;old=prior/'renders'/stem;new=a.build/'renders'/stem
                left=BeautifulSoup(old.with_suffix('.html').read_text(),'html.parser')
                assert len(left.select('.question'))==15
                assert [str(q) for q in left.select('.question')]==[str(q) for q in soup.select('.question')]
                for fmt in ['html','pdf','docx']:
                    before=json.loads(old.with_suffix('.'+fmt+'.fixture.json').read_text());after=json.loads(new.with_suffix('.'+fmt+'.fixture.json').read_text())
                    for key in ['recipe_sha256','events_sha256','km_sha256']:assert before[key]==after[key]
                    assert after['package_sha256']==report['package_sha256'][lang+'.zip']
                assert question_body(old.with_suffix('.pdf'),left)==question_body(new.with_suffix('.pdf'),soup)
                assert len(pdf_raw_page_texts(old.with_suffix('.pdf')))==row['pages']
                entries=groups(soup);assert len(entries)==EXPECTED[case],(case,lang,entries)
                before_doc,after_doc=Document(old.with_suffix('.docx')),Document(new.with_suffix('.docx'))
                projected,counts=expected_blocks(body(before_doc),entries)
                assert [xml(n) for n in projected]==[xml(n) for n in body(after_doc)],'Unexpected Word body change'
                links=lambda d:sorted(r.target_ref for r in d.part.rels.values() if r.is_external)
                assert links(before_doc)==links(after_doc)
                row['changed_q9_labels']=counts['styled_labels'];row['joined_q9_flag_pairs']=counts['joined_flag_pairs']
                with zipfile.ZipFile(old.with_suffix('.docx')) as x,zipfile.ZipFile(new.with_suffix('.docx')) as y:assert x.read('word/styles.xml')==y.read('word/styles.xml')
                preview=a.build/'word-preview'/(stem+'.pdf');row['word_pages']=inspect_preview(preview)
                row['prior_word_pages']=inspect_preview(prior/'word-preview'/(stem+'.pdf'))
                assert row['word_pages']<=row['prior_word_pages'],(case,lang,'Whole Word grew',row['prior_word_pages'],row['word_pages'])
                heading=soup.select_one('#q-ethical-issues h3').get_text();following=soup.select_one('#q-share-restrictions h3').get_text()
                for fmt,path in [('word',preview),('pdf',new.with_suffix('.pdf'))]:
                    pages=[v for v in subprocess.check_output(['pdftotext','-raw',str(path),'-'],text=True).split('\f') if v.strip()]
                    # Last flag on the same page bounds the whole short nested list;
                    # original order/first flags are independently protected by XML.
                    row['q9_'+fmt+'_pairs']=locations(pages,heading,following,[(n,f[-1]) for n,f in entries])
                    assert all(e['together'] for e in row['q9_'+fmt+'_pairs']),(case,lang,fmt,row['q9_'+fmt+'_pairs'])
                if case=='q9-long-purpose':
                    original=[compact(p.get_text()) for p in soup.select('#q-ethical-issues p') if 'Q9-PARA-' in p.get_text()]
                    assert len(original)==30
                    for path in [preview,new.with_suffix('.pdf')]:
                        text=compact(subprocess.check_output(['pdftotext','-raw',str(path),'-'],text=True))
                        assert all(v in text for v in original)
                    row['long_authored_paragraphs_retained']=30
                row['unchanged_question_html_pdf_and_word_text']=True
                row['prior_artifact_sha256']={str(old.with_suffix('.'+f)):sha(old.with_suffix('.'+f)) for f in ['html','pdf','docx','html.fixture.json']}
                for f in [new.with_suffix('.docx'),new.with_suffix('.docx.fixture.json'),preview]:row['artifact_sha256'][str(f.relative_to(a.build))]=sha(f)
                report['rows'].append(row)
                print(json.dumps({k:row[k] for k in ['case','language','pages','word_pages','changed_q9_labels','errors','reading_issues']}),flush=True)
            assert markers(soups[0])==markers(soups[1])
        report['selected_checks_passed']=len(report['rows'])==len(a.cases)*2 and all(not r['errors'] and not r['reading_issues'] for r in report['rows'])
    except Exception as error:
        report['failure']=str(error);raise
    finally:target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    assert report['selected_checks_passed'],'See preserved diagnostics'


if __name__=='__main__':main()
