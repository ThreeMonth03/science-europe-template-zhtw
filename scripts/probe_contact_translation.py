"""Generated bilingual references: exact words, targets, and retained authored blocks."""
import argparse
import json
import sys
from pathlib import Path
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from artifact_utils import sha
from check_contact_outputs import check_references


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', type=Path, required=True); p.add_argument('--english', type=Path, required=True)
    a = p.parse_args(); sys.path[:0] = [str(a.english.resolve() / n) for n in ['tests', 'scripts']]
    import test_science_europe_contract as adapter
    from test_repository_contact import contact_replies
    from generate_pilot_fixtures import IDS, path
    from generate_contact_fixtures import contact_case
    count = 0
    for folder, language, locale in [('en', 'english', 'en'), ('translated', 'chinese', 'zh-Hant')]:
        env = Environment(loader=FileSystemLoader(a.build / folder), extensions=['jinja2.ext.do'])
        env.filters.update(reply_path=adapter.reply_path, reply_items=adapter.reply_items, reply_str_value=adapter.reply_str_value, markdown=lambda v: v, any=any)
        env.tests['true'] = lambda v: v is True
        template = env.from_string("{% import 'src/macros.html.j2' as macros with context %}{% import 'src/uuids.j2' as uuids with context %}{% include 'src/questions/10-share-restrictions.html.j2' %}{% include 'src/questions/11-data-preservation.html.j2' %}")
        value = '<p>Contact-probe-2027.csv.</p><ul><li>Keep this.</li></ul><p>Last paragraph.</p>'
        cases = []
        for answer in [None, '', ' \n ', value]:
            for size in [1, 3]:
                replies = contact_replies(answer)
                key = next(k for k in replies if k.endswith(IDS['publishedDistrosQUuid']))
                replies[key] = replies[key][:size]
                cases.append((replies, size, value if answer == value else None))
        for pub, repo, choice in [(None, 'DomainSpecific', 'Other'), ('No', 'DomainSpecific', 'Other'), ('Yes', 'National', 'Other'), ('Yes', 'DomainSpecific', None), ('Yes', 'DomainSpecific', 'YesAlready'), ('Yes', 'DomainSpecific', 'future-choice')]:
            cases.append((contact_replies(value, pub, repo, choice), 0, None))
        cases.append(({k: v['value'] for k, v in contact_case(locale).items()}, 4, None))
        for replies, expected, body in cases:
            soup = BeautifulSoup(template.render(repliesMap=replies), 'html.parser')
            assert len(check_references(soup, language)) == expected
            assert 'Contact-probe-2027.csv' not in soup.find(id='q-share-restrictions').get_text()
            if body:
                assert all(n.decode_contents() == body for n in soup.select('.repository-contact .answer-detail'))
            assert not soup.select('p p, p div, p ul, p table')
            count += 1
    report = {'passed': True, 'release_acceptance': False, 'local_branch_language_checks': count,
              'checker_sha256': sha(Path(__file__)), 'package_sha256': {n: sha(a.build / n) for n in ['english.zip', 'chinese.zip']},
              'helper_sha256': {'check_contact_outputs.py': sha(Path(__file__).with_name('check_contact_outputs.py'))},
              'source_helper_sha256': {n: sha(a.english / n) for n in ['tests/test_repository_contact.py', 'tests/test_science_europe_contract.py', 'tests/test_answer_states.py', 'scripts/generate_contact_fixtures.py']},
              'limits': ['Adapter-based branch checks, not native DSW/PDF/Word acceptance']}
    (a.build / 'contact-translation-probe.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__': main()
