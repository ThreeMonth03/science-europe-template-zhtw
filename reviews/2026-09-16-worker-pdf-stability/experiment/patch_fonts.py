"""Backport two upstream ownership fixes to one reviewed WeasyPrint 68.1 source.

No layout changes or dependency upgrade. See README.md for upstream attribution.
"""
import hashlib
import importlib.util
from pathlib import Path

EXPECTED = {
    'fonts': '3f6662edc1f0a11e1666c39f9b72a2d2543769162ee985b216c2afbddd0312a1',
    'ffi': 'd7784b995d7d4624eca4a1e76bf46564c6abe82a53207c0f0cf48657516684d7',
}
REPLACEMENTS = {
    'fonts': [
        (b'self._config = ffi.gc(\n            fontconfig.FcInitLoadConfigAndFonts(), fontconfig.FcConfigDestroy)',
         b'self._config = fontconfig.FcInitLoadConfigAndFonts()'),
        (b'    return pangoft2.pango_fc_font_map_get_hb_face(fontmap, fc_font)',
         b'    hb_face = pangoft2.pango_fc_font_map_get_hb_face(fontmap, fc_font)\n'
         b'    return ffi.gc(harfbuzz.hb_face_reference(hb_face), harfbuzz.hb_face_destroy)'),
    ],
    'ffi': [(b'    void hb_face_destroy (hb_face_t *face);',
             b'    hb_face_t * hb_face_reference (hb_face_t *face);\n'
             b'    void hb_face_destroy (hb_face_t *face);')],
}


def patched_sources(sources):
    """Validate every original before returning any replacement (fail closed)."""
    if set(sources) != set(EXPECTED):
        raise ValueError('Expected exactly fonts and ffi sources')
    result = {}
    for name, original in sources.items():
        if hashlib.sha256(original).hexdigest() != EXPECTED[name]:
            raise ValueError(f'{name}: source differs from pinned WeasyPrint; refusing patch')
        patched = original
        for old, new in REPLACEMENTS[name]:
            if patched.count(old) != 1:
                raise ValueError(f'{name}: expected exactly one reviewed anchor')
            patched = patched.replace(old, new)
        compile(patched, name, 'exec')
        result[name] = patched
    return result


def main():
    paths = {name: Path(importlib.util.find_spec('weasyprint.text.'+name).origin) for name in EXPECTED}
    result = patched_sources({name: path.read_bytes() for name, path in paths.items()})
    for name, content in result.items():
        paths[name].write_bytes(content)
        print(name, hashlib.sha256(content).hexdigest())


if __name__ == '__main__':
    main()
