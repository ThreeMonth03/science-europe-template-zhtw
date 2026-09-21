"""Independent old-render boundary oracle, with exact authored subtree retention."""
import copy
from pathlib import Path
import sys
from bs4 import BeautifulSoup, NavigableString
from lead_recipe import ROOT, baseline, patch

sys.path[:0] = [str(ROOT / 'experiments/ethics-prompts'), str(ROOT / 'scripts')]
from ethics_probe import replies_from

SELECTOR = '#q-ethical-issues > .answer > .answer-detail'
MARKER = '<div id="q9-test-only-boundary">BOUNDARY-ORACLE-20260921</div>'


def first_reply(replies):
    from generate_pilot_fixtures import IDS, path
    from test_science_europe_contract import reply_str_value
    value = lambda key: reply_str_value(replies.get(key))
    personal = path('creatingCUuid', 'collectPersonalQUuid')
    gdpr = path(personal, 'collectPersonalYesAUuid', 'cpersGdprQUuid')
    if value(personal) != IDS['collectPersonalYesAUuid'] or value(gdpr) != IDS['cpersGdprExploreAUuid']: return None
    legal = path(gdpr, 'cpersGdprExploreAUuid', 'cpersGdprLegalBasisQUuid')
    paths = []
    if value(legal) == IDS['cpersGdprLegalBasisAskAUuid']:
        paths += [path(legal, 'cpersGdprLegalBasisAskAUuid', field) for field in
                  ['cpersExplainInformedQUuid', 'cpersDescribeProcedureQUuid']]
    paths.append(path(gdpr, 'cpersGdprExploreAUuid', 'cpersGdprPurposeQUuid'))
    return next((key for key in paths if value(key)), None)


def render(template, replies, profile='submission'):
    options = {} if profile is None else dict(output_profile=profile)
    return template.render(repliesMap=replies, dc={'project': {'created_by': None}, 'e': {'choices': {}}}, **options)


def expected(before, old_template, replies, language):
    """Find the boundary using an OLD-template sentinel render, not the patch.

    The sentinel is synthetic test input only, never written to a real answer.
    No punctuation, user HTML, or keywords are scanned to locate ownership.
    """
    from generate_pilot_fixtures import path
    from test_science_europe_contract import reply_items, reply_str_value
    result = copy.deepcopy(before); changes = []; key = first_reply(replies)
    produced = path('preservingCUuid', 'producedDataQUuid'); items = reply_items(replies.get(produced))
    if items and not any(reply_str_value(replies.get(path(produced, items[-1], field)))
                         for field in ['containPersonalQUuid', 'containSensitiveQUuid']):
        nodes = result.select('#q-ethical-issues > .answer > ul > li:not(.ethical-project)')
        assert len(nodes) == len(items)
        names = nodes[-1].find_all('strong', recursive=False); assert len(names) == 1 and not names[0].attrs
        names[0]['style'] = 'break-after: auto'
        changes.append(dict(kind='release-final-name-only-item', item=items[-1]))
    if key is None: return result, changes
    probe = copy.deepcopy(replies); probe[key] = MARKER
    sentinel = BeautifulSoup(render(old_template, probe), 'html.parser')
    marker = sentinel.select('#q9-test-only-boundary'); assert len(marker) == 1
    lead = marker[0].previous_sibling
    assert isinstance(lead, NavigableString) and marker[0].parent in sentinel.select(SELECTOR)
    prefix = str(lead); assert prefix.strip()
    separator = ' ' if language == 'english' else ''
    if separator: assert prefix.endswith(separator)
    owned = prefix[:-1] if separator else prefix
    detail = result.select(SELECTOR); assert len(detail) == 1
    first = detail[0].contents[0]
    assert isinstance(first, NavigableString) and str(first).startswith(prefix)
    remainder = str(first)[len(prefix):]
    # The old anonymous lead has no paragraph bottom margin. Keep its spacing;
    # only expose the ownership boundary to the existing keep-with-next rule.
    paragraph = result.new_tag('p', attrs={'class': 'answer-lead', 'style': 'margin-bottom: 0'}); paragraph.string = owned
    first.replace_with(paragraph)
    if remainder: paragraph.insert_after(NavigableString(remainder))
    return result, changes + [dict(kind='owned-lead-paragraph', path=key, owned_text=owned)]


def compare(before, after, old_template, replies, language):
    from probe_pdf_budget_reading import dom
    projected, changes = expected(before, old_template, replies, language)
    assert dom(projected) == dom(after), 'Unexpected authored text, paragraph, punctuation, or other-question delta'
    assert len(after.select('.question')) == 15 and len(after.select('.dmp-section')) == 6
    assert not after.select('p p, p div, p table, p ul, p ol')
    return changes


def templates(english, language, escape=False, word=False):
    from output_profile_contract import environment, WRAPPER
    wrapper = WRAPPER.replace("{% include 'src/content.html.j2' %}",
        "{% include 'src/contributors.html.j2' %}{% include 'src/content.html.j2' %}")
    if word: wrapper = '{% set word_budget_reading = true %}' + wrapper
    old = baseline(language); new, _ = patch(old, language)
    return [environment(english, escape, {f['fileName']: f['content'] for f in data['files']}).from_string(wrapper)
            for data in [old, new]]


def check_case(pair, replies, language):
    for profile in [None, 'review', 'unknown']:
        assert render(pair[0], replies, profile) == render(pair[1], replies, profile), 'Review bytes changed'
    old, new = [BeautifulSoup(render(t, replies), 'html.parser') for t in pair]
    return old, new, compare(old, new, pair[0], replies, language)


def run(english, extra):
    from artifact_utils import sha
    rows = []
    for language, locale in [('english', 'en'), ('chinese', 'zh-Hant')]:
        sources = list((english / 'fixtures/pilot' / locale).glob('*.events.json')) + list((extra / locale).glob('*.events.json'))
        for escape in [False, True]:
            for word in [False, True]:
                pair = templates(english, language, escape, word)
                for source in sorted(sources):
                    try: _, _, changes = check_case(pair, replies_from(source), language)
                    except AssertionError as error: raise AssertionError((language, escape, word, source.name, str(error))) from error
                    rows.append(dict(language=language, autoescape=escape, word_layout=word, case=source.name,
                                     fixture_sha256=sha(source), changes=changes, passed=True))
    return rows
