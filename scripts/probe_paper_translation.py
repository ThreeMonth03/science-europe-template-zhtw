"""Bilingual scalar references: exact values, labels, escaping and stage gating."""
import argparse
import json
import sys
from pathlib import Path
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from artifact_utils import sha
from check_paper_outputs import expected_papers, check_values


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', type=Path, required=True); p.add_argument('--english', type=Path, required=True)
    a = p.parse_args(); sys.path[:0] = [str(a.english.resolve() / n) for n in ['tests', 'scripts']]
    import test_science_europe_contract as adapter
    from test_paper_reference import paper_replies
    from generate_pilot_fixtures import IDS
    from generate_paper_fixtures import LONG_URL, PLAIN_CITATION, paper_case
    values = [(LONG_URL, True), ('https://example.org/Paper.csv.', True), ('http://example.org/x?x=1&y=2#end', True),
              (PLAIN_CITATION, False), ('doi:10.1234/Coast.', False), ('<b>Title</b>', False),
              ('javascript:alert(1)', False), ('data:text/html,<script>no</script>', False),
              ('https://example.org/paper followed by a title', False), (' https://example.org/paper', False),
              ('https://', False), ('https:///path', False), ('https://user@example.org/paper', False),
              ('https://example.org/"quote"', False), ('https://example.org/\\path', False),
              (None, False), ('', False), (' \n ', False)]
    count = 0
    for folder, language, locale in [('en', 'english', 'en'), ('translated', 'chinese', 'zh-Hant')]:
        env = Environment(loader=FileSystemLoader(a.build / folder), extensions=['jinja2.ext.do'])
        env.filters.update(reply_path=adapter.reply_path, reply_items=adapter.reply_items, reply_str_value=adapter.reply_str_value, markdown=lambda v:v)
        template = env.from_string("{% import 'src/macros.html.j2' as macros with context %}{% import 'src/uuids.j2' as uuids with context %}{% include 'src/questions/11-data-preservation.html.j2' %}")
        cases = [(paper_replies(value)[0], linked) for value, linked in values]
        replies, key = paper_replies(LONG_URL)
        stage = key.rsplit('.', 2)[0]
        for choice in ['', IDS['producedDataStageRawAUuid'], IDS['producedDataStageIntermediateAUuid'], 'future-stage']:
            cases.append(({**replies, stage: choice}, False))
        cases.append(({**replies, stage.rsplit('.', 1)[0] + '.' + IDS['isPublishedDataQUuid']: IDS['isPublishedDataNoAUuid']}, True))
        cases.append(({p:v['value'] for p,v in paper_case(locale).items()}, True))
        for replies, linked in cases:
            soup = BeautifulSoup(template.render(repliesMap=replies), 'html.parser')
            nodes = check_values(soup, expected_papers(replies, IDS), language)
            assert bool(soup.select('.paper-reference a')) == linked
            assert not soup.select('p p, p div, p ul, p table')
            count += 1
    report = {'passed': True, 'release_acceptance': False, 'local_branch_language_checks': count,
              'checker_sha256': sha(Path(__file__)), 'package_sha256': {n:sha(a.build/n) for n in ['english.zip','chinese.zip']},
              'helper_sha256': {n:sha(Path(__file__).with_name(n)) for n in ['check_paper_outputs.py','check_context_outputs.py']},
              'source_helper_sha256': {n:sha(a.english/n) for n in ['tests/test_paper_reference.py','tests/test_science_europe_contract.py','scripts/generate_paper_fixtures.py']},
              'limits': ['Adapter checks, not native PDF/Word acceptance', 'Blank reference behavior is unchanged, not a new full-completeness contract']}
    (a.build/'paper-translation-probe.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__': main()
