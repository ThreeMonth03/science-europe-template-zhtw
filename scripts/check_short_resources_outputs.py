"""Exact native PDF Q15 keep scope; HTML, Word and rejected PDF controls stay put."""
import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys
import zipfile
from bs4 import BeautifulSoup
from docx import Document
from artifact_utils import sha
from check_budget_outputs import body, xml
from check_word_rhythm_outputs import compare_questions, assert_styles, inspect_preview
from check_word_short_budget_outputs import verify_preview_paragraphs
from rehearse_profile_pagination import geometry
from rehearse_profile_pdf import snapshot, prefix_geometry
from check_budget_spacing_outputs import line_box_overlaps
from check_preservation_reading_outputs import hashes


def compare_text(before, after, soup):
    markers = {'•','◦','\uf0b7','\uf0a1'}
    assert not markers.intersection(soup.get_text()), 'Authored bullet characters need an independent oracle'
    left,right = ''.join(before),''.join(after)
    assert Counter(c for c in left if c in markers) == Counter(c for c in right if c in markers)
    assert ''.join(c for c in left if c not in markers) == ''.join(c for c in right if c not in markers), 'PDF text changed'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('build','prior-controls','prior-profile','english','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--cases',nargs='+',default=['profile-partial','empty','budget-long-no-currency','budget-many'],
        choices=['profile-partial','empty','budget-long-no-currency','budget-many'])
    a=p.parse_args();assert not a.output.exists() and len(a.cases)==len(set(a.cases))
    sys.path.insert(0,str(a.english.resolve()/'scripts'))
    from short_resources_contract import eligible
    report=dict(selected_checks_passed=False,release_acceptance=False,microsoft_word_acceptance=False,version='0.3.40',
        cases=a.cases,rows=[],checker_sha256=sha(Path(__file__)),
        helper_sha256={n:sha(Path(__file__).with_name(n)) for n in ['artifact_utils.py','check_budget_outputs.py','check_word_rhythm_outputs.py',
            'check_word_short_budget_outputs.py','rehearse_profile_pagination.py','rehearse_profile_pdf.py','check_budget_spacing_outputs.py','check_preservation_reading_outputs.py']},
        contract_sha256=sha(a.english/'scripts/short_resources_contract.py'),
        package_sha256={n:sha(a.build/n) for n in ('english.zip','chinese.zip')},
        limits=['Only selected public synthetic cases, not all DMPs',
            'HTML exports do not contain the PDF-entry hint; eligibility is independently inspected on their identical question DOM',
            'Outside list markers can change raw extraction order; preserve their counts and every other character',
            'LibreOffice preview, not Microsoft Word acceptance','Tables-only local worker; no experimental font patch'])
    try:
        for case in a.cases:
            prior = a.prior_profile if case in ('profile-partial','empty') else a.prior_controls
            packages={n:sha(prior/n) for n in ('english.zip','chinese.zip')}
            for profile in ('review','submission'):
                for language in ('english','chinese'):
                    stem=case+'-'+profile+'-'+language
                    old,new=[folder/'renders'/stem for folder in (prior,a.build)]
                    for fmt in ('html','pdf','docx'):
                        receipts=[json.loads(path.with_suffix('.'+fmt+'.fixture.json').read_text()) for path in (old,new)]
                        for key in ('recipe_sha256','events_sha256','km_sha256'):assert receipts[0][key]==receipts[1][key],(stem,fmt,key)
                        assert receipts[0]['package_sha256']==packages[language+'.zip']
                        assert receipts[1]['package_sha256']==report['package_sha256'][language+'.zip']
                    soups=[BeautifulSoup(path.with_suffix('.html').read_text(),'html.parser') for path in (old,new)]
                    count=compare_questions(*soups);assert not soups[1].select('.pdf-short-resources')
                    q=soups[1].select_one('#q-required-resources');selected=eligible(q)
                    assert selected==(case=='profile-partial'),(stem,'Unexpected eligibility')
                    docs=[Document(path.with_suffix('.docx')) for path in (old,new)]
                    assert_styles(docs[1]);assert [xml(n) for n in body(docs[0])]==[xml(n) for n in body(docs[1])],'Word body changed'
                    links=lambda d:sorted(r.target_ref for r in d.part.rels.values() if r.is_external)
                    assert links(docs[0])==links(docs[1])
                    with zipfile.ZipFile(old.with_suffix('.docx')) as x,zipfile.ZipFile(new.with_suffix('.docx')) as y:
                        for part in ('word/styles.xml','word/fontTable.xml','word/numbering.xml'):assert x.read(part)==y.read(part),part
                    previews=[folder/'word-preview'/(stem+'.pdf') for folder in (prior,a.build)]
                    assert geometry(previews[0])[1:]==geometry(previews[1])[1:],'Word body pagination changed'
                    word_pages=inspect_preview(previews[1])
                    paragraphs=verify_preview_paragraphs(docs[1],previews[1],soups[1])
                    snapshots=[snapshot(path.with_suffix('.pdf')) for path in (old,new)]
                    before,after=[s[0] for s in snapshots];before_box,after_box=[s[1] for s in snapshots]
                    compare_text(before,after,soups[1]);assert len(before)==len(after),(stem,'PDF page count changed')
                    assert line_box_overlaps(before_box)==line_box_overlaps(after_box),(stem,'New PDF line-box overlaps')
                    row=dict(case=case,profile=profile,language=language,selected=selected,question_comparisons=count,
                        pdf_pages=len(after),word_pages=word_pages,word_preview_paragraphs_checked=paragraphs,
                        exact_word_body_unchanged=True,word_body_geometry_unchanged=True,prior_package_sha256=packages,
                        prior_artifact_sha256=hashes(prior,stem),artifact_sha256=hashes(a.build,stem),
                        prior_pdf_line_box_overlaps=line_box_overlaps(before_box),pdf_line_box_overlaps=line_box_overlaps(after_box))
                    if selected:
                        assert prefix_geometry(before_box)==prefix_geometry(after_box),'Non-Q15 PDF geometry changed'
                        values=[q.h3.get_text(),q.select_one('.resource-table tbody').get_text()]
                        compact=lambda s:''.join(s.split())
                        positions=lambda pages:[[i for i,page in enumerate(pages,1) if compact(value) in page] for value in values]
                        row['prior_q15_heading_table_pages']=positions(before);row['q15_heading_table_pages']=positions(after)
                        assert all(len(v)==1 for v in row['q15_heading_table_pages'])
                        assert row['q15_heading_table_pages'][0]==row['q15_heading_table_pages'][1],(stem,'Q15 still split')
                        if (language,profile)==('chinese','submission'):
                            assert row['prior_q15_heading_table_pages']==[[5],[6]]
                            assert row['q15_heading_table_pages']==[[6],[6]]
                        row['prefix_geometry_unchanged']=True
                    else:
                        assert geometry(old.with_suffix('.pdf'))[1:]==geometry(new.with_suffix('.pdf'))[1:],(stem,'Rejected PDF changed')
                        row['whole_pdf_body_geometry_unchanged']=True
                    row['passed']=True;report['rows'].append(row)
                    print(json.dumps({k:row[k] for k in ('case','profile','language','selected','pdf_pages','word_pages')}),flush=True)
        report['selected_checks_passed']=len(report['rows'])==len(a.cases)*4
    except Exception as error:report['failure']=repr(error);raise
    finally:a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':main()
