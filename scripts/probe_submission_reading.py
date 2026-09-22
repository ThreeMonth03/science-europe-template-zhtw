"""Actual 0.3.45 packages versus the reviewed native reading prototypes."""
import argparse
import json
from pathlib import Path
import sys
from submission_reading_integration import check

ROOT = Path(__file__).resolve().parents[1]


def run(build, english, preview=False):
    check(build, english, preview)
    sys.path.insert(0, str(ROOT / 'experiments/word-asset'))
    from source_parity import run as compare
    report = compare(build, english, build / 'submission-reading-parity')
    assert report['passed'] and len(report['rows']) == 3312
    report.update(source_integrated=True, native_rebuilt_source_checked=False)
    with (build / 'submission-reading-structure.json').open('x') as stream:
        stream.write(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', type=Path, required=True); p.add_argument('--english', type=Path, required=True)
    p.add_argument('--preview', action='store_true')
    a = p.parse_args(); result = run(a.build.resolve(), a.english.resolve(), a.preview)
    print(json.dumps(dict(passed=result['passed'], checks=len(result['rows']))))
