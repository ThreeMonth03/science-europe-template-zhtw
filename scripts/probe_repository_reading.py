"""Check generated bilingual Q11 labels, missing rows and keep-hint boundaries."""
import argparse
import json
import sys
from pathlib import Path
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from artifact_utils import sha

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', type=Path, required=True); p.add_argument('--english', type=Path, required=True)
    args = p.parse_args()
    sys.path[:0] = [str(args.english.resolve() / f) for f in ['tests', 'scripts']]
    import test_science_europe_contract as adapter
    from test_answer_states import support_replies
    from generate_pilot_fixtures import IDS, path
    from generate_repository_fixtures import repository_cases
    count = 0
    for folder, locale in [('en', 'en'), ('translated', 'zh-Hant')]:
        env = Environment(loader=FileSystemLoader(args.build / folder), extensions=['jinja2.ext.do'])
        env.filters.update(reply_path=adapter.reply_path, reply_items=adapter.reply_items, reply_str_value=adapter.reply_str_value, markdown=lambda v: v, any=any)
        env.tests['true'] = lambda v: v is True
        def render(replies, q='11-data-preservation'):
            template = env.from_string("{% import 'src/macros.html.j2' as macros with context %}{% import 'src/uuids.j2' as uuids with context %}{% include 'src/questions/" + q + ".html.j2' %}")
            return BeautifulSoup(template.render(repliesMap=replies), 'html.parser')
        label = 'Distribution {}:' if folder == 'en' else '資料提供管道 {}：'
        cases = [(support_replies(('Yes',) * n), n <= 3) for n in [1, 2, 3, 4, 8]]
        for pub in [None, 'No']: cases.append((support_replies(('Yes', 'No'), publication=pub), False))
        for kind in [None, 'National']: cases.append((support_replies(('Yes', 'No'), repository=kind), True))
        cases.extend(({k: v['value'] for k, v in replies.items()}, name != 'repository-long') for name, replies in repository_cases(locale).items())
        for replies, short in cases:
            soup = render(replies)
            assert bool(soup.select('.short-repository-list')) == short
            for dataset in soup.select('.dataset-section'):
                rows = dataset.select('.repository-distribution')
                assert [n.get_text() for n in dataset.select('.repository-label')] == ([label.format(i) for i in range(1, len(rows) + 1)] if len(rows) > 1 else [])
                if len(rows) > 1:
                    for q in ['10-share-restrictions', '13-persistent-identifier']:
                        other = render(replies, q).select_one(f'.dataset-section[data-item-id="{dataset["data-item-id"]}"]')
                        assert [n['data-item-id'] for n in rows] == [n['data-item-id'] for n in other.select('.distribution-section')]
            assert not soup.select('p p, p div, p ul')
            count += 1
        for choice, state in [('', 'missing'), ('unsupported-choice', 'needs-review')]:
            replies = support_replies(('Yes', 'No', None))
            key = next(k for k in replies if 'distro-1' in k and k.endswith(IDS['publishedDataRepositoryKindQUuid']))
            replies[key] = choice
            middle = render(replies).select('.repository-distribution')[1]
            n = middle.select_one('[data-fact-id="repository-destination"]')
            assert n['data-status'] == state and not middle.select('[data-fact-id="repository-long-term-support"]')
            expected = ({'missing': 'The repository for this distribution has not been specified.', 'needs-review': 'The selected repository type cannot be described by this template.'} if folder == 'en' else
                        {'missing': '尚未說明此管道將使用哪個資料儲存庫。', 'needs-review': '本模板無法呈現所選的資料儲存庫類型，請核對。'})
            assert n.get_text() == expected[state]
            count += 1
    report = {'passed': True, 'release_acceptance': False, 'local_branch_language_checks': count,
              'checker_sha256': sha(Path(__file__)), 'package_sha256': {n: sha(args.build / n) for n in ['english.zip', 'chinese.zip']},
              'helper_sha256': {n: sha(args.english / n) for n in ['tests/test_answer_states.py', 'tests/test_science_europe_contract.py', 'scripts/generate_repository_fixtures.py']},
              'limits': ['Adapter checks, not native PDF/Word pagination acceptance', 'Only selected Common KM paths']}
    (args.build / 'repository-reading-probe.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__': main()
