"""Same-fixture Q5 pagination: words retained, only scoped Word styles may change."""
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
from check_archive_gap_outputs import body_geometry
from check_budget_spacing_outputs import pdf_raw_page_texts,line_box_overlaps
from check_format_reading_outputs import verified_format_markers
from check_metadata_followup_outputs import CASES as METADATA_CASES
from check_narrative_outputs import compact
from check_short_budget_outputs import question_pages
from check_word_rhythm_outputs import assert_styles,inspect_preview
from check_word_short_budget_outputs import verify_preview_paragraphs

EXTRA=['storage-sharing','budget-long']
CASES=METADATA_CASES+EXTRA


def word_parts(doc):
    nodes=body(doc)
    headings={Paragraph(n,doc).text.split('. ',1)[0]:i for i,n in enumerate(nodes) if n.tag==qn('w:p') and Paragraph(n,doc).style.name=='Heading 3'}
    start,end=headings['5'],headings['6']
    return nodes[:start],nodes[start:end],nodes[end:]


def check_word(before,after,selected):
    from probe_storage_context import word_changes
    left,right=word_parts(before),word_parts(after)
    for i in [0,2]:assert list(map(xml,left[i]))==list(map(xml,right[i])),'Word changed outside Q5'
    changes=word_changes(*[[etree.tostring(n,encoding='unicode') for n in parts[1]] for parts in [left,right]],selected)
    assert xml(before.part.numbering_part.element)==xml(after.part.numbering_part.element)
    links=lambda d:sorted(r.target_ref for r in d.part.rels.values() if r.is_external)
    assert links(before)==links(after)
    return len(changes)


def locations(pdf,soup):
    q=soup.select_one('#q-store-backup');policy=q.select_one('.workspace-policy');limits=q.select_one('.storage-detail-limits')
    nodes=[q.h3,policy,limits.p]+limits.select('li')
    pages=[compact(p) for p in subprocess.check_output(['pdftotext','-layout',str(pdf),'-'],text=True).split('\f')[:-1]]
    found=[[i for i,p in enumerate(pages,1) if compact(n.get_text()) in p] for n in nodes]
    assert all(len(h)==1 for h in found),found
    return [h[0] for h in found]


def check_pdf(old,new,before,after,selected):
    snapshots=[]
    for file,soup in [(old,before),(new,after)]:
        pages=pdf_raw_page_texts(file);bbox=subprocess.check_output(['pdftotext','-bbox-layout',str(file),'-'])
        heading=compact(soup.select_one('.question h3').get_text())
        start=next(i for i,t in enumerate(pages) if heading in t)
        clean,markers=verified_format_markers(pages,bbox,soup,start)
        snapshots.append((''.join(question_pages(clean,soup)),markers,bbox))
    assert snapshots[0][:2]==snapshots[1][:2],'PDF body words, punctuation or generated list markers changed'
    if not selected:assert body_geometry(snapshots[0][2],before)==body_geometry(snapshots[1][2],after),'Fallback PDF geometry changed'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['build','prior','prior-extra','english']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--output',type=Path);a=p.parse_args();sys.path[:0]=[str(a.english.resolve()/n) for n in ['scripts','tests']]
    from storage_context_contract import compare
    import check_missing_info_outputs as missing
    missing.HERE=a.english.resolve()
    report=dict(selected_checks_passed=False,release_acceptance=False,rows=[],checker_sha256=sha(Path(__file__)),
                package_sha256={n:sha(a.build/n) for n in ['english.zip','chinese.zip']},
                limits=['Ten synthetic cases per language; not full Science Europe or full-DMP acceptance',
                        'LibreOffice previews are not Microsoft Word execution; long/complex Q5 bounds also tested in pinned engine fixtures'])
    target=a.output or a.build/'storage-context-report.json';assert not target.exists()
    try:
        for case in CASES:
            prior=a.prior_extra if case in EXTRA else a.prior
            for language in ['english','chinese']:
                stem=case+'-'+language;old=prior/'renders'/stem;new=a.build/'renders'/stem
                before=BeautifulSoup(old.with_suffix('.html').read_text(),'html.parser')
                row,after=missing.inspect(a.build,case,language)
                selected=compare(*[BeautifulSoup(str(s.select_one('#dmp-content')),'html.parser') for s in [before,after]])
                for fmt in ['html','pdf','docx']:
                    x,y=[json.loads(f.with_suffix('.'+fmt+'.fixture.json').read_text()) for f in [old,new]]
                    for k in ['recipe_sha256','events_sha256','km_sha256']:assert x[k]==y[k]
                    assert x['package_sha256']==sha(prior/(language+'.zip'))
                    assert y['package_sha256']==report['package_sha256'][language+'.zip']
                left,right=[Document(f.with_suffix('.docx')) for f in [old,new]]
                assert_styles(right);row['word_style_changes']=check_word(left,right,selected)
                with zipfile.ZipFile(old.with_suffix('.docx')) as x,zipfile.ZipFile(new.with_suffix('.docx')) as y:
                    for part in ['word/styles.xml','word/fontTable.xml']:assert x.read(part)==y.read(part)
                check_pdf(old.with_suffix('.pdf'),new.with_suffix('.pdf'),before,after,selected)
                row['prior_pages']=len(pdf_raw_page_texts(old.with_suffix('.pdf')))
                previews=[root/'word-preview'/(stem+'.pdf') for root in [prior,a.build]]
                row['prior_word_pages'],row['word_pages']=[inspect_preview(f) for f in previews]
                row['preview_paragraphs_checked']=verify_preview_paragraphs(right,previews[1],after)
                if selected:
                    row['q5_locations']={}
                    for kind,files in [('pdf',[old.with_suffix('.pdf'),new.with_suffix('.pdf')]),('word',previews)]:
                        left_pages,right_pages=[locations(f,s) for f,s in zip(files,[before,after])]
                        assert len(set(right_pages))==1,(case,language,kind,right_pages)
                        row['q5_locations'][kind]={'before':left_pages,'after':right_pages,'fixed_separation':len(set(left_pages))>1}
                else:
                    bboxes=[subprocess.check_output(['pdftotext','-bbox-layout',str(f),'-']) for f in previews]
                    assert body_geometry(bboxes[0],before)==body_geometry(bboxes[1],after),'Fallback preview geometry changed'
                row['font_box_overlaps']={kind:[line_box_overlaps(subprocess.check_output(['pdftotext','-bbox-layout',str(f),'-'])) for f in files] for kind,files in [('pdf',[old.with_suffix('.pdf'),new.with_suffix('.pdf')]),('word',previews)]}
                assert not row['errors'] and not row['reading_issues'],row
                assert row['pages']<=row['prior_pages'] and row['word_pages']<=row['prior_word_pages'],'Page count increased'
                row.update(eligible=selected,passed=True,prior_root=str(prior))
                for key,root,base,preview in [('before_sha256',prior,old,previews[0]),('after_sha256',a.build,new,previews[1])]:
                    row[key]={str(f.relative_to(root)):sha(f) for f in [base.with_suffix('.'+fmt+extra) for fmt in ['html','pdf','docx'] for extra in ['', '.fixture.json']]+[preview]}
                report['rows'].append(row)
                print(json.dumps({k:row[k] for k in ['case','language','eligible','pages','word_pages','word_style_changes']}),flush=True)
        report['selected_checks_passed']=True
    except Exception as error:report['failure']=repr(error);raise
    finally:target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':main()
