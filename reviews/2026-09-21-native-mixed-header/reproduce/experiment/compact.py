"""Losslessly externalize embedded public font data for compact input evidence."""
import base64
import hashlib
import re

FONT = re.compile(rb'data:font/ttf;base64,([A-Za-z0-9+/=]+)')
REFERENCE = re.compile(rb'data:font/ttf;sha256,([0-9a-f]{64})')


def compact_source(source):
    assert not REFERENCE.search(source), 'Already compacted'
    assets = {}
    def replace(match):
        data = base64.b64decode(match[1], validate=True)
        assert base64.b64encode(data) == match[1], 'Noncanonical base64'
        digest = hashlib.sha256(data).hexdigest()
        entry = assets.setdefault(digest, {'bytes': len(data), 'occurrences': 0})
        entry['occurrences'] += 1
        return b'data:font/ttf;sha256,' + digest.encode()
    result = FONT.sub(replace, source)
    assert assets
    return result, assets


def restore_source(source, assets):
    def replace(match):
        digest = match[1].decode()
        data = assets[digest]
        assert hashlib.sha256(data).hexdigest() == digest, 'Font bytes do not match'
        return b'data:font/ttf;base64,' + base64.b64encode(data)
    return REFERENCE.sub(replace, source)
