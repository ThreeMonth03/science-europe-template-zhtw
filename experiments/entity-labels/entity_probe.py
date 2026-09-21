"""Independent reply-to-DOM oracle, including filtered and nested identities."""
import copy
import json
from pathlib import Path
import sys
from bs4 import BeautifulSoup
from entity_recipe import baseline, patch, LABELS, ROOT


def replies_from(source):
    return {e['path']: ({'value': {'value': e['value']['value']}}
            if e['value']['type'] == 'IntegrationReply' else e['value']['value'])
            for e in json.loads(source.read_text())}


def expected(old, language, replies):
    """Change only specific owned name nodes; all other facts/DOM are exact."""
    from generate_pilot_fixtures import IDS, path
    from test_science_europe_contract import reply_items, reply_str_value
    result = copy.deepcopy(old); changed = []
    items = lambda p: reply_items(replies.get(p))
    value = lambda p: reply_str_value(replies.get(p))

    def replace(node, kind, index, identity, placeholder):
        assert node is not None and node.get_text() == placeholder, (kind, identity, node)
        assert not node.find_parent(class_='answer-detail')
        node.clear(); node.append(LABELS[language][kind] + ' ' + str(index))
        changed.append(dict(kind=kind, index=index, identity=identity))

    project_path = path('adminDetailsCUuid', 'projectsQUuid')
    projects = items(project_path)
    overviews = result.select('#dmp-projects > .project')
    budgets = result.select('#q-required-resources .project-resources')
    assert len(overviews) == len(budgets) == len(projects)
    approvals = result.select('#q-ethical-issues .ethical-project')
    approved = [p for p in projects if value(path(project_path, p, 'projEthicalApprovalQUuid')) in
                [IDS['projEthicalApprovalYesAUuid'], IDS['projEthicalApprovalNoAUuid']]]
    assert len(approvals) == len(approved)
    for index, project in enumerate(projects, 1):
        prefix = path(project_path, project)
        budget = budgets[index - 1]; assert budget['data-item-id'] == prefix
        if not value(path(prefix, 'projectNameQUuid')):
            overview = overviews[index - 1].find('h3', recursive=False)
            replace(overview, 'project', index, prefix,
                    '(project name not given)' if language == 'english' else '（尚未提供專案名稱）')
            assert overview.get('class') == ['empty-value']; del overview['class']
            if project in approved:
                replace(approvals[approved.index(project)].find('strong', recursive=False), 'project', index, prefix,
                        '(no name given)' if language == 'english' else '（名稱尚未提供）')
            if len(projects) > 1:
                node = budget.find('p', recursive=False).strong
                placeholder = '(no name given)' if language == 'english' else '（計畫名稱尚未提供）'
                number = value(path(prefix, 'projectNumberQUuid'))
                tail = (' - ' + number if number else '') + (' ' if language == 'english' else '')
                assert node.get_text() == placeholder + tail
                node.clear(); node.append(LABELS[language]['project'] + ' ' + str(index) + tail)
                changed.append(dict(kind='project', index=index, identity=prefix))
        cost_path = path(prefix, 'costQUuid')
        for cost_index, cost in enumerate(items(cost_path), 1):
            cost_prefix = path(cost_path, cost)
            if value(path(cost_prefix, 'costTitleQUuid')): continue
            # Layout may have transformed a long row into a table. Both carry
            # the complete original item path; never address by filtered order.
            owners = budget.select('[data-item-id="' + cost_prefix + '"]')
            assert len(owners) == 1, ('Ambiguous resource owner', cost_prefix)
            node = owners[0].select_one('td > p > strong')
            replace(node, 'resource', cost_index, cost_prefix,
                    '(no resource name given)' if language == 'english' else '（尚未填寫資源名稱）')
    produced = path('preservingCUuid', 'producedDataQUuid')
    datasets = result.select('#q-access-data > .answer > .dataset-section')
    assert len(datasets) == len(items(produced))
    for dataset, node in zip(items(produced), datasets):
        assert node['data-item-id'] == dataset
        published = path(produced, dataset, 'isPublishedDataQUuid')
        use = path(published, 'isPublishedDataYesAUuid', 'publishedSpecSwUseQUuid')
        if value(published) != IDS['isPublishedDataYesAUuid'] or value(use) != IDS['publishedSpecSwUseYesAUuid']: continue
        software = path(use, 'publishedSpecSwUseYesAUuid', 'publishedSpecSwUseWhatQUuid')
        names = node.select(':scope > ul > li > strong')
        assert len(names) == len(items(software))
        for index, (tool, name_node) in enumerate(zip(items(software), names), 1):
            prefix = path(software, tool)
            if not value(path(prefix, 'publishedSpecSwUseWhatNameQUuid')):
                replace(name_node, 'software', index, prefix,
                        '(no name given)' if language == 'english' else '（名稱尚未提供）')
    return result, changed


def compare(old, new, language, replies):
    from probe_pdf_budget_reading import dom
    projected, changes = expected(old, language, replies)
    assert dom(projected) == dom(new), 'Unexpected text, numbering, layout or ownership delta'
    assert len(new.select('.question')) == 15 and len(new.select('.dmp-section')) == 6
    assert not new.select('p p, p table, p ul, p div')
    return changes


def templates(english, language, escape, word=False):
    from output_profile_contract import environment, WRAPPER
    wrapper = WRAPPER.replace("{% include 'src/content.html.j2' %}",
        "{% include 'src/contributors.html.j2' %}{% include 'src/content.html.j2' %}")
    if word: wrapper = '{% set word_budget_reading = true %}' + wrapper
    old = baseline(language); new, _ = patch(old, language)
    return [environment(english, escape, {f['fileName']: f['content'] for f in d['files']}).from_string(wrapper)
            for d in [old, new]]


def check_case(pair, replies, language):
    context = dict(repliesMap=replies, dc={'project': {'created_by': None}, 'e': {'choices': {}}})
    review = pair[0].render(**context)
    for mode in [None, 'review', 'unknown']:
        options = {} if mode is None else {'output_profile': mode}
        assert pair[1].render(**context, **options) == review, 'Review bytes changed'
    old, new = [BeautifulSoup(t.render(**context, output_profile='submission'), 'html.parser') for t in pair]
    changes = compare(old, new, language, replies)
    return old, new, changes


def run(english, extra=None):
    sys.path[:0] = [str(english / 'scripts'), str(english / 'tests')]
    from generate_pilot_fixtures import IDS
    from artifact_utils import sha
    fields = {IDS[k] for k in ['projectNameQUuid', 'costTitleQUuid', 'publishedSpecSwUseWhatNameQUuid']}
    rows = []
    for language, locale in [('english', 'en'), ('chinese', 'zh-Hant')]:
        sources = list((english / 'fixtures/pilot' / locale).glob('*.events.json'))
        if extra: sources += list((extra / locale).glob('*.events.json'))
        for escape in [False, True]:
            for word in [False, True]:
                pair = templates(english, language, escape, word)
                for source in sorted(sources):
                    for nameless in [False, True]:
                        replies = replies_from(source)
                        if nameless: replies = {p: v for p, v in replies.items() if p.split('.')[-1] not in fields}
                        try: _, _, changes = check_case(pair, replies, language)
                        except AssertionError as error:
                            raise AssertionError((source.name, language, escape, word, nameless, str(error))) from error
                        rows.append(dict(case=source.name, language=language, autoescape=escape, word_layout=word,
                            all_names_removed=nameless, changes=changes, fixture_sha256=sha(source), passed=True))
    return rows
