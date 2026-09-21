"""Compare actual rebuilt sources with frozen prototypes, without relaxing gates."""
import argparse
import difflib
import json
from pathlib import Path
import sys
import zipfile
from bs4 import BeautifulSoup
from asset_recipe import ROOT, HERE, ARCHIVE, baseline, sha


def run(build, english, output):
    assert not output.exists(); output.mkdir(parents=True)
    sys.path[:0] = [str(english / 'scripts'), str(english / 'tests'), str(ROOT / 'experiments/ethics-prompts')]
    from output_profile_contract import environment, WRAPPER
    from ethics_probe import replies_from
    from probe_pdf_budget_reading import dom
    wrapper = WRAPPER.replace("{% include 'src/content.html.j2' %}",
        "{% include 'src/contributors.html.j2' %}{% include 'src/content.html.j2' %}")
    rows = []; saved = set()
    for language, locale in [('english', 'en'), ('chinese', 'zh-Hant')]:
        with zipfile.ZipFile(build / (language + '.zip')) as z: actual = json.loads(z.read('template/template.json'))
        old = baseline(language)
        sources = list((english / 'fixtures/pilot' / locale).glob('*.events.json'))
        for archive in ['2026-09-21-entity-labels', '2026-09-21-ethics-prompts', '2026-09-21-ethics-lead']:
            sources += list((ROOT / 'reviews' / archive / 'fixtures' / locale).glob('*.events.json'))
        sources = sorted({(p.name, sha(p.read_bytes())): p for p in sources}.values())
        for escape in [False, True]:
            for layout in ['html', 'pdf', 'word']:
                entry = ('{% set ' + layout + '_budget_reading = true %}' if layout != 'html' else '') + wrapper
                pair = [environment(english, escape, {f['fileName']: f['content'] for f in data['files']}).from_string(entry)
                        for data in [old, actual]]
                for source in sources:
                    replies = replies_from(source)
                    for profile in [None, 'review', 'unknown', 'submission']:
                        options = {} if profile is None else dict(output_profile=profile)
                        values = [t.render(repliesMap=replies, dc={'project': {'created_by': None}, 'e': {'choices': {}}}, **options) for t in pair]
                        identical = values[0] == values[1]
                        parsed_equal = dom(BeautifulSoup(values[0], 'html.parser')) == dom(BeautifulSoup(values[1], 'html.parser'))
                        passed = parsed_equal if profile == 'submission' else identical
                        row = dict(language=language, autoescape=escape, layout=layout, profile=profile, case=source.name,
                            fixture_sha256=sha(source.read_bytes()), bytes_identical=identical, dom_identical=parsed_equal, passed=passed)
                        rows.append(row)
                        key = (language, escape, layout, profile)
                        if not passed and key not in saved:
                            saved.add(key); stem = '-'.join(map(str, key))
                            for phase, value in zip(['before', 'after'], values): (output / (stem + '-' + phase + '.html')).write_text(value)
                            (output / (stem + '.diff')).write_text(''.join(difflib.unified_diff(values[0].splitlines(True), values[1].splitlines(True))))
    result = dict(passed=all(r['passed'] for r in rows), source_integrated=False, native_rebuilt_source_checked=False,
        checker_sha256=sha(Path(__file__).read_bytes()), package_sha256={l: sha((build / (l + '.zip')).read_bytes()) for l in ['english', 'chinese']}, rows=rows)
    (output / 'report.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['build', 'english', 'output']: p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args(); result = run(a.build.resolve(), a.english.resolve(), a.output.resolve())
    print(json.dumps(dict(passed=result['passed'], checks=len(result['rows']), failures=sum(not r['passed'] for r in result['rows']))))
    raise SystemExit(0 if result['passed'] else 1)
