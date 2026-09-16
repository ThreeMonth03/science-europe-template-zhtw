"""Q13 fixed prose: bilingual choices, scope and owned joining boundaries."""
import argparse
import itertools
import json
import sys
from pathlib import Path
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader, ChoiceLoader, DictLoader
from artifact_utils import sha
from identifier_followup_contract import check_followups


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', type=Path, required=True)
    p.add_argument('--english', type=Path, required=True)
    a = p.parse_args()
    sys.path[:0] = [str(a.english.resolve()/n) for n in ['tests','scripts']]
    import test_science_europe_contract as adapter
    from test_identifier_reading import identifier_replies
    from identifier_concise_contract import compare
    from generate_pilot_fixtures import IDS
    phrases = json.loads((Path(__file__).resolve().parents[1]/'docs/readability-phrases.json').read_text())
    count = phrase_checks = 0
    for folder, language in [('en','english'), ('translated','chinese')]:
        env = Environment(loader=FileSystemLoader(a.build/folder), extensions=['jinja2.ext.do'])
        env.filters.update(reply_path=adapter.reply_path, reply_items=adapter.reply_items,
                           reply_str_value=adapter.reply_str_value, markdown=lambda v:v)
        template = env.from_string("{% import 'src/macros.html.j2' as macros with context %}{% import 'src/uuids.j2' as uuids with context %}{% include 'src/questions/13-persistent-identifier.html.j2' %}")
        question = 'src/questions/13-persistent-identifier.html.j2'
        baseline = Path(__file__).resolve().parents[1]/'tests/fixtures'/('identifier-0.3.26.'+('en' if language=='english' else 'zh-Hant')+'.html.j2')
        old_env = env.overlay(loader=ChoiceLoader([DictLoader({question: baseline.read_text()}), env.loader]))
        old_template = old_env.from_string("{% import 'src/macros.html.j2' as macros with context %}{% import 'src/uuids.j2' as uuids with context %}{% include '"+question+"' %}")
        def translated(s): return s if language == 'english' else phrases[s]
        for identifier, assigns, resolves, kind in itertools.product(
            ['Yes','No',None,'future-id'], ['Repository','ProjectDataSteward','InstitDataSteward',None,'future-assign'],
            ['Yes','No',None,'future-resolve'], ['DomainSpecific','GeneralPurpose','National','Institutional','Special',None,'future-kind']):
            replies = identifier_replies(identifier, assigns, resolves, kind)
            soup = BeautifulSoup(template.render(repliesMap=replies), 'html.parser')
            compare(BeautifulSoup(old_template.render(repliesMap=replies),'html.parser'),soup,language)
            check_followups(soup,replies,IDS,language,concise=True)
            distros = soup.select('.distribution-section')
            assert [d['data-item-id'] for d in distros] == ['distro-0','distro-1']
            for index, distro in enumerate(distros,1):
                heading = distro.select_one('.identifier-heading')
                assert heading and heading.select_one('p strong').get_text() == (f'Distribution {index}' if language=='english' else f'資料提供管道 {index}')
                policy = distro.select_one('.identifier-arrangement.dataset-policy')
                assert bool(policy) == (identifier == 'Yes')
                if policy:
                    expected = ['Persistent identifiers will be assigned.']
                    assign_text = {'Repository':'The repository will assign the persistent identifier.',
                                   'ProjectDataSteward':'A project data steward or principal investigator will assign the persistent identifier.',
                                   'InstitDataSteward':'An institutional data steward will assign the persistent identifier.'}
                    if assigns in assign_text: expected = [assign_text[assigns]]
                    if resolves in ['Yes','No']:
                        expected.append('The repository will ' + ('not ' if resolves=='No' else '') + 'make sure the persistent identifier can be resolved to a digital object.')
                    assert [n.get_text() for n in policy.find_all('p',recursive=False)] == [translated(s) for s in expected]
                    phrase_checks += len(expected)
                    assert not policy.select('.answer-detail, .data-gap')
                    if language == 'chinese':
                        paragraphs = policy.find_all('p', recursive=False)
                        for left, right in zip(paragraphs, paragraphs[1:]):
                            # The PDF override removes only a GENERATED separator.
                            # Literal source indentation between inline paragraphs
                            # would still show as a space; fail rather than strip it.
                            assert left.next_sibling is right
                            assert left.get_text().endswith('。')
                            assert '\u4e00' <= right.get_text()[0] <= '\u9fff'
                else:
                    assert not distro.select('[data-fact-id="persistent-identifier"]')
                    if identifier == 'No':
                        assert translated('Within this repository, unique and persistent identifiers will not be applied.') in distro.get_text()
                    else: assert distro.select_one('.data-gap[data-status="missing-output"]')
            assert not soup.select('p div, p p, p ul')
            count += 1
        for assigner,resolution in [(None,None),(' \n\t',None),('<script>future</script>','No'),
                                   ('Repository','future'),(' '+IDS['publishedDataIdentifierAssignsRepositoryAUuid'],None)]:
            replies=identifier_replies(assigns=assigner,resolves=resolution)
            soup=BeautifulSoup(template.render(repliesMap=replies),'html.parser')
            compare(BeautifulSoup(old_template.render(repliesMap=replies),'html.parser'),soup,language)
            check_followups(soup,replies,IDS,language,concise=True)
            assert '<script>' not in str(soup)
            count+=1
        from generate_identifier_fixtures import identifier_case
        replies={k:v['value'] for k,v in identifier_case('en' if language=='english' else 'zh-Hant').items()}
        check_followups(BeautifulSoup(template.render(repliesMap=replies),'html.parser'),replies,IDS,language,concise=True)
        count+=1
        for state in ['', IDS['isPublishedDataNoAUuid']]:
            replies = identifier_replies()
            key = next(k for k in replies if k.endswith(IDS['isPublishedDataQUuid']))
            replies[key] = state
            soup = BeautifulSoup(template.render(repliesMap=replies), 'html.parser')
            assert not soup.select('.identifier-heading, .identifier-arrangement')
            check_followups(soup,replies,IDS,language,concise=True)
            count += 1
    report = {'passed':True,'release_acceptance':False,'local_branch_language_checks':count,'fixed_phrase_checks':phrase_checks,
              'checker_sha256':sha(Path(__file__)), 'package_sha256':{n:sha(a.build/n) for n in ['english.zip','chinese.zip']},
              'source_helper_sha256':{n:sha(a.english/n) for n in ['tests/test_identifier_reading.py','tests/test_answer_states.py','tests/test_science_europe_contract.py']},
              'phrase_sha256':sha(Path(__file__).resolve().parents[1]/'docs/readability-phrases.json'),
              'helper_sha256':{'identifier_followup_contract.py':sha(Path(__file__).with_name('identifier_followup_contract.py'))},
              'fixture_source_sha256':sha(a.english/'scripts/generate_identifier_fixtures.py'),
              'limits':['Offline adapters, not native layout acceptance','Unsupported UUIDs are tested offline; they are not valid new KM choices','Only Q13 identifier assignment/resolution follow-ups are newly covered']}
    (a.build/'identifier-translation-probe.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__': main()
