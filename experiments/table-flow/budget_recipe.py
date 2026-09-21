"""Skip source-owned empty budget groups, never filter the project iterator."""
import copy
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / 'reviews/2026-09-21-ethics-lead'
SEAL = '9015bf798a4fb25db040d2abf713ed497f8ffa4184a0896ea422eafc7947d4ef'
TARGET = 'src/questions/15-required-resources.html.j2'


def baseline(language):
    seal = ARCHIVE / 'checksums.json'
    assert hashlib.sha256(seal.read_bytes()).hexdigest() == SEAL
    name = 'after/' + language + '.json'; raw = (ARCHIVE / name).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == json.loads(seal.read_text())[name]
    return json.loads(raw)


def patch(data, language):
    assert data == baseline(language), 'Only the exact frozen Q9-lead input is accepted'
    result = copy.deepcopy(data)
    file = next(f for f in result['files'] if f['fileName'] == TARGET)
    source = file['content']; operations = []

    def edit(pattern, replace, kind):
        matches = list(re.finditer(pattern, source)); assert len(matches) == 1, (language, kind)
        match = matches[0]
        operations.append(dict(start=match.start(), end=match.end(), before=match[0], after=replace(match[0]), kind=kind))

    scan = ("{%- set visibleBudget = namespace(any=false) -%}"
            "{%- for budgetProject in projectItems -%}"
            "{%- if repliesMap[[projectPath, budgetProject, uuids.costQUuid]|reply_path]|reply_items -%}"
            "{%- set visibleBudget.any = true -%}{%- endif -%}{%- endfor -%}")
    edit(r'<h4>[^<]+</h4>', lambda old: scan +
         "{% if output_profile|default('review') != 'submission' or visibleBudget.any %}" + old + '{% endif %}',
         'omit-heading-without-cost-items')
    edit(re.escape('<div class="project-resources" data-item-id="{{ projectItem }}">'),
         lambda old: "{% if output_profile|default('review') != 'submission' or repliesMap[[projectItem, uuids.costQUuid]|reply_path]|reply_items %}" + old,
         'guard-empty-project-budget')
    edit(r'</div>(?=\s+\{%- endfor -%\}\s+\{%- else -%\})',
         lambda old: old + '{% endif %}', 'close-empty-project-budget-guard')
    operations.sort(key=lambda op: op['start'])
    assert all(a['end'] <= b['start'] for a, b in zip(operations, operations[1:]))
    for op in reversed(operations): source = source[:op['start']] + op['after'] + source[op['end']:]
    file['content'] = source
    return result, {TARGET: operations}
