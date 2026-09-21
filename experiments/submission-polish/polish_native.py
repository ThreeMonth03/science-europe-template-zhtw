"""Native comparisons reuse the exact original pixel/text checks, with a new oracle."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'experiments/submission-notices'), str(Path(__file__).parent)]
from artifact_utils import sha
from notice_native import pair
from polish_probe import compare, replies_from

CASES = ['empty', 'notice-mixed', 'submission-metadata']


def run(before, after, fixtures, english, compacted=False):
    sys.path[:0] = [str(english / 'scripts'), str(english / 'tests')]
    from output_profile_contract import expected
    rows = []
    for case in CASES:
        for language, locale in [('english', 'en'), ('chinese', 'zh-Hant')]:
            replies = replies_from(fixtures / locale / (case + '.events.json'))
            for profile in ['review', 'submission']:
                checked = pair(before, after, case, language, profile, expected, compacted=compacted,
                               submission_compare=lambda old, new, lang: compare(old, new, lang, replies))
                rows.append(checked)
                print(json.dumps(dict(case=case, language=language, profile=profile,
                                      pages={k: v['pages'] for k, v in checked['rendered'].items()})), flush=True)
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['before', 'after', 'fixtures', 'english', 'output']: p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args(); assert not a.output.exists()
    report = dict(passed=False, prototype_only=True, release_acceptance=False, microsoft_word_acceptance=False,
                  global_switch_complete=False, checker_sha256=sha(Path(__file__)),
                  shared_checker_sha256=sha(ROOT / 'experiments/submission-notices/notice_native.py'))
    try:
        report['rows'] = run(a.before, a.after, a.fixtures, a.english.resolve()); report['passed'] = True
    except Exception as error: report['failure'] = repr(error); raise
    finally: a.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__': main()
