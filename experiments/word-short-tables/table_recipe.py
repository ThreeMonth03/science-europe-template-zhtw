"""Only add two shared Word-only files and extend the two Word format pipelines."""
import copy
import hashlib
import json
from pathlib import Path
import uuid

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
ARCHIVE = ROOT / 'reviews/2026-09-21-empty-budget'
SEAL = '3af4b110e89ebc277124a5f078ea46ec4693913f33f2a78884f5b8905d6198c2'
LUA = 'src/word/short-tables.lua'
XML = 'src/word/short-tables.xml.j2'
WORD_FORMATS = ['f4bd941a-dfbe-4226-a1fc-200fb5269311', '98081811-41ff-5438-b98a-0472607527c6']
IMAGE = 'sha256:6d3cbcab3294e760a4d92e27bec72d4fb23a0adb2cc1734d981478688741ab11'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def baseline(language):
    seal = ARCHIVE / 'checksums.json'; assert sha(seal.read_bytes()) == SEAL
    name = 'after/' + language + '.json'; raw = (ARCHIVE / name).read_bytes()
    assert sha(raw) == json.loads(seal.read_text())[name]
    return json.loads(raw)


def patch(data, language):
    assert data == baseline(language), 'Only the exact frozen empty-budget input is accepted'
    result = copy.deepcopy(data)
    assert not any(v['fileName'] in [LUA, XML] for v in data['assets'] + data['files'])
    ident = lambda path: str(uuid.uuid5(uuid.NAMESPACE_URL, 'science-europe/word-short-tables/v1/' + language + '/' + path))
    result['assets'].append(dict(fileName=LUA, contentType='application/octet-stream', uuid=ident(LUA)))
    result['files'].append(dict(fileName=XML, content=(HERE / 'short-tables.xml.j2').read_text(), uuid=ident(XML)))
    for fmt in result['formats']:
        if fmt['uuid'] not in WORD_FORMATS: continue
        assert len(fmt['steps']) == 2 and fmt['steps'][1]['name'] == 'pandoc'
        assert fmt['steps'][1]['options']['to'] == 'docx'
        fmt['steps'][1]['options']['args'] += ' --lua-filter=' + LUA
        fmt['steps'].append(dict(name='enrich-docx', options={'rewrite:word/document.xml': 'render:' + XML}))
    assert sum(f['uuid'] in WORD_FORMATS for f in result['formats']) == 2
    return result


def reverse(data, language):
    result = copy.deepcopy(data)
    asset = [a for a in result['assets'] if a['fileName'] == LUA]; assert len(asset) == 1
    file = [a for a in result['files'] if a['fileName'] == XML]; assert len(file) == 1
    assert file[0]['content'] == (HERE / 'short-tables.xml.j2').read_text()
    result['assets'].remove(asset[0]); result['files'].remove(file[0])
    for fmt in result['formats']:
        if fmt['uuid'] not in WORD_FORMATS: continue
        assert fmt['steps'].pop() == dict(name='enrich-docx', options={'rewrite:word/document.xml': 'render:' + XML})
        args = fmt['steps'][1]['options']['args']; suffix = ' --lua-filter=' + LUA
        assert args.endswith(suffix); fmt['steps'][1]['options']['args'] = args[:-len(suffix)]
    assert result == baseline(language)
    assert data == patch(result, language)
    return result
