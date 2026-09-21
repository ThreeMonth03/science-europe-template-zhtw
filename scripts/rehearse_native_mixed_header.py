"""Bounded PDF-entry trials, with exact native baseline reproduction checked first."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
from bs4 import BeautifulSoup
from artifact_utils import sha
from mixed_budget_trial import trial
from rehearse_mixed_budget import content
from rehearse_profile_pdf import snapshot, prefix_geometry
from rehearse_profile_pagination import geometry
from check_short_resources_outputs import fonts

ROOT = Path(__file__).resolve().parents[1]
IMAGE = 'sha256:6d3cbcab3294e760a4d92e27bec72d4fb23a0adb2cc1734d981478688741ab11'
LONG = re.compile(r'<table class="resource-table pdf-resource-reading" .*?</table>', re.S)


def keep_body(source):
    def replace(match):
        table = match[0]
        assert table.count('<tbody>') == 1
        return table.replace('<tbody>', '<tbody style="break-inside: avoid">', 1)
    assert len(LONG.findall(source)) == 1
    result = LONG.sub(replace, source)
    assert result.replace('<tbody style="break-inside: avoid">', '<tbody>') == source
    return result


TAIL = 'html body .pdf-resource-reading tbody > tr > td > .answer-detail[data-fact-id="resource-justification"] { break-after: avoid; }'


def keep_tail(source):
    assert TAIL not in source and '</style>' in source
    result = source.replace('</style>', '\n' + TAIL + '\n</style>', 1)
    assert result.replace('\n' + TAIL + '\n</style>', '</style>', 1) == source
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['input', 'native', 'english', 'output']:
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    assert not a.output.exists()
    a.output.mkdir(parents=True)
    a.output.chmod(0o777)
    sys.path.insert(0, str(a.english.resolve() / 'scripts'))
    original = a.input.read_text()
    short, selected = trial(original, a.english)
    assert len(selected) == 8
    variants = {'baseline': original, 'short-rows': short,
                'body-keep': keep_body(original), 'both': keep_body(short),
                'short-tail': keep_tail(short), 'body-short-tail': keep_tail(keep_body(short))}
    report = {'diagnostic_only': True, 'native_candidate': False, 'release_acceptance': False,
              'input_sha256': sha(a.input), 'native_sha256': sha(a.native), 'selected': selected,
              'image': IMAGE, 'rows': []}
    reference = snapshot(a.native)
    canonical = content(reference[0], original)['canonical']
    for name, source in variants.items():
        path = a.output / (name + '.html')
        path.write_text(source)
        subprocess.run(['docker', 'run', '--rm', '--network', 'none', '--read-only',
                        '--tmpfs', '/tmp:rw,size=1g', '-e', 'XDG_CACHE_HOME=/tmp/cache',
                        '-e', 'PYTHONDONTWRITEBYTECODE=1', '--cap-drop', 'ALL',
                        '--security-opt', 'no-new-privileges',
                        '-v', str(a.output.resolve()) + ':/input:ro',
                        '-v', str(a.output.resolve()) + ':/out',
                        '-v', str(ROOT / 'experiments/mixed-budget-header') + ':/probe:ro',
                        '--entrypoint', 'python', IMAGE, '/probe/replay.py', name], check=True, timeout=180)
        pdf = a.output / (name + '.pdf')
        current = snapshot(pdf)
        parsed = content(current[0], original)
        assert parsed['canonical'] == canonical
        assert fonts(pdf) == fonts(a.native)
        same_geometry = current[1] == reference[1]
        if name == 'baseline':
            assert same_geometry, 'Captured native PDF-entry baseline still differs'
        assert prefix_geometry(current[1]) == prefix_geometry(reference[1])
        headers = {r['page'] for r in parsed['repeated_headers'] if r['kind'] == 'long-identity'}
        missing = sorted(set(parsed['long_pages'][1:]) - headers)
        trace = json.loads((a.output / (name + '.trace.json')).read_text())
        row = dict(variant=name, pages=len(current[0]), native_geometry_identical=same_geometry,
                   short_rows=parsed['rows'], long_pages=parsed['long_pages'], missing_header_pages=missing,
                   header_drop_events=[r for r in trace['trace'] if r['line'] == 529],
                   input_sha256=sha(path), pdf_sha256=sha(pdf))
        report['rows'].append(row)
        (a.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps({k:row[k] for k in ['variant','pages','native_geometry_identical','missing_header_pages']}), flush=True)


if __name__ == '__main__':
    main()
