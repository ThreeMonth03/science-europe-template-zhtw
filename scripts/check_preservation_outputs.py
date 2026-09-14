"""Check native Q11 answer retention, scope and exact bounded prior comparisons."""
import argparse
from collections import Counter
import copy
import json
from pathlib import Path
from bs4 import BeautifulSoup
from docx import Document
from check_narrative_outputs import compact, page_bounds, pdf_text, sha
from check_polish_outputs import canonical_word_dates, assert_quantity_lines
from check_sharing_outputs import direct_runs
from compare_runtime_outputs import markers


def compare_prior(old, new):
    # The old synthetic cases have none of the newly mapped replies. Only the
    # explicit Q11 selection-review notice is expected to be added to them.
    current = copy.deepcopy(new)
    for node in current.select('#q-data-preservation [data-fact-id="preservation-selection-review"]'): node.decompose()
    assert markers(old)==markers(current), 'Unexpected prior fact-marker change'
    count=0
    for question in old.select('.question'):
        other=current.find(id=question['id'])
        assert other is not None and compact(question.get_text())==compact(other.get_text()), (question['id'],'Unexpected prior text change')
        assert [compact(n.get_text()) for n in question.select('.answer-detail')]==[compact(n.get_text()) for n in other.select('.answer-detail')], 'Prior authored block changed'
        count+=1
    assert count==15
    return count


def inspect(build, prior, case, language):
    base=build/'renders'/f'{case}-{language}'
    soup=BeautifulSoup(base.with_suffix('.html').read_text(),'html.parser')
    q=soup.find(id='q-data-preservation')
    paragraphs=[canonical_word_dates(soup,p.text) for p in Document(base.with_suffix('.docx')).paragraphs]
    pdf=pdf_text(base.with_suffix('.pdf'))
    assert not q.select('p p, p div, p ul, p table')
    for node in q.select('p,li'):
        expected=compact(node.get_text())
        assert expected in compact(pdf) and expected in compact(''.join(paragraphs)), (case,language,'Q11 text lost',node.get_text())
    authored=[compact(n.get_text()) for n in q.select('.answer-detail > p')]
    available=Counter(compact(p) for p in paragraphs)
    assert all(available[t]>=n for t,n in Counter(authored).items()), 'Authored paragraph lost or merged'
    for node in q.select('p.data-gap'):
        assert compact(node.get_text()) in available, ('Gap merged',node.get_text())
    archive=q.select_one('.post-project-archive')
    joined=0
    if archive:
        assert len(q.select('.post-project-archive'))==1 and archive['data-scope']=='project'
        assert not archive.find_parent(class_='dataset-section'), 'Project-level archive attached to a dataset'
        for run in direct_runs(archive.select_one('.dataset-policy')):
            assert compact(''.join(run)) in available, ('Owned archive prose not one Word paragraph',run)
            joined+=len(run)>1
        quantities=[node.get_text() for node in archive.select('.quantity')]
        for quantity in quantities:
            assert '\xa0' in quantity and any(quantity in p for p in paragraphs), 'Archive quantity lost nonbreaking space'
        assert_quantity_lines(base.with_suffix('.pdf'),quantities)
        preview=build/'word-preview'/(base.name+'.pdf')
        if preview.exists(): assert_quantity_lines(preview,quantities)
    if case.startswith('preservation-'):
        assert len(q.select('.dataset-section'))==2
        assert q.select_one('[data-fact-id="preservation-selection-review"][data-status="needs-review"]')
        assert 'Selection-2027-12-31.csv' in pdf and any('Selection-2027-12-31.csv' in p for p in paragraphs)
        assert len(q.select('[data-fact-id="preservation-dataset-description"]'))==2
        assert len(q.select('[data-fact-id="preservation-data-stage"]'))==2
        assert len(q.select('[data-fact-id="preservation-related-paper"]'))==1
        assert ('This dataset will not be published.' if language=='english' else '此資料集將不公開發布。') in q.get_text()
        if case=='preservation-partial':
            for fact in ['nonpublication-reason','archive-payer','archive-minimum-period','archive-extension-authority','archive-extension-basis','archive-format-migration']:
                assert q.select_one(f'[data-fact-id="{fact}"][data-status="missing"]'), (case,fact)
            assert q.select_one('[data-fact-id="archive-media-migration"][data-status="explicit-no"]')
        elif case=='preservation-no-cold':
            assert archive.select_one('[data-fact-id="post-project-archive"][data-status="explicit-no"]')
            assert not archive.select('[data-fact-id="archive-payer"], [data-fact-id="archive-minimum-period"]')
        elif case=='preservation-custom':
            assert q.select_one('.answer-detail[data-fact-id="archive-minimum-period"]')
            assert q.select_one('[data-fact-id="archive-extension"][data-status="explicit-no"]')
            assert q.select_one('[data-fact-id="archive-extension-limit"][data-status="complete"]')
        else:
            for fact in ['actual-use','predicted-use','budget']:
                assert q.select_one(f'[data-fact-id="archive-extension-{fact}"][data-status="complete"]')
    comparisons=0
    if prior and (old:=prior/'renders'/(base.name+'.html')).exists():
        comparisons=compare_prior(BeautifulSoup(old.read_text(),'html.parser'),soup)
    row={'case':case,'language':language,'passed':True,'q11_fact_nodes':len(q.select('[data-fact-id]')),
         'separate_authored_paragraphs':len(authored),'joined_archive_runs':joined,
         'controlled_question_comparisons':comparisons,'pdf_pages':page_bounds(base.with_suffix('.pdf'))}
    preview=build/'word-preview'/(base.name+'.pdf')
    if preview.exists(): row['word_preview_pages']=page_bounds(preview)
    return soup,row


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build',type=Path,required=True)
    parser.add_argument('--prior',type=Path)
    parser.add_argument('--cases',nargs='+',required=True)
    args=parser.parse_args()
    report={'selected_checks_passed':False,'release_acceptance':False,'rows':[],
            'checker_sha256':sha(Path(__file__)),
            'helper_sha256':{n:sha(Path(__file__).with_name(n)) for n in ['check_narrative_outputs.py','check_polish_outputs.py','check_sharing_outputs.py','compare_runtime_outputs.py']},
            'package_sha256':{n:sha(args.build/n) for n in ['english.zip','chinese.zip']},
            'artifact_sha256':{str(p.relative_to(args.build)):sha(p) for folder in ['renders','word-preview'] for p in sorted((args.build/folder).glob('*')) if p.is_file()},
            'limits':['Selected synthetic Q11 paths only; not full SE coverage','The prior comparator is for old cases without newly mapped answers','LibreOffice preview is not Microsoft Word acceptance','Stock Markdown tables remain blocked']}
    target=args.build/'preservation-report.json'
    target.write_text(json.dumps(report,indent=2)+'\n')
    try:
        for case in args.cases:
            pair=[]
            for language in ['english','chinese']:
                soup,row=inspect(args.build,args.prior,case,language); pair.append(soup); report['rows'].append(row)
            assert markers(pair[0])==markers(pair[1]), 'Bilingual markers differ'
    except Exception as e:
        report['failure']=str(e); target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n'); raise
    report['selected_checks_passed']=True
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'passed':True,'pairs':len(report['rows']),'comparisons':sum(r['controlled_question_comparisons'] for r in report['rows'])}))


if __name__=='__main__': main()
