"""Offline Q10/Q11 branch-language checks; not actual renderer acceptance."""
import argparse
import json
import sys
from pathlib import Path
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from artifact_utils import sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--english', type=Path, required=True)
    args = parser.parse_args()
    sys.path[:0] = [str(args.english.resolve() / folder) for folder in ('tests', 'scripts')]
    import test_science_europe_contract as adapter
    from test_sharing_preservation import matrix_cases, AUTHORED
    from generate_sharing_fixtures import sharing_cases
    count = 0
    for language, folder in [('english', 'en'), ('chinese', 'translated')]:
        env = Environment(loader=FileSystemLoader(args.build / folder), extensions=['jinja2.ext.do'])
        env.filters.update(reply_path=adapter.reply_path, reply_items=adapter.reply_items, reply_str_value=adapter.reply_str_value, markdown=lambda v: v, any=any)
        env.tests['true'] = lambda v: v is True
        def render(question, replies):
            template = env.from_string("{% import 'src/macros.html.j2' as macros with context %}{% import 'src/uuids.j2' as uuids with context %}{% include 'src/questions/" + question + "' %}")
            return BeautifulSoup(template.render(repliesMap=replies), 'html.parser')
        for replies, access, metadata, has_custom in matrix_cases():
            soup = render('10-share-restrictions.html.j2', replies)
            proc = soup.select_one('.restriction-process')
            assert bool(proc.select('[data-fact-id="restriction-access-process"]')) == (access is None)
            selected = access == 'licenseRestrictAccessAnotherAUuid'
            assert bool(proc.select('[data-fact-id="restriction-custom-process"][data-status="missing"]')) == (selected and not has_custom)
            assert bool(proc.select('[data-fact-id="restriction-metadata-publication"]')) == (metadata is None)
            negative = 'will not be published' if language == 'english' else '不會納入公開的後設資料'
            assert (negative in proc.get_text()) == (metadata == 'licenseRestrictMetadataNoAUuid')
            if selected and has_custom: assert proc.select_one('.answer-detail').decode_contents() == AUTHORED
            if language == 'chinese':
                assert 'has not been' not in proc.get_text() and '尚待補充' in proc.get_text() if access is None or metadata is None else True
                link = proc.select_one('a').parent.get_text()
                assert link.startswith('使用限制的詳細資訊：') and link.endswith('。')
            count += 1
        for replies in sharing_cases('en' if language == 'english' else 'zh-Hant').values():
            soup = render('11-data-preservation.html.j2', {p: v['value'] for p,v in replies.items()})
            assert not soup.select('.preservation-summary > p.data-gap, p div, p p')
            assert ('The metadata will be available even when the data no longer exists.' if language == 'english' else '即使資料已不存在，仍會持續提供後設資料。') in soup.get_text()
            count += 1
    report = {'passed': True, 'local_branch_language_checks': count, 'release_acceptance': False,
              'checker_sha256': sha(Path(__file__)), 'fixture_helper_sha256': sha(args.english / 'tests/test_sharing_preservation.py'),
              'package_sha256': {n: sha(args.build / n) for n in ('english.zip', 'chinese.zip')},
              'scope': '24 Q10 process/metadata/custom-detail combinations + 2 Q11 fixture states, each EN/ZH; adapters, not DSW renders'}
    (args.build / 'sharing-translation-probe.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__': main()
