"""Fail-closed mechanical patch for one pinned, isolated worker image only."""
import hashlib
import importlib.util
from pathlib import Path

path = Path(importlib.util.find_spec('dsw.document_worker.model.utils').origin)
original = path.read_bytes()
expected = 'a908edd89d700914a7fbddbd54d10c5178df63c65c5b48308207e57db3eb9d82'
if hashlib.sha256(original).hexdigest() != expected:
    raise SystemExit('Worker source differs from the reviewed baseline; refusing patch')
anchor = b'            DSWMarkdownExt(),\n'
if original.count(anchor) != 1:
    raise SystemExit('Expected exactly one reviewed Markdown extension location')
patched = original.replace(anchor, anchor + b"            'tables',\n")
path.write_bytes(patched)
print('Patched Markdown tables; source SHA256:', hashlib.sha256(patched).hexdigest())
