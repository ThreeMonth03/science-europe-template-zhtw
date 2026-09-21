"""Move one exact machine helper from translated template text to shared asset."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
ARCHIVE = ROOT / 'reviews/2026-09-21-word-short-tables'
SEAL = 'ef2fad262a2615ab5eeb35a40a6e8513adb68678171c0ae5753de4e8b75a8fb9'
sys.path.insert(0, str(ROOT / 'experiments/word-short-tables'))
from table_recipe import LUA, XML as OLD_XML, WORD_FORMATS, IMAGE
XML = OLD_XML.removesuffix('.j2')
CASES = ['ethics-missing', 'ethics-answered', 'ethics-long']


def sha(data): return hashlib.sha256(data).hexdigest()


def baseline(language):
    seal = ARCHIVE / 'checksums.json'; assert sha(seal.read_bytes()) == SEAL
    name = 'after/' + language + '.json'; raw = (ARCHIVE / name).read_bytes()
    assert sha(raw) == json.loads(seal.read_text())[name]
    return json.loads(raw)


def helper():
    values = [next(f['content'] for f in baseline(lang)['files'] if f['fileName'] == OLD_XML)
              for lang in ['english', 'chinese']]
    assert values[0] == values[1]
    return values[0].encode()


def patch(data, language):
    assert data == baseline(language)
    result = copy.deepcopy(data)
    file = next(f for f in result['files'] if f['fileName'] == OLD_XML)
    assert file['content'].encode() == helper()
    assert not any(f['fileName'] == XML for f in result['files'] + result['assets'])
    result['files'].remove(file)
    result['assets'].append(dict(fileName=XML, contentType='application/xml',
        uuid=str(uuid.uuid5(uuid.NAMESPACE_URL, 'science-europe/word-asset/v1/' + language + '/' + XML))))
    for fmt in result['formats']:
        if fmt['uuid'] not in WORD_FORMATS: continue
        assert fmt['steps'][-1] == dict(name='enrich-docx', options={'rewrite:word/document.xml': 'render:' + OLD_XML})
        fmt['steps'][-1]['options']['rewrite:word/document.xml'] = 'render:' + XML
    return result


def reverse(data, language):
    assert data == patch(baseline(language), language)
    result = copy.deepcopy(data); old = baseline(language)
    result['assets'].remove(next(a for a in result['assets'] if a['fileName'] == XML))
    file = next(f for f in old['files'] if f['fileName'] == OLD_XML)
    result['files'].insert(old['files'].index(file), file)
    for fmt in result['formats']:
        if fmt['uuid'] in WORD_FORMATS:
            fmt['steps'][-1]['options']['rewrite:word/document.xml'] = 'render:' + OLD_XML
    assert result == old
    return result
