"""Offline pinned-worker lifecycle diagnostic, not a full native export."""
import faulthandler
import gc
import hashlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import resource
import sys
import time
from types import SimpleNamespace

faulthandler.enable(all_threads=True)
from dsw.document_worker.documents import DocumentFile, FileFormats
from dsw.document_worker.templates.steps.conversion import WeasyPrintStep


def emit(event, **values):
    print(json.dumps({'event': event, **values}), flush=True)


def font_lifetime(path):
    """Adapt the upstream #2799 regression to our bundled, static CJK font.

    Deliberately release the Pango owners before subsetting. This is a targeted
    ownership test, not a reproduction of the historical DSW queue crash.
    """
    from weasyprint import CSS
    from weasyprint.pdf.fonts import Font
    from weasyprint.text.ffi import ffi, gobject, pango
    from weasyprint.text.fonts import FontConfiguration
    font_config = FontConfiguration()
    CSS(string='@font-face {font-family: lifetime; src: url("'+path.as_uri()+'");}',
        font_config=font_config)
    context = ffi.gc(pango.pango_font_map_create_context(font_config.font_map), gobject.g_object_unref)
    description = ffi.gc(pango.pango_font_description_new(), pango.pango_font_description_free)
    pango.pango_font_description_set_family(description, ffi.new('char[]', b'lifetime'))
    pango_font = ffi.gc(pango.pango_font_map_load_font(font_config.font_map, context, description), gobject.g_object_unref)
    font = Font(pango_font, description, 10)
    del context, description, pango_font, font_config
    gc.collect()
    emit('owners-released')
    font.clean({1: 'a', 2: 'b'}, hinting=False)
    emit('subset-complete')


def main():
    settings = json.load(sys.stdin)
    source = Path(importlib.util.find_spec('dsw.document_worker.templates.steps.conversion').origin)
    emit('environment', versions={n: importlib.metadata.version(n) for n in ['weasyprint', 'cffi', 'pydyf', 'fonttools']},
        python=sys.version, conversion_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        gc_threshold=gc.get_threshold(), gc_policy=settings['gc_policy'])
    if settings.get('probe') == 'font-lifetime':
        for iteration, name in enumerate(settings['sequence'], 1):
            emit('lifetime-start', iteration=iteration)
            font_lifetime(Path('/sources')/name)
            gc.collect()
            emit('lifetime-complete', iteration=iteration)
        emit('complete', iterations=len(settings['sequence']))
        return
    step = WeasyPrintStep(SimpleNamespace(template_dir=Path('/sources')), {})
    for iteration, name in enumerate(settings['sequence'], 1):
        content = (Path('/sources')/name).read_bytes()
        emit('render-start', iteration=iteration, source=name, source_sha256=hashlib.sha256(content).hexdigest())
        started = time.monotonic()
        result = step.execute_follow(DocumentFile(FileFormats.HTML, content), {})
        data = result.content
        emit('render-complete', iteration=iteration, source=name, seconds=round(time.monotonic()-started, 3),
            bytes=len(data), pdf_sha256=hashlib.sha256(data).hexdigest(), rss_max_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        if settings.get('save_all') or iteration == 1 or iteration == len(settings['sequence']):
            (Path('/out')/f'sample-{iteration:03d}.pdf').write_bytes(data)
        del result, data, content
        if settings['gc_policy'] == 'after-each':
            emit('gc-start', iteration=iteration)
            collected = gc.collect()
            emit('gc-complete', iteration=iteration, collected=collected)
    emit('final-gc-start')
    collected = gc.collect()
    emit('complete', renders=len(settings['sequence']), final_collected=collected)


if __name__ == '__main__': main()
