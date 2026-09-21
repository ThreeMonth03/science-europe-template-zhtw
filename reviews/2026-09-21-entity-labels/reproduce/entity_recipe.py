"""Bounded 0.3.44 package experiment; never rewrite a rendered document.

The paired source/translation integration is deliberately a later gate. Only
five Jinja files change; review bytes and all assets/metadata stay identical.
"""
import copy
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / 'reviews/2026-09-21-submission-preview-integration'
SEAL = '91c722c3fa9e436c8ffd517f8b24e3d1e1d4ed274dfba769ed41e9da36c7ddbf'
SUBMIT = "output_profile|default('review') == 'submission'"
LABELS = {'english': {'project': 'Project', 'resource': 'Resource', 'software': 'Software tool'},
          'chinese': {'project': '計畫', 'resource': '資源', 'software': '軟體工具'}}


def baseline(language):
    seal = BASELINE / 'checksums.json'
    assert hashlib.sha256(seal.read_bytes()).hexdigest() == SEAL
    name = 'package/' + language + '.json'
    raw = (BASELINE / name).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == json.loads(seal.read_text())[name]
    return json.loads(raw)


def macros(language):
    return ''.join('\n{%- macro ' + kind + 'Label(index) -%}'
        + text + ' {{ index }}{%- endmacro -%}\n'
        for kind, text in LABELS[language].items())


def patch(data, language):
    assert data == baseline(language), 'Only the frozen, verified 0.3.44 input is accepted'
    result = copy.deepcopy(data); operations = {}
    for file in result['files']:
        name, source = file['fileName'], file['content']; edits = []

        def replace(pattern, replacement, kind):
            found = list(re.finditer(pattern, source, re.S))
            assert len(found) == 1, (name, kind, len(found))
            match = found[0]
            edits.append(dict(start=match.start(), end=match.end(), before=match[0],
                              after=replacement(match[0]), kind=kind))

        def label(kind, index):
            return '{{ macros.' + kind + 'Label(' + index + ') }}'

        def fallback(variable, kind, index, placeholder):
            pattern = (r'\{\{\s*' + re.escape(variable) + r'(?:\|e)? if ' + re.escape(variable)
                       + r' else "' + re.escape(placeholder) + r'"\s*\}\}') if language == 'english' else (
                       r'\{% if ' + re.escape(variable) + r' %\}.*?\{% else %\}.*?\{% endif %\}')
            replace(pattern, lambda old: '{% if ' + SUBMIT + ' and not ' + variable + ' %}'
                    + label(kind, index) + '{% else %}' + old + '{% endif %}', kind)

        if name == 'src/projects.html.j2':
            replace(r'<h3 class="empty-value">[^<]*</h3>',
                lambda old: '{% if ' + SUBMIT + ' %}<h3>' + label('project', 'projectsItems.index(projectsItem) + 1')
                + '</h3>{% else %}' + old + '{% endif %}', 'project-overview')
        elif name == 'src/questions/09-ethical-issues.html.j2':
            replace(re.escape("{'name': projectName, 'approval': projEthicalApprovalAUuid, 'authorities': projAuth}"),
                lambda old: old[:-1] + ", 'index': projectsItems.index(projectItem) + 1}", 'unfiltered-project-identity')
            fallback('project.name', 'project', 'project.index', '(no name given)')
        elif name == 'src/questions/12-access-data.html.j2':
            fallback('swNameReply', 'software', 'isPublishedSwItems.index(swItem) + 1', '(no name given)')
        elif name == 'src/questions/15-required-resources.html.j2':
            if language == 'english':
                fallback('projectItemNameReply', 'project', 'projectItems.index(i) + 1', '(no name given)')
            else:
                # The translator lifted this conditional to a whole sentence.
                # Only its missing-name branch changes; keep all named bytes.
                replace(r'<p><strong>（計畫名稱尚未提供）(.*?)</strong></p>',
                    lambda old: old.replace('（計畫名稱尚未提供）', '{% if ' + SUBMIT + ' %}'
                        + label('project', 'projectItems.index(i) + 1') + '{% else %}（計畫名稱尚未提供）{% endif %}'),
                    'project-budget')
            fallback('projectCostItemTitleReply', 'resource', 'projectCostItems.index(j) + 1', '(no resource name given)')
        elif name == 'src/macros.html.j2':
            edits.append(dict(start=len(source), end=len(source), before='', after=macros(language), kind='helpers'))
        edits.sort(key=lambda op: op['start'])
        assert all(a['end'] <= b['start'] for a, b in zip(edits, edits[1:]))
        for op in reversed(edits):
            source = source[:op['start']] + op['after'] + source[op['end']:]
        if edits: operations[name] = edits
        file['content'] = source
    assert len(operations) == 5 and sum(map(len, operations.values())) == 7
    return result, operations


def reverse(data, operations):
    result = copy.deepcopy(data)
    for file in result['files']:
        value = file['content']
        for op in operations.get(file['fileName'], []):
            start = op['start']
            assert value[start:start + len(op['after'])] == op['after']
            value = value[:start] + op['before'] + value[start + len(op['after']):]
        file['content'] = value
    return result
