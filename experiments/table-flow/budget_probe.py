"""Independent reachability + exact old-DOM oracle for budget-only omissions."""
import copy
import sys
from bs4 import BeautifulSoup
from budget_recipe import ROOT, baseline, patch

sys.path[:0] = [str(ROOT / 'experiments/ethics-prompts'), str(ROOT / 'scripts')]
from ethics_probe import replies_from


def render(template, replies, profile='submission'):
    options = {} if profile is None else dict(output_profile=profile)
    return template.render(repliesMap=replies, dc={'project': {'created_by': None}, 'e': {'choices': {}}}, **options)


def expected(before, replies):
    from generate_pilot_fixtures import path
    from test_science_europe_contract import reply_items
    result = copy.deepcopy(before); changes = []
    base = path('adminDetailsCUuid', 'projectsQUuid')
    projects = reply_items(replies.get(base))
    groups = result.select('#q-required-resources > .answer > .project-resources')
    assert [g['data-item-id'] for g in groups] == [path(base, item) for item in projects]
    for item, group in zip(projects, groups):
        if reply_items(replies.get(path(base, item, 'costQUuid'))): continue
        # Only an owned name label is allowed, never answered paragraphs/table.
        children = group.find_all(recursive=False)
        if len(projects) > 1:
            assert len(children) == 1 and children[0].name == 'p'
            assert len(children[0].find_all(recursive=False)) == 1 and children[0].strong is not None
        else: assert not children
        changes.append(dict(kind='empty-project-budget', path=path(base, item), label=group.get_text(strip=True)))
        group.decompose()
    if projects and not result.select('#q-required-resources > .answer > .project-resources'):
        headings = result.select('#q-required-resources > .answer > h4'); assert len(headings) == 1
        changes.append(dict(kind='empty-budget-heading', label=headings[0].get_text()))
        headings[0].decompose()
    return result, changes


def compare(before, after, replies):
    from probe_pdf_budget_reading import dom
    projected, changes = expected(before, replies)
    assert dom(projected) == dom(after), 'Unexpected authored, numbering, overview, or other-question change'
    assert len(after.select('.question')) == 15 and len(after.select('.dmp-section')) == 6
    assert not after.select('p p, p div, p table, p ul, p ol')
    return changes


def templates(english, language, escape=False, layout='html'):
    from output_profile_contract import environment, WRAPPER
    assert layout in ['html', 'pdf', 'word']
    wrapper = WRAPPER.replace("{% include 'src/content.html.j2' %}",
        "{% include 'src/contributors.html.j2' %}{% include 'src/content.html.j2' %}")
    if layout != 'html': wrapper = '{% set ' + layout + '_budget_reading = true %}' + wrapper
    old = baseline(language); new, _ = patch(old, language)
    return [environment(english, escape, {f['fileName']: f['content'] for f in data['files']}).from_string(wrapper)
            for data in [old, new]]


def check_case(pair, replies):
    for profile in [None, 'review', 'unknown']:
        assert render(pair[0], replies, profile) == render(pair[1], replies, profile), 'Review bytes changed'
    old, new = [BeautifulSoup(render(t, replies), 'html.parser') for t in pair]
    return old, new, compare(old, new, replies)


def run(english, extra):
    from artifact_utils import sha
    rows = []
    for language, locale in [('english', 'en'), ('chinese', 'zh-Hant')]:
        sources = list((english / 'fixtures/pilot' / locale).glob('*.events.json')) + list((extra / locale).glob('*.events.json'))
        for escape in [False, True]:
            for layout in ['html', 'pdf', 'word']:
                pair = templates(english, language, escape, layout)
                for source in sorted(sources):
                    try: _, _, changes = check_case(pair, replies_from(source))
                    except AssertionError as error: raise AssertionError((language, escape, layout, source.name, str(error))) from error
                    rows.append(dict(language=language, autoescape=escape, layout=layout, case=source.name,
                                     fixture_sha256=sha(source), changes=changes, passed=True))
    return rows
