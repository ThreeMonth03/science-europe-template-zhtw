"""Exhaustive local Jinja branch probe, separate from the actual DSW format tests."""
import argparse
import itertools
import json
import sys
from pathlib import Path
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from check_quality_outputs import METHODS, check_summary
from check_narrative_outputs import sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--english', type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.english.resolve() / 'tests'))
    import test_science_europe_contract as adapter
    import test_quality_reading as fixture
    count = 0
    for language, folder in [('english', 'en'), ('chinese', 'translated')]:
        env = Environment(loader=FileSystemLoader(args.build / folder), extensions=['jinja2.ext.do'], autoescape=False)
        env.filters.update(reply_path=adapter.reply_path, reply_items=adapter.reply_items,
                           reply_str_value=adapter.reply_str_value, markdown=lambda v: v, any=any,
                           dot=lambda v: str(v) + '.' if v else v)
        env.tests['true'] = lambda v: v is True
        for question in (fixture.Q1, fixture.Q4):
            template = env.from_string("{% import 'src/macros.html.j2' as macros with context %}{% import 'src/uuids.j2' as uuids with context %}" + "{% include '" + question + "' with context %}")
            for selected in itertools.product((False, True), repeat=7):
                replies = fixture.replies()
                for (name, _), yes in zip(fixture.METHODS, selected):
                    answer = fixture.IDS.get(f'mdQuality{name}{"Yes" if yes else "No"}AUuid')
                    if answer: replies[fixture.path(fixture.PREFIX, f'mdQuality{name}QUuid')] = answer
                soup = BeautifulSoup(template.render(repliesMap=replies), 'html.parser')
                marker = soup.select_one('[data-fact-id="quality-methods"]')
                assert marker
                if any(selected):
                    check_summary(marker.get_text(), language, [m for m, yes in zip(METHODS[language], selected) if yes], 'Coastal observations')
                    assert not marker.select('ul, br, p')
                else: assert marker['data-status'] == 'missing'
                count += 1
            unnamed = fixture.replies()
            del unnamed[fixture.path(fixture.DATASET, 'measuredDataNameQUuid')]
            soup = BeautifulSoup(template.render(repliesMap=unnamed), 'html.parser')
            assert ('（名稱尚未提供）' if language == 'chinese' else '(no name given)') in soup.get_text()
    report = {'passed': True, 'branch_question_language_checks': count, 'checker_sha256': sha(Path(__file__)),
              'assertion_helper_sha256': sha(Path(__file__).with_name('check_quality_outputs.py')),
              'package_sha256': {name: sha(args.build / name) for name in ('english.zip', 'chinese.zip')},
              'scope': '128 selected/not-selected combinations × Q1/Q4 × EN/ZH; local reply adapter, not 512 DSW render jobs',
              'release_acceptance': False}
    (args.build / 'quality-translation-probe.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__': main()
