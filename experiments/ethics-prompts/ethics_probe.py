"""Independently identify the two source-owned Q9 fragments from reply paths."""
import copy
import json
from pathlib import Path
import sys
from bs4 import BeautifulSoup, NavigableString
from ethics_recipe import baseline, patch, TEXT, ROOT

sys.path[:0] = [str(ROOT / 'experiments/entity-labels')]
from entity_probe import replies_from


def expected(before, language, replies):
    from generate_pilot_fixtures import IDS, path
    from test_science_europe_contract import reply_items, reply_str_value
    result = copy.deepcopy(before); changes = []
    value = lambda p: reply_str_value(replies.get(p))
    produced = path('preservingCUuid', 'producedDataQUuid')
    items = reply_items(replies.get(produced))
    nodes = result.select('#q-ethical-issues > .answer > ul > li:not(.ethical-project)')
    assert len(nodes) == len(items), 'Ambiguous Q9 produced-data list'
    for item, node in zip(items, nodes):
        prefix = path(produced, item)
        if value(path(prefix, 'containPersonalQUuid')) or value(path(prefix, 'containSensitiveQUuid')): continue
        candidates = node.find_all('span', recursive=False)
        assert len(candidates) == 1 and candidates[0].get_text() == ' - ' + TEXT[language]['flags']
        assert candidates[0].find('em', recursive=False) is not None
        candidates[0].decompose(); changes.append(dict(kind='missing-data-flags', item=item))
    personal = path('creatingCUuid', 'collectPersonalQUuid')
    gdpr = path(personal, 'collectPersonalYesAUuid', 'cpersGdprQUuid')
    legal = path(gdpr, 'cpersGdprExploreAUuid', 'cpersGdprLegalBasisQUuid')
    other = path(legal, 'cpersGdprLegalBasisOtherAUuid', 'cpersGdprLegalBasisOtherWhichQUuid')
    active = (value(personal) == IDS['collectPersonalYesAUuid'] and value(gdpr) == IDS['cpersGdprExploreAUuid']
              and value(legal) == IDS['cpersGdprLegalBasisOtherAUuid'] and not value(other))
    if active:
        nodes = result.select('#q-ethical-issues > .answer > .answer-detail')
        assert len(nodes) == 1
        first = nodes[0].contents[0]; assert isinstance(first, NavigableString)
        separator = ' ' if language == 'english' else ''
        prefix = TEXT[language]['lead'] + separator + TEXT[language]['old']
        assert str(first).startswith(prefix), ('Unexpected owned prefix', str(first))
        # Only the leading source-owned sentence. An identical literal in the
        # subsequent authored reply (even in the same text node) stays untouched.
        first.replace_with(TEXT[language]['lead'] + separator + TEXT[language]['new'] + str(first)[len(prefix):])
        changes.append(dict(kind='other-basis-partial-fact', path=legal))
    return result, changes


def compare(before, after, language, replies):
    from probe_pdf_budget_reading import dom
    projected, changes = expected(before, language, replies)
    assert dom(projected) == dom(after), 'Unexpected text, paragraph, answer, identity or formatting delta'
    assert len(after.select('.question')) == 15 and len(after.select('.dmp-section')) == 6
    assert not after.select('p p, p div, p table, p ul')
    return changes


def templates(english, language, escape, word=False):
    from output_profile_contract import environment, WRAPPER
    wrapper = WRAPPER.replace("{% include 'src/content.html.j2' %}",
        "{% include 'src/contributors.html.j2' %}{% include 'src/content.html.j2' %}")
    if word: wrapper = '{% set word_budget_reading = true %}' + wrapper
    old = baseline(language); new, _ = patch(old, language)
    return [environment(english, escape, {f['fileName']: f['content'] for f in data['files']}).from_string(wrapper)
            for data in [old, new]]


def check_case(pair, replies, language):
    context = dict(repliesMap=replies, dc={'project': {'created_by': None}, 'e': {'choices': {}}})
    review = pair[0].render(**context)
    for mode in [None, 'review', 'unknown']:
        options = {} if mode is None else {'output_profile': mode}
        assert pair[1].render(**context, **options) == review, 'Review bytes changed'
    before, after = [BeautifulSoup(t.render(**context, output_profile='submission'), 'html.parser') for t in pair]
    return before, after, compare(before, after, language, replies)


def run(english, extra):
    sys.path[:0] = [str(english / 'scripts'), str(english / 'tests'), str(ROOT / 'scripts')]
    from artifact_utils import sha
    rows = []
    for language, locale in [('english', 'en'), ('chinese', 'zh-Hant')]:
        sources = list((english / 'fixtures/pilot' / locale).glob('*.events.json'))
        sources += list((extra / locale).glob('*.events.json'))
        for escape in [False, True]:
            for word in [False, True]:
                pair = templates(english, language, escape, word)
                for source in sorted(sources):
                    try: _, _, changes = check_case(pair, replies_from(source), language)
                    except AssertionError as error: raise AssertionError((language, escape, word, source.name, str(error))) from error
                    rows.append(dict(language=language, autoescape=escape, word_layout=word, case=source.name,
                                     fixture_sha256=sha(source), changes=changes, passed=True))
    return rows
