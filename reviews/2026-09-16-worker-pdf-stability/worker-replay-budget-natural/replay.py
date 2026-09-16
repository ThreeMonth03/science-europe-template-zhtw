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


def main():
    settings = json.load(sys.stdin)
    source = Path(importlib.util.find_spec('dsw.document_worker.templates.steps.conversion').origin)
    emit('environment', versions={n: importlib.metadata.version(n) for n in ['weasyprint', 'cffi', 'pydyf', 'fonttools']},
        python=sys.version, conversion_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        gc_threshold=gc.get_threshold(), gc_policy=settings['gc_policy'])
    step = WeasyPrintStep(SimpleNamespace(template_dir=Path('/sources')), {})
    for iteration, name in enumerate(settings['sequence'], 1):
        content = (Path('/sources')/name).read_bytes()
        emit('render-start', iteration=iteration, source=name, source_sha256=hashlib.sha256(content).hexdigest())
        started = time.monotonic()
        result = step.execute_follow(DocumentFile(FileFormats.HTML, content), {})
        data = result.content
        emit('render-complete', iteration=iteration, source=name, seconds=round(time.monotonic()-started, 3),
            bytes=len(data), pdf_sha256=hashlib.sha256(data).hexdigest(), rss_max_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        if iteration == 1 or iteration == len(settings['sequence']):
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
