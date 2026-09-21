"""Neutral dataset labels use the original questionnaire-list position, not a filtered loop."""
import copy
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'experiments/submission-polish'), str(ROOT / 'experiments/submission-notices')]
from polish_recipe import patch as polish_patch, SUBMIT
from notice_recipe import project as reverse

LABELS = {
    'english': {'instrument': 'Instrument dataset', 'reference': 'Reference dataset',
                'non-reference': 'Non-reference dataset', 'non-equipment': 'Non-equipment dataset', 'produced': 'Produced dataset'},
    'chinese': {'instrument': '儀器資料集', 'reference': '參考資料集',
                'non-reference': '非參考資料集', 'non-equipment': '非儀器資料集', 'produced': '產出資料集'},
}
EXPRESSIONS = {
    'src/questions/01-how-data.html.j2': [('measuredDataName', 'instrument', 'measuredDataItems', 'datasetItem')],
    'src/questions/02-what-data.html.j2': [('neqDataSetsName', 'non-equipment', 'neqDataSetsItems', 'neqDataSetItem')],
    'src/questions/09-ethical-issues.html.j2': [('producedDataName', 'produced', 'producedDataItems', 'i')],
    'src/questions/10-share-restrictions.html.j2': [('producedDataName', 'produced', 'producedDataItems', 'i')],
    'src/questions/11-data-preservation.html.j2': [('producedDataName', 'produced', 'producedDataItems', 'i')],
    'src/questions/12-access-data.html.j2': [('producedDataName', 'produced', 'producedDataItems', 'i')],
    'src/questions/13-persistent-identifier.html.j2': [('producedDataName', 'produced', 'producedDataItems', 'i'),
        ('measuredDataNameReply', 'instrument', 'dataMeasuredItems', 'k')],
}
BLOCKS = {
    'src/questions/01-how-data.html.j2': [('strong', 'reference', 'refDataItems', 'refDataItem'), ('strong', 'non-reference', 'nrefDataItems', 'nrefDataItem')],
    'src/questions/02-what-data.html.j2': [('span', 'instrument', 'measuredDataItems', 'datasetItem')],
    'src/quality-control.html.j2': [('span', 'instrument', 'measuredDataItems', 'datasetItem')],
    'src/questions/08-copyright-ipr.html.j2': [('div', 'reference', 'refDataItems', 'i'), ('div', 'non-reference', 'nrefDataItems', 'i')],
}


def macro(language):
    branches = ''.join(('{%- if' if i == 0 else '{%- elif') + ' kind == "' + kind + '" -%}' + label
                       for i, (kind, label) in enumerate(LABELS[language].items()))
    # The caller has a classified list and a real member; no invented fallback
    # for an unknown kind or a lost item identity is allowed.
    return ('\n{%- macro datasetLabel(kind, index) -%}'
            '<span class="dataset-label" data-list-kind="{{ kind }}" data-list-index="{{ index }}">' +
            branches + '{%- endif %} {{ index }}</span>{%- endmacro -%}\n')


def patch(data, language):
    base, previous = polish_patch(data, language)
    result = copy.deepcopy(base); operations = {}
    for file in result['files']:
        name, source = file['fileName'], file['content']; edits = []
        def add(match, replacement, kind):
            edits.append(dict(start=match.start(), end=match.end(), before=match[0], after=replacement, kind=kind))
        def label(kind, items, item):
            return '{{ macros.datasetLabel("' + kind + '", ' + items + '.index(' + item + ') + 1) }}'
        for variable, kind, items, item in EXPRESSIONS.get(name, []):
            if language == 'english':
                pattern = r'\{\{\s*' + variable + r'(?:\|e)? if ' + variable + r' else "\(no name given\)"\s*\}\}'
            else:
                pattern = r'\{% if ' + variable + r' %\}.*?\{% else %\}.*?\{% endif %\}'
            matches = list(re.finditer(pattern, source, re.S)); assert len(matches) == 1, (name, variable)
            old = matches[0]
            replacement = '{% if ' + SUBMIT + ' and not ' + variable + ' %}' + label(kind, items, item) + '{% else %}' + old[0] + '{% endif %}'
            add(old, replacement, kind)
        blocks = BLOCKS.get(name, [])
        if blocks:
            tag = blocks[0][0]; assert all(b[0] == tag for b in blocks)
            text = r'\(no name given\)' if language == 'english' else '（名稱尚未提供）'
            pattern = '<' + tag + r'>(?:\{#.*?#\}\s*)*' + text + r'(?:\s*\{#.*?#\})*</' + tag + '>'
            matches = list(re.finditer(pattern, source, re.S)); assert len(matches) == len(blocks), (name, len(matches))
            for match, (_, kind, items, item) in zip(matches, blocks):
                replacement = '{% if ' + SUBMIT + ' %}<' + tag + '>' + label(kind, items, item) + '</' + tag + '>{% else %}' + match[0] + '{% endif %}'
                add(match, replacement, kind)
        if name == 'src/macros.html.j2':
            edits.append(dict(start=len(source), end=len(source), before='', after=macro(language), kind='shared-label-helper'))
        edits.sort(key=lambda o: o['start'])
        assert all(a['end'] <= b['start'] for a, b in zip(edits, edits[1:])), (name, 'Overlapping edits')
        for op in reversed(edits): source = source[:op['start']] + op['after'] + source[op['end']:]
        if edits: operations[name] = edits
        file['content'] = source
    assert sum(len(v) for v in operations.values()) == 15
    assert reverse(result, operations) == base
    return result, dict(**previous, labels=operations)
