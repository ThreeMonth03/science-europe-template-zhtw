"""0.3.24 native comparison: empty-Q15 panel only; no content or Word changes."""
import argparse
import json
from pathlib import Path
import sys
import zipfile
from bs4 import BeautifulSoup
from docx import Document
from artifact_utils import sha
from check_budget_outputs import body,xml,question_body
from check_budget_spacing_outputs import pdf_raw_page_texts
from check_word_rhythm_outputs import inspect_preview
from compare_runtime_outputs import markers

CASES=['empty','negative','personal-transfer-complete','partial','budget-long-no-currency']
NEW_BASELINES={'partial','budget-long-no-currency'}


def check_pages(case,language,before,after):
    if case=='empty':
        assert (before,after)==((4,3) if language=='chinese' else (4,4)),(case,language,before,after)
    else:assert before==after,(case,language,'Unexpected control pagination change',before,after)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['build','prior','extra-prior','english']:p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--cases',nargs='+',default=CASES);p.add_argument('--output',type=Path);a=p.parse_args()
    sys.path.insert(0,str(a.english.resolve()/'scripts'))
    from probe_empty_pdf import SELECTOR
    import check_missing_info_outputs as missing
    missing.HERE=a.english.resolve()
    target=a.output or a.build/'empty-pdf-report.json';assert not target.exists()
    report={'selected_checks_passed':False,'release_acceptance':False,'version':'0.3.24','rows':[],
        'checker_sha256':sha(Path(__file__)),'package_sha256':{n:sha(a.build/n) for n in ['english.zip','chinese.zip']},
        'limits':['Only the exact four-gap Q15 panel changes','LibreOffice preview, not Microsoft Word acceptance',
                  'Reviewed local Markdown-tables worker; stock-worker table issue remains a release gate']}
    try:
        for case in a.cases:
            soups=[]
            for language in ['english','chinese']:
                prior=a.extra_prior if case in NEW_BASELINES else a.prior
                stem=case+'-'+language;old=prior/'renders'/stem;new=a.build/'renders'/stem
                row,soup=missing.inspect(a.build,case,language);soups.append(soup)
                left=BeautifulSoup(old.with_suffix('.html').read_text(),'html.parser')
                assert len(left.select('.question'))==15
                assert [str(q) for q in left.select('.question')]==[str(q) for q in soup.select('.question')]
                row['panel_matches']=len(soup.select(SELECTOR));assert row['panel_matches']==int(case=='empty')
                for fmt in ['html','pdf','docx']:
                    before=json.loads(old.with_suffix('.'+fmt+'.fixture.json').read_text());after=json.loads(new.with_suffix('.'+fmt+'.fixture.json').read_text())
                    for key in ['recipe_sha256','events_sha256','km_sha256']:assert before[key]==after[key]
                    assert before['package_sha256']==sha(prior/(language+'.zip'))
                    assert after['package_sha256']==report['package_sha256'][language+'.zip']
                before_pages=pdf_raw_page_texts(old.with_suffix('.pdf'));after_pages=pdf_raw_page_texts(new.with_suffix('.pdf'))
                row['prior_pages']=len(before_pages);check_pages(case,language,row['prior_pages'],row['pages'])
                assert question_body(old.with_suffix('.pdf'),left)==question_body(new.with_suffix('.pdf'),soup),'PDF question text changed'
                if case!='empty':
                    first=lambda s:''.join(s.select_one('.question h3').get_text().split())
                    def strip_front(pages,heading):
                        index=next(i for i,text in enumerate(pages) if heading in text)
                        return [pages[index].split(heading,1)[1]]+pages[index+1:]
                    assert strip_front(before_pages,first(left))==strip_front(after_pages,first(soup))
                documents=[Document(f.with_suffix('.docx')) for f in [old,new]]
                assert [xml(n) for n in body(documents[0])]==[xml(n) for n in body(documents[1])],'Word body changed'
                links=lambda d:sorted(r.target_ref for r in d.part.rels.values() if r.is_external)
                assert links(documents[0])==links(documents[1])
                with zipfile.ZipFile(old.with_suffix('.docx')) as x,zipfile.ZipFile(new.with_suffix('.docx')) as y:
                    assert x.read('word/styles.xml')==y.read('word/styles.xml')
                preview=a.build/'word-preview'/(stem+'.pdf');old_preview=prior/'word-preview'/(stem+'.pdf')
                row['word_pages']=inspect_preview(preview);row['prior_word_pages']=inspect_preview(old_preview)
                assert row['word_pages']==row['prior_word_pages']
                row['exact_question_html_pdf_text_and_word_body']=True
                row['prior_artifact_sha256']={str(f):sha(f) for f in [old.with_suffix('.'+fmt+extra) for fmt in ['html','pdf','docx'] for extra in ['', '.fixture.json']]+[old_preview]}
                for f in [new.with_suffix('.docx'),new.with_suffix('.docx.fixture.json'),preview]:row['artifact_sha256'][str(f.relative_to(a.build))]=sha(f)
                report['rows'].append(row)
                print(json.dumps({k:row[k] for k in ['case','language','prior_pages','pages','word_pages','errors','reading_issues']}),flush=True)
            assert markers(soups[0])==markers(soups[1])
        report['selected_checks_passed']=len(report['rows'])==len(a.cases)*2 and all(not r['errors'] and not r['reading_issues'] for r in report['rows'])
    except Exception as e:
        report['failure']=str(e);raise
    finally:target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    assert report['selected_checks_passed'],'See preserved diagnostics'


if __name__=='__main__':main()
