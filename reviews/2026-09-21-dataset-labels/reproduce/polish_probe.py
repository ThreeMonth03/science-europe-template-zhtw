"""Independent structural oracle. Only tests project rendered nodes; never ships."""
import argparse
import copy
import itertools
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from bs4 import BeautifulSoup, NavigableString

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'experiments/submission-notices'), str(Path(__file__).parent)]
from artifact_utils import sha
from notice_probe import expected as marked_expected, compact, owned_gaps
from polish_recipe import patch


def replies_from(path):
    return {e['path']: ({'value': {'value': e['value']['value']}} if e['value']['type'] == 'IntegrationReply' else e['value']['value'])
            for e in json.loads(path.read_text())}


def expected(old, language, replies):
    from generate_pilot_fixtures import IDS, path
    from test_science_europe_contract import reply_items, reply_str_value
    soup = marked_expected(old, language)
    # Both prior quality summaries are owned facts, never authored paragraphs.
    for other in list(soup.select('p.quality-summary[data-fact-id="quality-other"][data-status="partial"]')):
        if other.find_parent(class_='answer-detail'): continue
        name = copy.deepcopy(other.strong)
        previous = other.find_previous_sibling('p')
        methods = None
        if previous and previous.get('data-fact-id') == 'quality-methods':
            if previous.get('data-status') == 'complete':
                text = previous.get_text()
                prefix = ('Quality control measures for ' + name.get_text() + ': ') if language == 'english' else (name.get_text() + '：品質管控措施包括')
                end = '.' if language == 'english' else '。'
                assert text.startswith(prefix) and text.endswith(end)
                methods = text[len(prefix):-len(end)]
            previous.decompose()
        other.clear()
        if language == 'english':
            other.append('Quality control measures planned for ' if methods else 'Other quality control methods are planned for ')
            other.append(name)
            other.append(': ' if methods else '.')
        else:
            if not methods: other.append('本計畫將對')
            other.append(name)
            other.append('的品質管控措施包括' if methods else '採取其他品質管控方法。')
        if methods:
            span = soup.new_tag('span', attrs={'data-fact-id': 'quality-methods', 'data-status': 'complete'})
            span.string = methods; other.append(span)
            other.append(' and other quality control methods.' if language == 'english' else '及其他品質管控方法。')
    measured = path('creatingCUuid', 'measuredQUuid', 'measuredYesAUuid', 'measuredDataQUuid')
    for item in reply_items(replies.get(measured)):
        prefix = path(measured, item)
        if not reply_items(replies.get(path(prefix, 'measuredDataInstrQUuid'))):
            parent = soup.select_one('#q-how-data [data-item-id="' + prefix + '"]')
            if parent:
                phrase = 'No instruments for this dataset have been specified.' if language == 'english' else '尚未指定此資料集使用的儀器。'
                nodes = [n for n in parent.find_all('p', recursive=False) if n.get_text() == phrase]
                assert len(nodes) == 1
                nodes[0].decompose()
    projects_path = path('adminDetailsCUuid', 'projectsQUuid')
    items = reply_items(replies.get(projects_path)); overview = soup.select_one('#dmp-projects')
    if not items:
        overview.decompose()
    else:
        projects = overview.select(':scope > .project'); assert len(projects) == len(items)
        for item, project in zip(items, projects):
            prefix = path(projects_path, item)
            table = project.select_one('.project-details'); rows = table.select(':scope > tbody > tr')
            for field, row in zip(['projectNumberQUuid', 'projectStartQUuid', 'projectEndQUuid'], rows[:3]):
                if not reply_str_value(replies.get(path(prefix, field))): row.decompose()
            funders_path = path(prefix, 'fundersQUuid')
            funders = reply_items(replies.get(funders_path))
            if not any(reply_str_value(replies.get(path(prefix, field))) for field in ['projectNumberQUuid', 'projectStartQUuid', 'projectEndQUuid']) and not funders:
                table.decompose(); continue
            if funders:
                entries = rows[-1].select('li'); assert len(entries) == len(funders)
                for funder, li in zip(funders, entries):
                    base = path(funders_path, funder)
                    if not reply_str_value(replies.get(path(base, 'grantNumberQUuid'))):
                        needle = ': grant number not yet given' if language == 'english' else '：尚未提供補助編號'
                        parts = [n for n in li.contents if isinstance(n, NavigableString) and needle in str(n)]
                        assert len(parts) == 1
                        # Last occurrence is the owned suffix; an authored label
                        # may itself contain exactly the same phrase.
                        value = str(parts[0]); at = value.rindex(needle)
                        parts[0].replace_with(value[:at] + value[at + len(needle):])
                    elif not replies.get(path(base, 'funderNameQUuid')):
                        first = next(n for n in li.contents if isinstance(n, NavigableString))
                        colon = ': ' if language == 'english' else '：'
                        assert str(first).startswith(colon)
                        first.replace_with(str(first)[len(colon):])
    # The structural suite supplies created_by=None. Native output usually has
    # an actual creator and therefore retains the contributor overview.
    contributors = soup.select_one('#dmp-contributors')
    if contributors and not reply_items(replies.get(path('adminDetailsCUuid', 'contributorsQUuid'))) and not contributors.select('.contributor'):
        contributors.decompose()
    return soup


def compare(old, new, language, replies):
    wanted = expected(old, language, replies)
    assert compact(wanted.get_text()) == compact(new.get_text()), 'Unexpected prose, punctuation or supplied-field delta'
    for selector in ['.answer-detail', '.abstract', '[data-status="explicit-no"]']:
        assert [str(n) for n in old.select(selector)] == [str(n) for n in new.select(selector)], selector
    assert [(a.get('href'), a.get_text()) for a in old.select('a')] == [(a.get('href'), a.get_text()) for a in new.select('a')]
    assert not owned_gaps(new)
    assert len(new.select('.question')) == 15 and len(new.select('.dmp-section')) == 6
    assert not new.select('p p, p div, p ul, p table')
    assert [h.get_text() for h in old.select('.question > h3, .dmp-section > h2')] == [h.get_text() for h in new.select('.question > h3, .dmp-section > h2')]
    assert len(new.select('#dmp-projects .project-details tr')) == len(wanted.select('#dmp-projects .project-details tr'))
    assert len(new.select('p.quality-summary')) == len(wanted.select('p.quality-summary'))
    return dict(passed=True, quality_paragraphs=len(new.select('p.quality-summary')),
                project_rows=len(new.select('#dmp-projects .project-details tr')), owned_gaps=0)


def run(english, fixtures):
    sys.path[:0] = [str(english / 'scripts'), str(english / 'tests')]
    from output_profile_contract import environment, WRAPPER
    from generate_pilot_fixtures import IDS, path
    rows = []
    for language, locale in [('english', 'en'), ('chinese', 'zh-Hant')]:
        old = json.loads((ROOT / 'reviews/2026-09-21-submission-notices/package' / ('before-' + language + '.json')).read_text())
        new, edits = patch(old, language)
        for escaping in [False, True]:
            wrapper = WRAPPER + "{% include 'src/contributors.html.j2' %}"
            templates = [environment(english, escaping, {f['fileName']: f['content'] for f in data['files']}).from_string(wrapper) for data in [old, new]]
            sources = sorted((english / 'fixtures/pilot' / locale).glob('*.events.json')) + [fixtures / locale / (name + '.events.json') for name in ['notice-mixed', 'submission-metadata']]
            cases = [(p.name, replies_from(p)) for p in sources]
            # Exhaust all seven fixed-method flags, both escaping settings, and
            # other-detail states without changing the real fixture generator.
            base = replies_from(fixtures / locale / 'notice-mixed.events.json')
            quality = next(k for k in base if k.endswith(IDS['measuredDataQualityQUuid']))
            qp = quality + '.' + IDS['measuredDataQualityYesAUuid']
            methods = ['mdQualityCalibrating', 'mdQualityRepetition', 'mdQualityStandardized', 'mdQualityValidation', 'mdQualityPeerReview', 'mdQualityVocabularies', 'mdQualityConsistency']
            for index, enabled in enumerate(itertools.product([False, True], repeat=7)):
                values = copy.deepcopy(base)
                for field, selected in zip(methods, enabled):
                    if selected: values[path(qp, field + 'QUuid')] = IDS[field + 'YesAUuid']
                    else: values.pop(path(qp, field + 'QUuid'), None)
                cases.append(('quality-flags-' + str(index), values))
            for name, replies in cases:
                def render(template, **kw):
                    return template.render(repliesMap=replies, dc=SimpleNamespace(project=SimpleNamespace(created_by=None), e=SimpleNamespace(choices={})), **kw)
                review = [render(t) for t in templates]
                assert review[0] == review[1], (name, language, escaping, 'Review byte delta')
                assert render(templates[1], output_profile='review') == review[0]
                assert render(templates[1], output_profile='unknown') == review[0]
                prior, candidate = [BeautifulSoup(render(t, output_profile='submission'), 'html.parser') for t in templates]
                try: result = compare(prior, candidate, language, replies)
                except AssertionError as error: raise AssertionError((name, language, escaping, str(error))) from error
                rows.append(dict(case=name, language=language, autoescape=escaping, **result))
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['english', 'fixtures', 'output']: p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args(); assert not a.output.exists()
    report = dict(passed=False, release_acceptance=False, global_switch_complete=False,
                  checker_sha256=sha(Path(__file__)), recipe_sha256=sha(Path(__file__).with_name('polish_recipe.py')))
    try:
        report['rows'] = run(a.english.resolve(), a.fixtures); report['passed'] = True
    except Exception as error: report['failure'] = repr(error); raise
    finally: a.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(passed=True, cases=len(report['rows']))))


if __name__ == '__main__': main()
