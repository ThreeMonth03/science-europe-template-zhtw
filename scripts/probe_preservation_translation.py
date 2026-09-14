"""Check selected Q11 branch semantics against reviewed phrases in both generated languages."""
import argparse
import copy
import itertools
import json
import sys
from pathlib import Path
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from artifact_utils import sha
from check_paper_outputs import check_paper_flow

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--english', type=Path, required=True)
    args = parser.parse_args()
    sys.path[:0] = [str(args.english.resolve() / f) for f in ('tests','scripts')]
    import test_science_europe_contract as adapter
    from test_preservation_coverage import archive_matrix, plain, AUTHORED
    from generate_pilot_fixtures import IDS, path
    from generate_preservation_fixtures import preservation_cases
    phrases = json.loads((ROOT / 'docs/readability-phrases.json').read_text())
    cases = [r for r,_,_ in archive_matrix()] + [plain(c) for c in preservation_cases('en')]
    base = plain(); ap = path('preservingCUuid','archivedAfterQUuid','archivedAfterYesAUuid')
    for field, choices in [
        ('archivedAfterFormatsQUuid',['archivedAfterFormatsNoAUuid','archivedAfterFormatsYesAUuid']),
        ('archivedAfterMediaQUuid',['archivedAfterMediaNoAUuid','archivedAfterMediaYesAUuid']),
        ('archivedAfterExtendQUuid',['archivedAfterExtendNoAUuid','archivedAfterExtendYesAUuid']),
        ('notPublishedReasonQUuid',[f'notPublishedReason{n}AUuid' for n in ['Raw','Results','Intermediate','NoReuse','Cost','Lost','Other']]),
        ('producedDataStageQUuid',[f'producedDataStage{n}AUuid' for n in ['Raw','Intermediate','Unpublishable','Published']])]:
        key = next(p for p in base if p.endswith(IDS[field]))
        for choice in [None]+choices:
            replies = copy.deepcopy(base); replies[key] = IDS[choice] if choice else ''; cases.append(replies)
    basis = path(ap,'archivedAfterExtendQUuid','archivedAfterExtendYesAUuid','archivedAfterExtendBasisQUuid')
    for flags in itertools.product([False,True],repeat=3):
        replies=copy.deepcopy(base)
        replies[basis]=[IDS[f'archivedAfterExtendBasis{n}ChoiceUuid'] for n,f in zip(['Actual','Predicted','Budget'],flags) if f]
        cases.append(replies)
    # Exercise both authorities and both non-extension limits, beyond the fixture choices.
    for field, choice, parent in [('archivedAfterExtendWhoQUuid','archivedAfterExtendWhoPiAUuid','Yes'),
                                  ('archivedAfterExtendNoReasonQUuid','archivedAfterExtendNoBudgetAUuid','No')]:
        replies=plain('preservation-complete' if parent=='Yes' else 'preservation-custom')
        replies[path(ap,'archivedAfterExtendQUuid',f'archivedAfterExtend{parent}AUuid',field)] = IDS[choice]
        cases.append(replies)
    free=plain('preservation-custom')
    for name in ['producedDataDescriptionQUuid','notPublishedReasonOtherQUuid','archivedAfterPeriodOtherQUuid']:
        free[next(p for p in free if p.endswith(IDS[name]))] = AUTHORED
    cases.append(free)
    rendered=[]; checked_phrases=0
    for folder in ('en','translated'):
        env=Environment(loader=FileSystemLoader(args.build/folder),extensions=['jinja2.ext.do'])
        env.filters.update(reply_path=adapter.reply_path,reply_items=adapter.reply_items,reply_str_value=adapter.reply_str_value,markdown=lambda v:v)
        template=env.from_string("{% import 'src/macros.html.j2' as macros with context %}{% import 'src/uuids.j2' as uuids with context %}{% include 'src/questions/11-data-preservation.html.j2' %}")
        rendered.append([BeautifulSoup(template.render(repliesMap=replies),'html.parser') for replies in cases])
    for en,zh in zip(*rendered):
        a,b=[s.select('[data-fact-id]') for s in (en,zh)]
        assert [(n['data-fact-id'],n['data-status']) for n in a]==[(n['data-fact-id'],n['data-status']) for n in b]
        for src,dst in zip(a,b):
            value=src.get_text().strip()
            if value in phrases:
                assert dst.get_text().strip()==phrases[value],(value,dst.get_text()); checked_phrases+=1
            if src.get('class')==['answer-detail']: assert src.decode_contents()==dst.decode_contents()
        for s in (en,zh):
            assert not s.select('p p, p div, p ul')
            check_paper_flow(s)
    assert checked_phrases > 400
    assert '12\xa0年' in rendered[1][24].get_text(), 'Archive year unit was not translated'
    report={'passed':True,'release_acceptance':False,'local_branch_language_checks':2*len(cases),
            'exact_reviewed_phrase_checks':checked_phrases,'checker_sha256':sha(Path(__file__)),
            'context_flow_checks':2*len(cases),
            'helper_sha256':{n:sha(Path(__file__).with_name(n)) for n in ['check_context_outputs.py','check_paper_outputs.py']},
            'fixture_helper_sha256':sha(args.english/'tests/test_preservation_coverage.py'),
            'reviewed_phrases_sha256':sha(ROOT/'docs/readability-phrases.json'),
            'package_sha256':{n:sha(args.build/n) for n in ('english.zip','chinese.zip')},
            'limits':['Adapter-based branch checks, not native DSW rendering','Authored probe HTML stays unchanged','No full SE coverage claim']}
    (args.build/'preservation-translation-probe.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__': main()
