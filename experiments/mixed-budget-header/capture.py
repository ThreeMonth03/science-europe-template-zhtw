"""Observe public synthetic PDF conversions without modifying their input/options.

For the isolated pilot only. Not a replacement PDF renderer or production hook.
"""
import hashlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import sys
import threading

EXPECTED = {
    'dsw.document_worker.templates.steps.conversion': '95d11d5d00b837bd734bca5a0aa0eefacc5c671089915d39a2e69a79dc6b08fa',
    'weasyprint.layout.table': '2b214e83d6a2325ff03b7d7fd2443b5ab095787b46258d08afe85db9bdaa4928',
    'dsw.document_worker.model.utils': 'bc8d1d61f42265b8e7219c34f9fd6b4d4b3ad988297018b67545d2a7ba731c19',
    'weasyprint.text.fonts': '3f6662edc1f0a11e1666c39f9b72a2d2543769162ee985b216c2afbddd0312a1',
    'weasyprint.text.ffi': 'd7784b995d7d4624eca4a1e76bf46564c6abe82a53207c0f0cf48657516684d7',
}
OUT = Path('/diagnostics')
LOCK = threading.Lock()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def public_mixed_input(data):
    return (b'class="resource-table pdf-resource-reading"' in data and
            all(data.count(f'MIX-LONG-09-PARA-{i:02d}:'.encode()) == 1 for i in range(1, 61)))


def table_trace(records):
    def trace(frame, event, value):
        if frame.f_code.co_name != 'all_groups_layout':
            return None
        if not frame.f_code.co_filename.endswith('/weasyprint/layout/table.py'):
            return None
        v = frame.f_locals
        table = v.get('table')
        if table is None or 'pdf-resource-reading' not in table.element.get('class', '').split():
            return None
        row = {'event': event, 'line': frame.f_lineno, 'id': table.element.get('data-item-id')}
        for name in ['page_is_empty', 'has_header', 'avoid_breaks', 'position_y', 'header_height', 'bottom_space', 'skip_stack', 'resume_at']:
            if name in v:
                item = v[name]
                row[name] = item if not isinstance(item, float) or abs(item) != float('inf') else str(item)
        row['page'] = getattr(v.get('context'), 'current_page', None)
        for name in ['header', 'footer', 'new_table_children']:
            if name in v:
                row[name + '_present'] = bool(v[name])
        if event == 'return' and isinstance(value, tuple):
            row['returned_header'] = bool(value[0])
            row['returned_body'] = bool(value[1])
            row['returned_resume_at'] = value[4]
        records.append(row)
        return trace
    return trace


def install():
    for name, digest in EXPECTED.items():
        actual = sha(Path(importlib.util.find_spec(name).origin).read_bytes())
        if actual != digest:
            raise RuntimeError('Unreviewed diagnostic runtime: ' + name)
    from dsw.document_worker.templates.steps.conversion import WeasyPrintStep
    original = WeasyPrintStep.execute_follow

    def observed(self, document, context):
        if not public_mixed_input(document.content):
            raise RuntimeError('This diagnostic only accepts the public 60-paragraph mixed fixture')
        with LOCK:
            number = len(list(OUT.glob('*.input.html'))) + 1
            prefix = OUT / f'{number:03d}'
            with prefix.with_suffix('.input.html').open('xb') as target:
                target.write(document.content)
            records = []
            report = {'diagnostic_only': True, 'native_input_captured': True, 'input_modified': False,
                      'options_modified': False, 'layout_engine_modified': False, 'source_sha256': EXPECTED,
                      'observer_sha256': sha(Path(__file__).read_bytes()), 'input_sha256': sha(document.content),
                      'options': self.wp_options, 'zoom': self.wp_zoom, 'trace': records}
            previous = sys.gettrace()
            try:
                if previous is not None:
                    raise RuntimeError('Refusing to replace an existing tracer')
                sys.settrace(table_trace(records))
                result = original(self, document, context)
                with prefix.with_suffix('.output.pdf').open('xb') as target:
                    target.write(result.content)
                report['output_sha256'] = sha(result.content)
                report['completed'] = True
                return result
            finally:
                sys.settrace(previous)
                prefix.with_suffix('.trace.json').write_text(json.dumps(report, indent=2) + '\n')
    WeasyPrintStep.execute_follow = observed


if __name__ == '__main__':
    install()
    sys.argv = ['dsw-document-worker', 'run']
    entry = next(e for e in importlib.metadata.entry_points(group='console_scripts') if e.name == 'dsw-document-worker')
    entry.load()()
