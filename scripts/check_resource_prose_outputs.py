"""Native 0.3.40/41 Q15 comparison; admit only the independently specified pair."""
import argparse
import copy
import json
from pathlib import Path
import sys
import zipfile
from bs4 import BeautifulSoup
from docx import Document
from lxml import etree as E
from artifact_utils import sha
from check_budget_outputs import body,xml
from check_short_resources_outputs import fonts,compare_text
from check_preservation_reading_outputs import hashes
from check_word_rhythm_outputs import compare_questions,assert_styles,inspect_preview
from check_word_short_budget_outputs import verify_preview_paragraphs
from check_budget_spacing_outputs import line_box_overlaps
from rehearse_profile_pdf import snapshot,prefix_geometry
from rehearse_profile_pagination import W,c14n,text,geometry,locate
from rehearse_resource_prose import join_html,join_word,word_prefix_geometry,SENTENCES


def characters(paragraph):
    """Permit Pandoc run segmentation, not new fields/formatting/content."""
    assert all(n.tag in (W+'pPr',W+'r') for n in paragraph)
    result=[]
    for run in paragraph.findall(W+'r'):
        assert not run.attrib and all(n.tag in (W+'rPr',W+'t') for n in run)
        props=run.find(W+'rPr');fmt=c14n(props) if props is not None else None
        for node in run.findall(W+'t'):
            assert set(node.attrib) <= {'{http://www.w3.org/XML/1998/namespace}space'}
            result.extend((char,fmt) for char in node.text or '')
    return result


def check_word(before,after,language,selected):
    expected,joined=join_word(before.element,language)
    assert joined==selected,'Native Word eligibility differs from owned HTML pair'
    left=body(DocumentRoot(expected,before));right=body(after)
    assert len(left)==len(right)
    first,endings=SENTENCES[language]
    possible=[first+(' ' if language=='english' else '')+last for last in endings]
    differences=0
    for old,new in zip(left,right):
        if xml(old)==xml(new):continue
        assert selected and old.tag==new.tag==W+'p' and text(old) in possible
        assert old.attrib==new.attrib
        assert c14n(old.find(W+'pPr'))==c14n(new.find(W+'pPr')),'Joined paragraph style changed'
        assert characters(old)==characters(new),'Joined character formatting changed'
        differences+=1
    assert differences<=int(selected)
    links=lambda d:sorted(r.target_ref for r in d.part.rels.values() if r.is_external)
    assert links(before)==links(after)
    return dict(joined=joined,exact_body_outside_pair=True,character_formatting_preserved=True)


class DocumentRoot:
    # body() uses only element and Paragraph construction; retaining the original
    # part avoids losing style context while comparing a non-mutating XML copy.
    def __init__(self,element,original):self.element=element;self.part=original.part


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('build','prior','english','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--cases',nargs='+',default=['profile-partial','empty','budget-long-no-currency','budget-many'])
    a=p.parse_args();assert not a.output.exists()
    sys.path.insert(0,str(a.english.resolve()/'scripts'))
    from short_resources_contract import eligible
    report=dict(selected_checks_passed=False,release_acceptance=False,microsoft_word_acceptance=False,version='0.3.41',
        native_export=True,rows=[],checker_sha256=sha(Path(__file__)),
        helper_sha256={n:sha(Path(__file__).with_name(n)) for n in ['artifact_utils.py','check_budget_outputs.py',
            'check_short_resources_outputs.py','check_preservation_reading_outputs.py','check_word_rhythm_outputs.py',
            'check_word_short_budget_outputs.py','check_budget_spacing_outputs.py','rehearse_profile_pdf.py',
            'rehearse_profile_pagination.py','rehearse_resource_prose.py','inspect_resource_punctuation.py']},
        contract_sha256=sha(a.english/'scripts/resource_prose_contract.py'),
        package_sha256={n:sha(a.build/n) for n in ('english.zip','chinese.zip')},
        prior_package_sha256={n:sha(a.prior/n) for n in ('english.zip','chinese.zip')},
        limits=['Public synthetic controls, not arbitrary real projects','Native tables-only worker, no font patch',
                'LibreOffice previews, not Microsoft Word acceptance','No new optional-notice scope'])
    try:
        for case in a.cases:
            for profile in ('review','submission'):
                for language in ('english','chinese'):
                    stem=case+'-'+profile+'-'+language
                    old,new=[folder/'renders'/stem for folder in (a.prior,a.build)]
                    for fmt in ('html','pdf','docx'):
                        receipts=[json.loads(path.with_suffix('.'+fmt+'.fixture.json').read_text()) for path in (old,new)]
                        for key in ('recipe_sha256','events_sha256','km_sha256'):assert receipts[0][key]==receipts[1][key],(stem,fmt,key)
                        assert receipts[0]['package_sha256']==report['prior_package_sha256'][language+'.zip']
                        assert receipts[1]['package_sha256']==report['package_sha256'][language+'.zip']
                    originals=[path.with_suffix('.html').read_text() for path in (old,new)]
                    expected,selected=join_html(originals[0],language)
                    assert selected==(case!='empty')
                    soups=[BeautifulSoup(value,'html.parser') for value in originals]
                    # Cover build/version provenance legitimately changes. The
                    # whole 15-question DOM must match the independent oracle.
                    count=compare_questions(BeautifulSoup(expected,'html.parser'),soups[1])
                    q=soups[1].select_one('#q-required-resources')
                    assert eligible(q)==(case=='profile-partial')
                    docs=[Document(path.with_suffix('.docx')) for path in (old,new)]
                    assert_styles(docs[1]);word=check_word(*docs,language,selected)
                    with zipfile.ZipFile(old.with_suffix('.docx')) as x,zipfile.ZipFile(new.with_suffix('.docx')) as y:
                        for part in ('word/styles.xml','word/fontTable.xml','word/numbering.xml'):assert x.read(part)==y.read(part),part
                    row=dict(case=case,profile=profile,language=language,selected=selected,question_comparisons=count,word=word,
                        artifact_sha256=hashes(a.build,stem),prior_artifact_sha256=hashes(a.prior,stem),formats={})
                    for fmt,paths,prefix in [('pdf',[v.with_suffix('.pdf') for v in (old,new)],prefix_geometry),
                            ('word',[folder/'word-preview'/(stem+'.pdf') for folder in (a.prior,a.build)],word_prefix_geometry)]:
                        snapshots=[snapshot(path) for path in paths]
                        pages=[s[0] for s in snapshots];boxes=[s[1] for s in snapshots]
                        compare_text(pages[0][1:],pages[1][1:],soups[1])
                        assert len(pages[0])==len(pages[1]),(stem,fmt,'Page count changed')
                        font_pair=[fonts(path) for path in paths];assert font_pair[0]==font_pair[1],(stem,fmt,'Fonts changed',font_pair)
                        # Ignore only the known provenance-bearing cover page.
                        prefix_pair=[[r for r in prefix(b) if r[0]>1] for b in boxes]
                        assert prefix_pair[0]==prefix_pair[1],(stem,fmt,'Non-Q15 body moved')
                        overlaps=[line_box_overlaps(b) for b in boxes]
                        assert overlaps[0]==overlaps[1],(stem,fmt,'Line overlap changed',overlaps)
                        if not selected:assert geometry(paths[0])[1:]==geometry(paths[1])[1:],(stem,fmt,'Fallback moved')
                        values=[q.h3.get_text(),q.h4.get_text()] if case=='profile-partial' else [q.h3.get_text()]
                        positions=[locate(path,values)[1] for path in paths]
                        if case=='profile-partial':
                            assert positions[1]==[6,6],(stem,fmt,'Short Q15 remains split',positions)
                            if language=='chinese' and profile=='submission' and fmt=='word':assert positions[0]==[5,6]
                        row['formats'][fmt]=dict(prior_pages=len(pages[0]),pages=len(pages[1]),font_inventory=font_pair[1],
                            prior_heading_pages=positions[0],heading_pages=positions[1],prefix_body_geometry_unchanged=True,
                            prior_line_overlaps=overlaps[0],line_overlaps=overlaps[1])
                    preview=a.build/'word-preview'/(stem+'.pdf')
                    row['word_preview_paragraphs_checked']=verify_preview_paragraphs(docs[1],preview,soups[1])
                    inspect_preview(preview);row['passed']=True;report['rows'].append(row)
                    print(json.dumps(dict(stem=stem,joined=selected,passed=True)),flush=True)
        report['selected_checks_passed']=len(report['rows'])==len(a.cases)*4
    except Exception as error:report['failure']=repr(error);raise
    finally:a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':main()
