"""Expose only the first source-owned Q9 lead; do not keep a whole answer."""
import copy
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / 'reviews/2026-09-21-ethics-prompts'
SEAL = '7bbe9c7eb8bc9dffbfa818271e796e528af3f5ef8241063216761eb68f1b6a34'
TARGET = 'src/questions/09-ethical-issues.html.j2'
FIELDS = ['cpersExplainInformed', 'cpersDescribeProcedure', 'cpersGdprPurpose']


def baseline(language):
    seal = ARCHIVE / 'checksums.json'
    assert hashlib.sha256(seal.read_bytes()).hexdigest() == SEAL
    name = 'after/' + language + '.json'; raw = (ARCHIVE / name).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == json.loads(seal.read_text())[name]
    return json.loads(raw)


def patch(data, language):
    assert data == baseline(language), 'Only the exact frozen Q9-prompt input is accepted'
    result = copy.deepcopy(data)
    file = next(f for f in result['files'] if f['fileName'] == TARGET)
    source = file['content']; operations = []
    def edit(pattern, replace, kind):
        matches = list(re.finditer(pattern, source)); assert len(matches) == 1, (language, kind)
        match = matches[0]
        operations.append(dict(start=match.start(), end=match.end(), before=match[0], after=replace(match[0]), kind=kind))
    edit(r"<strong>(?=\{% if output_profile\|default\('review'\) == 'submission' and not producedDataName %\})",
         lambda _: '<strong{% if output_profile|default(\'review\') == \'submission\' and loop.last and not containPersonal and not containSensitive %} style="break-after: auto"{% endif %}>',
         'release-final-name-only-item')
    edit(r"\{%- set sentences = \[.*?\] -%\}",
         lambda old: old + '{%- set ethicsLead = namespace(first=none) -%}', 'initialize-owned-boundary')
    for field in FIELDS:
        edit(re.escape('{%- do sentences.append(' + field + '|markdown) -%}'),
             lambda old: '{%- if ethicsLead.first is none -%}{%- set ethicsLead.first = sentences|length -%}{%- endif -%}' + old,
             'record-first-' + field)
    join = "' '" if language == 'english' else '""'
    old = '<div class="answer-detail">{{ sentences|join(' + join + ') }}</div>'
    replacement = ('{% if output_profile|default(\'review\') == \'submission\' and ethicsLead.first is not none %}'
        '<div class="answer-detail"><p class="answer-lead" style="margin-bottom: 0">{{ sentences[:ethicsLead.first]|join(' + join + ') }}</p>'
        '{{ sentences[ethicsLead.first:]|join(' + join + ') }}</div>{% else %}' + old + '{% endif %}')
    edit(re.escape(old), lambda _: replacement, 'render-owned-lead-in-submission')
    operations.sort(key=lambda op: op['start'])
    assert all(a['end'] <= b['start'] for a, b in zip(operations, operations[1:]))
    for op in reversed(operations): source = source[:op['start']] + op['after'] + source[op['end']:]
    file['content'] = source
    return result, {TARGET: operations}
