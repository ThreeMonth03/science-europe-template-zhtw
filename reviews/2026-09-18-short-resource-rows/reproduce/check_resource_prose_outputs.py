"""Native 0.3.40/41 Q15 comparison; admit only the independently specified pair."""
import argparse
import copy
import json
from pathlib import Path
import sys
import zipfile
from collections import Counter
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


def expected_word(before,language):
    candidate=copy.deepcopy(before.element)
    nodes=list(candidate.find(W+'body'));first,endings=SENTENCES[language]
    headings=[i for i,n in enumerate(nodes) if n.tag==W+'p' and text(n).startswith('15. ')]
    assert len(headings)==1
    for a,b in zip(nodes[headings[0]+1:],nodes[headings[0]+2:]):
        if a.tag!=W+'p' or b.tag!=W+'p' or text(a)!=first or text(b) not in endings:continue
        # Long budgets use Pandoc's FirstParagraph/BodyText pair instead of two
        # PilotLead paragraphs. Accept only these exact aliases with identical
        # actual reference paragraph AND run settings, not arbitrary styles.
        props=[n.find(W+'pPr') for n in (a,b)]
        if any(v is None for v in props):continue
        styles=[v.find(W+'pStyle') for v in props]
        if any(v is None for v in styles):continue
        if [v.get(W+'val') for v in styles]==['FirstParagraph','BodyText']:
            assert all(len(v)==1 and not v.attrib for v in props)
            first_style,body_style=[before.styles[n].element for n in ('First Paragraph','Body Text')]
            assert first_style.find(W+'basedOn').get(W+'val')=='BodyText'
            for name in ('pPr','rPr'):
                pair=[style.find(W+name) for style in (first_style,body_style)]
                assert all(v is not None for v in pair) and c14n(pair[0])==c14n(pair[1]),'Reference aliases differ'
            # Only the paragraph that will be removed is normalized for the
            # independent reversible trial oracle. First paragraph stays intact.
            styles[1].set(W+'val','FirstParagraph')
    return join_word(candidate,language)


def check_word(before,after,language,selected):
    expected,joined=expected_word(before,language)
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


def continuation_headers(pages,soup,case):
    """Remove only this fixture's exact repeated identity at continuation tops.

    Keep the first in-body identity and all authored text. Compaction can move
    a paragraph across a repeated header without changing a single answer.
    """
    if case not in ('budget-long-no-currency','budget-many'):return pages,[]
    compact=lambda s:''.join(s.split())
    q=soup.select_one('#q-required-resources');table=q.select_one('.resource-table')
    cells=table.tbody.tr.find_all('td',recursive=False);assert len(cells)==3
    title=cells[0].find('p',recursive=False).get_text()
    identity=compact(table.thead.get_text()+(title+cells[1].get_text()+cells[2].get_text() if case=='budget-long-no-currency' else ''))
    assert identity and all(identity not in compact(n.get_text()) for n in q.select('.answer-detail'))
    headings=[i for i,page in enumerate(pages) if compact(q.h3.get_text()) in page];assert len(headings)==1
    result=list(pages);removed=[]
    first=[i for i in range(headings[0],len(pages)) if identity in pages[i]]
    assert first,'First resource identity missing'
    # A long, breakable Q15 may place its first table below the heading page.
    # That first real identity is always retained, even at a page top.
    for i in range(first[0]+1,len(pages)):
        if result[i].startswith(identity):
            result[i]=result[i][len(identity):];removed.append(i+1)
    if case=='budget-long-no-currency':assert removed,'Long fixture must have continuation headers'
    return result,removed


def canonical_many_rows(pages,soup):
    """Fixture-specific cell oracle: page splitting may reorder painting of cells.

    Consume every exact paragraph once within its unique row boundaries; keep
    purpose paragraphs in order. Never normalize arbitrary authored prose.
    """
    compact=lambda s:''.join(s.split())
    markers={'•','◦','\uf0b7','\uf0a1'}
    assert not markers.intersection(soup.get_text())
    whole=''.join(c for c in ''.join(pages[1:]) if c not in markers)
    tables=soup.select('#q-required-resources .resource-table');assert len(tables)==1
    rows=tables[0].tbody.find_all('tr',recursive=False);assert len(rows)==8
    titles=[compact(r.find('td').find('p',recursive=False).get_text()) for r in rows]
    assert len(set(titles))==8 and all(whole.count(t)==1 for t in titles),'Ambiguous resource row identity'
    positions=[whole.index(t) for t in titles];assert positions==sorted(positions)
    canonical=whole[:positions[0]]
    for i,(row,title) in enumerate(zip(rows,titles)):
        cells=row.find_all('td',recursive=False);assert len(cells)==3
        paragraphs=[[compact(p.get_text()) for p in cell.find_all('p')] for cell in cells]
        assert all(''.join(ps)==compact(cell.get_text()) for ps,cell in zip(paragraphs,cells))
        assert paragraphs[0][0]==title and len(paragraphs[1])==len(paragraphs[2])==1
        tokens=paragraphs[0][1:]+paragraphs[1]+paragraphs[2]
        assert all(tokens) and len(tokens)==len(set(tokens))
        value=whole[positions[i]+len(title):positions[i+1] if i+1<len(rows) else len(whole)]
        pending=list(range(len(tokens)));seen=[]
        while value:
            hits=[n for n in pending if value.startswith(tokens[n])]
            assert len(hits)==1,(title,'Missing, duplicated, changed or wrong-row PDF cell text',value[:100])
            n=hits[0];value=value[len(tokens[n]):];pending.remove(n);seen.append(n)
        assert not pending,(title,'PDF cell text lost')
        purpose=[n for n in seen if n<len(paragraphs[0])-1]
        assert purpose==sorted(purpose),(title,'Purpose order changed')
        canonical+=title+''.join(tokens)
    return [canonical]


def compare_native_text(pages,soup,case):
    projected=[continuation_headers(values,soup,case) for values in pages]
    assert projected[0][1]==projected[1][1],'Repeated header pages changed'
    if case=='budget-many':
        markers={'•','◦','\uf0b7','\uf0a1'}
        assert Counter(c for c in ''.join(pages[0]) if c in markers)==Counter(c for c in ''.join(pages[1]) if c in markers)
        normalized=[canonical_many_rows(value[0],soup) for value in projected]
    else:normalized=[value[0][1:] for value in projected]
    compare_text(*normalized,soup)
    return projected[1][1]


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
                        header_pages=compare_native_text(pages,soups[1],case)
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
                            verified_continuation_header_pages=header_pages,
                            exact_many_row_cells_checked=8 if case=='budget-many' else 0,
                            prior_line_overlaps=overlaps[0],line_overlaps=overlaps[1])
                    preview=a.build/'word-preview'/(stem+'.pdf')
                    row['word_preview_paragraphs_checked']=verify_preview_paragraphs(docs[1],preview,soups[1])
                    inspect_preview(preview);row['passed']=True;report['rows'].append(row)
                    print(json.dumps(dict(stem=stem,joined=selected,passed=True)),flush=True)
        report['selected_checks_passed']=len(report['rows'])==len(a.cases)*4
    except Exception as error:report['failure']=repr(error);raise
    finally:a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':main()
