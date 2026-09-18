"""Native 0.3.41/42: PDF row pagination only; HTML and editable Word unchanged."""
import argparse
import json
from pathlib import Path
import sys
import zipfile
from bs4 import BeautifulSoup
from docx import Document
from artifact_utils import sha
from check_budget_outputs import body,xml
from check_short_resources_outputs import fonts
from check_preservation_reading_outputs import hashes
from check_word_rhythm_outputs import compare_questions,assert_styles,inspect_preview
from check_word_short_budget_outputs import verify_preview_paragraphs
from check_budget_spacing_outputs import line_box_overlaps
from rehearse_profile_pdf import snapshot,prefix_geometry
from rehearse_profile_pagination import geometry
from rehearse_resource_prose import word_prefix_geometry
from check_resource_prose_outputs import compare_native_text,continuation_headers

HELPERS=['artifact_utils.py','check_budget_outputs.py','check_short_resources_outputs.py','check_preservation_reading_outputs.py',
         'check_word_rhythm_outputs.py','check_word_short_budget_outputs.py','check_budget_spacing_outputs.py',
         'rehearse_profile_pdf.py','rehearse_profile_pagination.py','rehearse_resource_prose.py','check_resource_prose_outputs.py']


def row_pages(pages,soup):
    """Assign complete paragraph tokens to the correct row before counting pages.

    Values repeated in several rows cannot satisfy another row: each unique
    title delimits its own window, and every exact cell paragraph is consumed.
    """
    pages,_=continuation_headers(pages,soup,'budget-many')
    markers={'•','◦','\uf0b7','\uf0a1'}
    compact=lambda s:''.join(s.split())
    values=[''.join(c for c in p if c not in markers) for p in pages[1:]]
    whole=''.join(values); locations=[n for n,p in enumerate(values,2) for _ in p]
    rows=soup.select_one('#q-required-resources .resource-table').tbody.find_all('tr',recursive=False)
    titles=[compact(row.td.p.get_text()) for row in rows]
    assert len(rows)==8 and len(set(titles))==8 and all(whole.count(t)==1 for t in titles)
    starts=[whole.index(t) for t in titles];assert starts==sorted(starts)
    result=[]
    for n,(row,start) in enumerate(zip(rows,starts)):
        stop=starts[n+1] if n+1<len(starts) else len(whole)
        value=whole[start:stop]
        tokens=[compact(p.get_text()) for p in row.find_all('p')]
        assert all(tokens) and len(set(tokens))==len(tokens)
        assert value.startswith(tokens[0]);pending=list(tokens);position=start;found=[]
        while value:
            hits=[t for t in pending if value.startswith(t)];assert len(hits)==1,'Missing, duplicated or wrong-row paragraph'
            token=hits[0];found.append((token,position));position+=len(token);value=value[len(token):];pending.remove(token)
        assert not pending
        purpose=[compact(p.get_text()) for p in row.td.find_all('p')]
        assert [t for t,_ in found if t in purpose]==purpose,'Purpose paragraph order changed'
        result.append(dict(index=n+1,identity=row['data-item-id'],pages=sorted(set(locations[start:stop])),paragraph_count=len(tokens)))
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('build','prior','english','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();assert not a.output.exists();sys.path.insert(0,str(a.english.resolve()/'scripts'))
    from short_resource_rows_contract import eligible,row_fragments
    report=dict(selected_checks_passed=False,release_acceptance=False,microsoft_word_acceptance=False,version='0.3.42',native_export=True,rows=[],
        checker_sha256=sha(Path(__file__)),helper_sha256={n:sha(Path(__file__).with_name(n)) for n in HELPERS},
        contract_sha256=sha(a.english/'scripts/short_resource_rows_contract.py'),
        package_sha256={n:sha(a.build/n) for n in ['english.zip','chinese.zip']},
        prior_package_sha256={n:sha(a.prior/n) for n in ['english.zip','chinese.zip']},
        limits=['Public synthetic fixtures only','Word previews use LibreOffice, not Microsoft Word',
                'No additional missing-notice suppression','Long and unsupported PDF rows keep prior behavior'])
    try:
        for case in ['profile-partial','empty','budget-long-no-currency','budget-many']:
            for profile in ['review','submission']:
                for language in ['english','chinese']:
                    stem='-'.join([case,profile,language]);old,new=[folder/'renders'/stem for folder in [a.prior,a.build]]
                    for fmt in ['html','pdf','docx']:
                        receipts=[json.loads(v.with_suffix('.'+fmt+'.fixture.json').read_text()) for v in [old,new]]
                        for key in ['recipe_sha256','events_sha256','km_sha256']:assert receipts[0][key]==receipts[1][key],(stem,fmt,key)
                        for receipt,key in zip(receipts,['prior_package_sha256','package_sha256']):assert receipt['package_sha256']==report[key][language+'.zip']
                    soups=[BeautifulSoup(v.with_suffix('.html').read_text(),'html.parser') for v in [old,new]]
                    count=compare_questions(*soups);assert count==15
                    docs=[Document(v.with_suffix('.docx')) for v in [old,new]]
                    assert [xml(v) for v in body(docs[0])]==[xml(v) for v in body(docs[1])],(stem,'Word body changed')
                    links=lambda doc:sorted(r.target_ref for r in doc.part.rels.values() if r.is_external)
                    assert links(docs[0])==links(docs[1]);assert_styles(docs[1])
                    with zipfile.ZipFile(old.with_suffix('.docx')) as x,zipfile.ZipFile(new.with_suffix('.docx')) as y:
                        for part in ['word/styles.xml','word/fontTable.xml','word/numbering.xml']:assert x.read(part)==y.read(part)
                    row=dict(case=case,profile=profile,language=language,selected=case=='budget-many',question_comparisons=count,
                        exact_word_body=True,artifact_sha256=hashes(a.build,stem),prior_artifact_sha256=hashes(a.prior,stem),formats={})
                    if case=='budget-many':
                        rs=soups[1].select('#q-required-resources .resource-table tbody > tr');assert len(rs)==8
                        assert all(eligible(row_fragments(r)) for r in rs),'Native row outside bounded grammar'
                    for fmt,paths,prefix in [('pdf',[v.with_suffix('.pdf') for v in [old,new]],prefix_geometry),
                            ('word',[folder/'word-preview'/(stem+'.pdf') for folder in [a.prior,a.build]],word_prefix_geometry)]:
                        snapshots=[snapshot(path) for path in paths];pages=[s[0] for s in snapshots];boxes=[s[1] for s in snapshots]
                        headers=compare_native_text(pages,soups[1],case)
                        assert len(pages[0])==len(pages[1]),(stem,fmt,'Page count changed')
                        assert fonts(paths[0])==fonts(paths[1]),(stem,fmt,'Fonts changed')
                        prefixes=[[r for r in prefix(b) if r[0]>1] for b in boxes];assert prefixes[0]==prefixes[1],(stem,fmt,'Non-Q15 body moved')
                        overlaps=[line_box_overlaps(b) for b in boxes];assert overlaps[0]==overlaps[1],(stem,fmt,'Overlap records changed')
                        if fmt=='word' or not row['selected']:assert geometry(paths[0])[1:]==geometry(paths[1])[1:],(stem,fmt,'Control body geometry changed')
                        values=dict(prior_pages=len(pages[0]),pages=len(pages[1]),font_inventory=fonts(paths[1]),prefix_body_geometry_unchanged=True,
                            full_body_geometry_unchanged=fmt=='word' or not row['selected'],verified_continuation_header_pages=headers,
                            prior_line_overlaps=overlaps[0],line_overlaps=overlaps[1])
                        if case=='budget-many':
                            before,after=[row_pages(v,soups[1]) for v in pages]
                            if fmt=='pdf':
                                assert all(len(r['pages'])==1 for r in after),(stem,'Short row remains split')
                                if language=='english':assert before[6]['pages']==[8,9] and after[6]['pages']==[9],(stem,before[6],after[6])
                            values.update(prior_rows=before,rows=after)
                        row['formats'][fmt]=values
                    preview=a.build/'word-preview'/(stem+'.pdf')
                    row['word_preview_paragraphs_checked']=verify_preview_paragraphs(docs[1],preview,soups[1]);inspect_preview(preview)
                    row['passed']=True;report['rows'].append(row);print(json.dumps(dict(stem=stem,passed=True)),flush=True)
        report['selected_checks_passed']=len(report['rows'])==16
    except Exception as error:report['failure']=repr(error);raise
    finally:a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':main()
