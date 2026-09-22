"""Check a rejected diagnostic selector before proposing a layout fix.

Unconditional spacing below is intentionally diagnostic-only. It must never
be promoted without a conservative scope guard and mixed-content controls.
"""
import json,subprocess
import diagnose_empty as prior
import check

def main():
    original="selector='html body #dmp-content:has(> .dmp-section > .compact-empty-question):not(:has(> .dmp-section > .question:not(.compact-empty-question))) > .dmp-section'"
    assert prior.WORKER.count(original)==1
    worker=prior.WORKER.replace('next-empty-diagnostic','next-empty-selector-diagnostic')
    worker=worker.replace(original,"selector='html body #dmp-content > .dmp-section'")
    injection="""
 from cssselect2 import ElementWrapper,compile_selector_list
 tree=ElementWrapper.from_html_root(HTML(string=source).etree_element)
 candidates={
  'whole-document-descendant-chain': 'html body #dmp-content:has(> .dmp-section > .compact-empty-question):not(:has(> .dmp-section > .question:not(.compact-empty-question))) > .dmp-section',
  'per-section-guard': 'html body #dmp-content > .dmp-section:has(> .compact-empty-question):not(:has(> .question:not(.compact-empty-question)))',
  'unconditional-diagnostic-only': selector}
 matches={k:sum(compile_selector_list(v)[0].test(e) for e in tree.iter_subtree()) for k,v in candidates.items()}
"""
    worker=worker.replace(" assert source.count('</head>')==1",injection+" assert source.count('</head>')==1")
    worker=worker.replace("rows.append(dict(locale=locale,variant=name,", "rows.append(dict(locale=locale,variant=name,selector_matches=matches,")
    command=['docker','run','--rm','--network','none','--log-driver','none','--cap-drop','ALL',
        '--security-opt','no-new-privileges','--user','1000:1000',
        '-e','PYTHONPATH=/home/user/.local/lib/python3.13/site-packages','-e','XDG_CACHE_HOME=/tmp/private-cache',
        '--entrypoint','python','-v',str(prior.ROOT)+':/audit',prior.IMAGE,'-c',worker]
    subprocess.run(command,check=True,timeout=300)
    directory=prior.ROOT/'next-empty-selector-diagnostic';result=json.loads((directory/'engine.json').read_text())
    for locale in ['en','zh-Hant']:
        actual,_=check.pdf(prior.ROOT/'candidate/renders'/('EMPTY-'+locale+'-submission')/'document.pdf')
        control,text=check.pdf(directory/(locale+'-control.pdf'));assert actual==control
        for row in result['rows']:
            if row['locale']!=locale:continue
            import re
            _,parts=check.pdf(directory/row['pdf'])
            clean=lambda pages:''.join(re.sub(r'\d+/\d+$','',p) for p in pages)
            assert clean(text)==clean(parts)
            row['all_original_text_retained']=True
    result.update(diagnostic_only=True,source_integrated=False,release_acceptance=False,
        unguarded_spacing_is_not_a_candidate=True,mixed_or_long_document_cases_checked=False)
    with (directory/'checks.json').open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps([dict(locale=r['locale'],variant=r['variant'],pages=r['pages'],selector_matches=r['selector_matches']) for r in result['rows']]))
if __name__=='__main__':main()
