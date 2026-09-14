"""Native Pandoc probe using the pinned local worker image; no DSW or credentials."""
import argparse
import json
import subprocess
import sys
from pathlib import Path
from artifact_utils import sha

IMAGE = 'datastewardshipwizard/document-worker@sha256:5e5c5e1e436feb49fc4cbcd62c2e0ab2785db2141b0fe40d2926906bcfeaebfc'


def plain(node):
    if isinstance(node, dict):
        if node.get('t') == 'Str': return node['c']
        if node.get('t') in ('Space', 'SoftBreak'): return ' '
        return ''.join(plain(v) for v in node.values())
    if isinstance(node, list): return ''.join(plain(v) for v in node)
    return ''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--english', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    sys.path[:0] = [str(args.english.resolve() / folder) for folder in ('tests', 'scripts')]
    from test_science_europe_contract import render_question
    from generate_sharing_fixtures import sharing_cases
    from generate_pilot_fixtures import IDS
    source = args.english.resolve() / 'src/word/pilot.lua'
    rows = []
    for case, data in sharing_cases('en').items():
        replies = {p: v['value'] for p,v in data.items()}
        authored = '<p>Keep Access-2027-12-31.csv!</p><p>Second paragraph.</p><ul><li>First.</li><li>Second.</li></ul>'
        for p in replies:
            if any(p.endswith(IDS[n]) for n in ('licenseRestrictConditionsQUuid', 'licenseRestrictAccessAnotherQUuid', 'repoChargesHowPayOtherQUuid')):
                replies[p] = authored
        html = ''.join(render_question('src/questions/' + q, replies) for q in ('10-share-restrictions.html.j2', '11-data-preservation.html.j2'))
        ast = json.loads(subprocess.check_output(['docker', 'run', '--rm', '--network', 'none', '-i', '--entrypoint', '/usr/local/bin/pandoc', '-v', f'{source}:/tmp/pilot.lua:ro', IMAGE, '--from=html', '--to=json', '--lua-filter=/tmp/pilot.lua'], input=html.encode()))
        paragraphs = []
        def walk(node):
            if isinstance(node, dict):
                if node.get('t') == 'Para': paragraphs.append(plain(node))
                for value in node.values(): walk(value)
            elif isinstance(node, list):
                for value in node: walk(value)
        walk(ast)
        assert any('2027\u201112\u201131' in p and 'Open access' in p and 'CC-BY' in p for p in paragraphs)
        if case == 'sharing-custom':
            assert any('2027\u201106\u201101' in p and 'subject to restrictions' in p for p in paragraphs)
            assert paragraphs.count('Keep Access-2027-12-31.csv!') == 3
            assert paragraphs.count('Second paragraph.') == 3
            assert any('This dataset will be published.' in p and 'Retention period' in p and 'metadata' in p for p in paragraphs)
        else:
            assert 'The retention period has not been provided.' in paragraphs
            assert 'The metadata will be available even when the data no longer exists.' in paragraphs
            assert 'The specialized access process has not been described.' in paragraphs
        rows.append({'case': case, 'passed': True})
    report = {'passed': True, 'checks': rows, 'worker_image': IMAGE, 'word_filter_sha256': sha(source),
              'checker_sha256': sha(Path(__file__)), 'release_acceptance': False,
              'scope': 'Native Pandoc AST; synthetic HTML paragraphs substituted for Markdown to isolate the Lua filter. Not DOCX pagination acceptance.'}
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__': main()
