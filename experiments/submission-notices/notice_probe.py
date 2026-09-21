"""Independent fact/text oracle for the marked-notice trial, including hostile-looking prose."""
import argparse
from collections import Counter
import copy
import json
from pathlib import Path
import sys
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'scripts'), str(Path(__file__).parent)]
from artifact_utils import sha
from notice_recipe import patch, project, PHRASES


def owned_gaps(soup):
    return [n for n in soup.select('.data-gap') if not n.find_parent(class_='answer-detail')]


def expected(old, language):
    """Independent rendered-node oracle; never used to generate documents."""
    result = copy.deepcopy(old)
    for node in list(owned_gaps(result)):
        # The previous partial profile already omits the Q5 diagnostic container.
        assert node.name == 'p', ('Unclassified non-paragraph diagnostic', str(node))
        fact = node.get('data-fact-id')
        question = node.find_parent(class_='question')
        question = question.get('id') if question else None
        replacement = None
        if question in ['q-how-data', 'q-quality-control'] and fact == 'quality-other':
            replacement = BeautifulSoup('<p class="quality-summary" data-fact-id="quality-other" data-status="partial">' + PHRASES[language]['quality-other'] + '</p>', 'html.parser').p
            name = copy.deepcopy(node.strong); assert name is not None
            replacement.strong.replace_with(name)
        elif fact == 'quality-control':
            replacement = BeautifulSoup('<p class="quality-context"></p>', 'html.parser').p
            replacement.append(copy.deepcopy(node.strong))
        elif fact == 'required-software-list':
            replacement = BeautifulSoup('<p data-requirement-id="SE-5c" data-fact-id="required-software-list" data-status="partial">' + PHRASES[language]['software'] + '</p>', 'html.parser').p
        elif question == 'q-how-data' and fact is None:
            replacement = BeautifulSoup('<p data-fact-id="reuse-restrictions" data-status="partial">' + PHRASES[language]['restrictions'] + '</p>', 'html.parser').p
        if replacement is None: node.decompose()
        else: node.replace_with(replacement)
    for node in result.select('#q-what-data p.collection-summary'):
        if node.get_text().endswith(('has not yet been described.', '的蒐集方式尚待說明。')):
            name = copy.deepcopy(node.strong); node.clear(); node['class'] = ['collection-context']; node.append(name)
    return result


def compact(value): return ''.join(value.split())


def compare(old, new, language):
    wanted = expected(old, language)
    assert compact(wanted.get_text()) == compact(new.get_text()), 'Unexpected prose, punctuation or answer change'
    assert not owned_gaps(new), 'A system diagnostic remains'
    for selector in ['.answer-detail', '[data-status="explicit-no"]']:
        assert [str(n) for n in old.select(selector)] == [str(n) for n in new.select(selector)], selector
    assert [(a.get('href'), a.get_text()) for a in old.select('a')] == [(a.get('href'), a.get_text()) for a in new.select('a')]
    assert [h.get_text() for h in old.select('.question > h3, .dmp-section > h2')] == [h.get_text() for h in new.select('.question > h3, .dmp-section > h2')]
    assert len(new.select('.question')) == 15 and len(new.select('.dmp-section')) == 6
    assert not new.select('p p, p div, p ul, p table')
    return dict(removed_notices=len(owned_gaps(old)), remaining_owned_notices=0,
                authored_blocks=len(new.select('.answer-detail')), explicit_no_nodes=len(new.select('[data-status="explicit-no"]')))


def run(english, extra=None):
    sys.path[:0] = [str(english / 'scripts'), str(english / 'tests')]
    from output_profile_contract import environment, WRAPPER
    result = []
    for language, locale in [('english', 'en'), ('chinese', 'zh-Hant')]:
        old = json.loads((ROOT / 'reviews/2026-09-21-budget-grouping-integration/package' / (language + '.json')).read_text())
        new, operations = patch(old, language); assert project(new, operations) == old
        for escaping in [False, True]:
            templates = [environment(english, escaping, {f['fileName']: f['content'] for f in package['files']}).from_string(WRAPPER) for package in [old, new]]
            sources = list(sorted((english / 'fixtures/pilot' / locale).glob('*.events.json')))
            if extra: sources += list(sorted((extra / locale).glob('notice-*.events.json')))
            for source in sources:
                replies = {e['path']: ({'value': {'value': e['value']['value']}} if e['value']['type'] == 'IntegrationReply' else e['value']['value']) for e in json.loads(source.read_text())}
                render = lambda template, **kw: template.render(repliesMap=replies, **kw)
                review = [render(t) for t in templates]
                assert review[0] == review[1], ('Default review changed', source.name)
                for mode in ['review', 'unknown']:
                    assert render(templates[1], output_profile=mode) == review[0]
                outputs = [BeautifulSoup(render(t, output_profile='submission'), 'html.parser') for t in templates]
                try: checked = compare(*outputs, language)
                except AssertionError as error: raise AssertionError((source.name, language, escaping, str(error))) from error
                if source.name.startswith('notice-'):
                    assert len(outputs[1].select('.answer-detail .data-gap')) >= 1, 'Authored diagnostic-looking HTML lost'
                    assert outputs[1].select('[data-fact-id="required-software-list"][data-status="partial"]')
                    assert outputs[1].select('[data-fact-id="quality-other"][data-status="partial"]')
                    assert outputs[1].select('[data-fact-id="reuse-restrictions"][data-status="partial"]')
                result.append(dict(case=source.name, language=language, autoescape=escaping, **checked))
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--english', type=Path, required=True); p.add_argument('--fixtures', type=Path)
    p.add_argument('--output', type=Path, required=True); a = p.parse_args(); assert not a.output.exists()
    result = dict(selected_checks_passed=False, release_acceptance=False, global_switch_complete=False,
                  checker_sha256=sha(Path(__file__)), recipe_sha256=sha(Path(__file__).with_name('notice_recipe.py')))
    try:
        result['rows'] = run(a.english.resolve(), a.fixtures)
        result['selected_checks_passed'] = True
    except Exception as error: result['failure'] = repr(error); raise
    finally: a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(cases=len(result['rows']), passed=True)))


if __name__ == '__main__': main()
