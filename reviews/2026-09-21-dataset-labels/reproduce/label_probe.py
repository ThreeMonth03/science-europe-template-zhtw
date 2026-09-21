"""Check labels against reply identities, then invert only owned label nodes."""
import copy
import itertools
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'experiments/submission-polish'), str(Path(__file__).parent)]
from polish_probe import compare as polish_compare, replies_from, compact
from label_recipe import patch, LABELS


def expected_order(replies):
    from generate_pilot_fixtures import IDS, path
    from test_science_europe_contract import reply_items, reply_str_value
    definitions = {
        'instrument': (path('creatingCUuid', 'measuredQUuid', 'measuredYesAUuid', 'measuredDataQUuid'), 'measuredDataNameQUuid'),
        'reference': (path('reusingCUuid', 'preexistingQUuid', 'preexistingYesAUuid', 'refDataQUuid'), 'refDataNameQUuid'),
        'non-reference': (path('reusingCUuid', 'preexistingQUuid', 'preexistingYesAUuid', 'nrefDataQUuid'), 'nrefDataNameQUuid'),
        'non-equipment': (path('creatingCUuid', 'neqDataQUuid', 'neqDataYesAUuid', 'neqDataSetsQUuid'), 'neqDataSetsNameQUuid'),
        'produced': (path('preservingCUuid', 'producedDataQUuid'), 'producedDataNameQUuid'),
    }
    lists = {}
    for kind, (prefix, field) in definitions.items():
        lists[kind] = [(kind, index, item) for index, item in enumerate(reply_items(replies.get(prefix)), 1)
                       if not reply_str_value(replies.get(path(prefix, item, field)))]
    if replies.get(path('creatingCUuid', 'measuredQUuid')) != IDS['measuredYesAUuid']: lists['instrument'] = []
    if replies.get(path('creatingCUuid', 'neqDataQUuid')) != IDS['neqDataYesAUuid']: lists['non-equipment'] = []
    if replies.get(path('reusingCUuid', 'preexistingQUuid')) != IDS['preexistingYesAUuid']:
        lists['reference'] = []; lists['non-reference'] = []
    legal = []
    for kind, prefix in [('reference', 'refData'), ('non-reference', 'nrefData')]:
        base = definitions[kind][0]
        for row in lists[kind]:
            used = path(base, row[2], prefix + 'UseQUuid')
            if replies.get(used) == IDS[prefix + 'UseYesAUuid'] and replies.get(path(used, prefix + 'UseYesAUuid', prefix + 'ConditionsQUuid')):
                legal.append(row)
    i, r, n, e, p = [lists[k] for k in ['instrument', 'reference', 'non-reference', 'non-equipment', 'produced']]
    return {'q-how-data': i + r + n, 'q-what-data': i + e, 'q-quality-control': i,
            'q-copyright-ipr': legal, 'q-ethical-issues': p, 'q-share-restrictions': p,
            'q-data-preservation': p, 'q-access-data': p, 'q-persistent-identifier': p + i}


def project_labels(new, language, replies):
    source = copy.deepcopy(new)
    ordering = expected_order(replies)
    labels = [n for n in source.select('.dataset-label') if not n.find_parent(class_='answer-detail')]
    by_question = {q: [] for q in ordering}
    for node in labels:
        question = node.find_parent(class_='question')['id']
        kind = node['data-list-kind']; index = int(node['data-list-index'])
        matching = [row for row in ordering[question] if row[:2] == (kind, index)]
        assert len(matching) == 1, ('Label does not identify an unnamed source item', question, kind, index)
        item = node.find_parent(attrs={'data-item-id': True})
        if item: assert item['data-item-id'].split('.')[-1] == matching[0][2], 'Dataset label is attached to a different item'
        assert node.get_text() == LABELS[language][kind] + ' ' + str(index)
        by_question[question].append((kind, index))
        node.replace_with('(no name given)' if language == 'english' else '（名稱尚未提供）')
    for question, expected in ordering.items():
        actual = [key for key, _ in itertools.groupby(by_question[question])]
        assert actual == [row[:2] for row in expected], (question, actual, expected, 'Filtered or reordered numbering')
    return source, len(labels)


def compare(old, new, language, replies):
    projected, count = project_labels(new, language, replies)
    polish_compare(old, projected, language, replies)
    return count


def run(english, extra=None):
    sys.path[:0] = [str(english / 'scripts'), str(english / 'tests')]
    from output_profile_contract import environment, WRAPPER
    from generate_pilot_fixtures import IDS
    fields = {IDS[k] for k in ['measuredDataNameQUuid', 'refDataNameQUuid', 'nrefDataNameQUuid', 'neqDataSetsNameQUuid', 'producedDataNameQUuid']}
    rows = []
    for language, locale in [('english', 'en'), ('chinese', 'zh-Hant')]:
        old = json.loads((ROOT / 'reviews/2026-09-21-submission-polish/package' / ('before-' + language + '.json')).read_text())
        new, _ = patch(old, language)
        for escape in [False, True]:
            templates = [environment(english, escape, {f['fileName']: f['content'] for f in data['files']}).from_string(WRAPPER) for data in [old, new]]
            sources = sorted((english / 'fixtures/pilot' / locale).glob('*.events.json'))
            if extra: sources += list((extra / locale).glob('*.events.json'))
            for path in sources:
                for nameless in [False, True]:
                    replies = replies_from(path)
                    if nameless: replies = {p: v for p, v in replies.items() if p.split('.')[-1] not in fields}
                    reviews = [t.render(repliesMap=replies) for t in templates]
                    assert reviews[0] == reviews[1], (path.name, language, escape, 'Review delta')
                    for mode in ['review', 'unknown']: assert templates[1].render(repliesMap=replies, output_profile=mode) == reviews[0]
                    old_html, new_html = [BeautifulSoup(t.render(repliesMap=replies, output_profile='submission'), 'html.parser') for t in templates]
                    try: count = compare(old_html, new_html, language, replies)
                    except AssertionError as error: raise AssertionError((path.name, language, escape, nameless, str(error))) from error
                    rows.append(dict(case=path.name, language=language, autoescape=escape, all_names_removed=nameless, labels=count, passed=True))
    return rows
