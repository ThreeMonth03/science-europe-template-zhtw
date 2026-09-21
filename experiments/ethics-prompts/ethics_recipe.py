"""Two Q9 owned prompt branches, layered on the frozen entity-label prototype."""
import copy
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / 'reviews/2026-09-21-entity-labels'
SEAL = '567daf5949fea60ca22887a06b8a16fd138bb0bbc4bbd1a150efae9d544aff7b'
TARGET = 'src/questions/09-ethical-issues.html.j2'
SUBMIT = "output_profile|default('review') == 'submission'"
TEXT = {
    'english': {
        'flags': 'no information on personal nor sensitive data.',
        'old': 'An alternative legal basis was selected, but it has not been specified; see Question 7.',
        'new': 'An alternative legal basis was selected.',
        'lead': 'We will collect data related to individuals, i.e. "personal data".',
    },
    'chinese': {
        'flags': '尚未說明是否包含個人資料或敏感資料。',
        'old': '本計畫選擇了其他法律依據，但尚未說明具體依據；請參閱第 7 題。',
        'new': '本計畫已選擇其他法律依據。',
        'lead': '我們將蒐集與個人相關的資料，即「個人資料」。',
    },
}


def baseline(language):
    seal = ARCHIVE / 'checksums.json'
    assert hashlib.sha256(seal.read_bytes()).hexdigest() == SEAL
    name = 'after/' + language + '.json'; raw = (ARCHIVE / name).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == json.loads(seal.read_text())[name]
    return json.loads(raw)


def patch(data, language):
    assert data == baseline(language), 'Only the exact reviewed entity-label input is accepted'
    result = copy.deepcopy(data)
    file = next(f for f in result['files'] if f['fileName'] == TARGET)
    source = file['content']; edits = []
    def edit(pattern, replacement, kind):
        matches = list(re.finditer(pattern, source, re.S)); assert len(matches) == 1, (language, kind)
        m = matches[0]
        edits.append(dict(start=m.start(), end=m.end(), before=m[0], after=replacement(m[0]), kind=kind))
    edit(r'<span> - <em>(?:\{#.*?#\})?' + re.escape(TEXT[language]['flags']) + r'(?:\{#.*?#\})?</em></span>',
         lambda old: '{% if ' + SUBMIT + ' %}{% else %}' + old + '{% endif %}', 'missing-data-flags')
    statement = "{%- do sentences.append('" + TEXT[language]['old'] + "') -%}"
    edit(re.escape(statement), lambda old: '{%- if ' + SUBMIT + " -%}{%- do sentences.append('"
         + TEXT[language]['new'] + "') -%}{%- else -%}" + old + '{%- endif -%}', 'other-basis-partial-fact')
    edits.sort(key=lambda e: e['start']); assert edits[0]['end'] <= edits[1]['start']
    for op in reversed(edits): source = source[:op['start']] + op['after'] + source[op['end']:]
    file['content'] = source
    return result, {TARGET: edits}
