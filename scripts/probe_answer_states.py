"""Selected Q5/Q11 state and exact-translation checks; not renderer acceptance."""
import argparse
import itertools
import json
import sys
from pathlib import Path
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from artifact_utils import sha

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--english', type=Path, required=True)
    args = parser.parse_args()
    sys.path[:0] = [str(args.english.resolve() / f) for f in ('tests', 'scripts')]
    import test_science_europe_contract as adapter
    from test_answer_states import storage_matrix, support_replies, LEAD, SUPPORT, Q5, Q11
    phrases = json.loads((ROOT / 'docs/readability-phrases.json').read_text())
    count = 0
    for folder in ('en', 'translated'):
        env = Environment(loader=FileSystemLoader(args.build / folder), extensions=['jinja2.ext.do'])
        env.filters.update(reply_path=adapter.reply_path, reply_items=adapter.reply_items, reply_str_value=adapter.reply_str_value, markdown=lambda v: v)
        def render(q, replies):
            t = env.from_string("{% import 'src/macros.html.j2' as macros with context %}{% import 'src/uuids.j2' as uuids with context %}{% include '" + q + "' %}")
            return BeautifulSoup(t.render(repliesMap=replies), 'html.parser')
        def expected(en): return phrases[en] if folder == 'translated' else en
        for replies in storage_matrix():
            q = render(Q5, replies)
            assert q.select_one('.storage-detail-limits > p').get_text() == expected(LEAD)
            assert [n['data-status'] for n in q.select('.storage-detail-limits [data-fact-id]')] == ['unmapped', 'unmapped']
            count += 1
        for pub, repo, choice in itertools.product([None, 'No', 'Yes'], [None, 'National', 'Special'], ['Yes', 'No', None, '', 'unknown']):
            q = render(Q11, support_replies((choice,), repo, pub))
            nodes = q.select('[data-fact-id="repository-long-term-support"]')
            assert bool(nodes) == (pub == 'Yes' and repo == 'Special')
            if nodes:
                state = {'Yes': 'complete', 'No': 'explicit-no'}.get(choice, 'missing')
                assert len(nodes) == 1 and nodes[0]['data-status'] == state
                assert nodes[0].get_text() == expected(SUPPORT[state])
                assert nodes[0].find_parent(attrs={'data-item-id': True})['data-item-id'] == 'distro-0'
            assert not q.select('p p, p div, p ul')
            count += 1
        q = render(Q11, support_replies(('Yes', 'No', None)))
        assert [(n.find_parent(attrs={'data-item-id': True})['data-item-id'], n['data-status'], n.get_text())
                for n in q.select('[data-fact-id="repository-long-term-support"]')] == [
                    (f'distro-{i}', state, expected(SUPPORT[state])) for i, state in enumerate(['complete', 'explicit-no', 'missing'])]
        count += 1
    report = {'passed': True, 'release_acceptance': False, 'local_branch_language_checks': count,
              'checker_sha256': sha(Path(__file__)), 'fixture_helper_sha256': sha(args.english / 'tests/test_answer_states.py'),
              'adapter_sha256': sha(args.english / 'tests/test_science_europe_contract.py'),
              'reviewed_phrases_sha256': sha(ROOT / 'docs/readability-phrases.json'),
              'package_sha256': {n: sha(args.build / n) for n in ['english.zip', 'chinese.zip']},
              'limits': ['Adapter-based synthetic branches, not actual DSW renders', 'No full SE coverage claim']}
    (args.build / 'answer-state-probe.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__': main()
