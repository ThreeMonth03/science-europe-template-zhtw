"""Actual bilingual build versus frozen native prototypes and independent oracles.

Unlike the prototype probes, these render the source produced by build.py, not
a patched package. Review bytes must match 0.3.43; submission must retain exactly
the facts and stable labels accepted by the separate parsed-tree oracle.
"""
import argparse
import json
from pathlib import Path
import sys
from bs4 import BeautifulSoup
from artifact_utils import sha

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'reviews/2026-09-21-dataset-labels'


def run(build, english):
    sys.path[:0] = [str(english / 'scripts'), str(english / 'tests'), str(ROOT / 'experiments/dataset-labels')]
    from output_profile_contract import environment, WRAPPER
    from generate_pilot_fixtures import IDS
    from label_probe import compare, replies_from
    from probe_pdf_budget_reading import dom
    wrapper = WRAPPER.replace("{% include 'src/content.html.j2' %}",
        "{% include 'src/contributors.html.j2' %}{% include 'src/content.html.j2' %}")
    fields = {IDS[k] for k in ['measuredDataNameQUuid', 'refDataNameQUuid', 'nrefDataNameQUuid', 'neqDataSetsNameQUuid', 'producedDataNameQUuid']}
    rows = []
    for language, locale, folder in [('english', 'en', 'en'), ('chinese', 'zh-Hant', 'translated')]:
        old, prototype = [json.loads((ARCHIVE / 'package' / (phase + '-' + language + '.json')).read_text())
                          for phase in ['before', 'after']]
        sources = list((english / 'fixtures/pilot' / locale).glob('*.events.json'))
        for archive in ['2026-09-21-submission-notices', '2026-09-21-submission-polish', '2026-09-21-dataset-labels']:
            sources += list((ROOT / 'reviews' / archive / 'fixtures' / locale).glob('*.events.json'))
        # The same archived case may occur in two trials; validate it only once.
        sources = sorted({(p.name, sha(p)): p for p in sources}.values())
        for escape in [False, True]:
            old_template, trial_template = [environment(english, escape,
                {f['fileName']: f['content'] for f in data['files']}).from_string(wrapper) for data in [old, prototype]]
            current = environment(build / folder, escape).from_string(wrapper)
            dc = {'project': {'created_by': None}, 'e': {'choices': {}}}
            for source in sources:
                for nameless in [False, True]:
                    replies = replies_from(source)
                    if nameless:
                        replies = {p: v for p, v in replies.items() if p.split('.')[-1] not in fields}
                    identity = (language, escape, source.name, nameless)
                    review = old_template.render(repliesMap=replies, dc=dc)
                    assert trial_template.render(repliesMap=replies, dc=dc) == review, identity
                    for mode in [None, 'review', 'unknown']:
                        options = {} if mode is None else {'output_profile': mode}
                        assert current.render(repliesMap=replies, dc=dc, **options) == review, (identity, mode, 'Review byte drift')
                    render = lambda t: BeautifulSoup(t.render(repliesMap=replies, dc=dc, output_profile='submission'), 'html.parser')
                    before, approved, actual = [render(t) for t in [old_template, trial_template, current]]
                    assert dom(actual) == dom(approved), (identity, 'Integrated submission differs from native prototype')
                    count = compare(before, actual, language, replies)
                    rows.append(dict(language=language, autoescape=escape, case=source.name,
                        fixture_sha256=sha(source), all_names_removed=nameless, labels=count, passed=True))
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', type=Path, required=True); p.add_argument('--english', type=Path, required=True)
    a = p.parse_args(); rows = run(a.build.resolve(), a.english.resolve())
    report = dict(passed=True, release_acceptance=False, native_integrated_render_checked=False,
        rows=rows, checker_sha256=sha(Path(__file__)),
        package_sha256={language: sha(a.build / (language + '.zip')) for language in ['english', 'chinese']})
    with (a.build / 'submission-preview-structure.json').open('x') as stream:
        stream.write(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(passed=True, checks=len(rows))))


if __name__ == '__main__': main()
