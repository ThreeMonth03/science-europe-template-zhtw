"""Replay captured PDF-entry HTML with the pinned DSW conversion step."""
import argparse
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from capture import EXPECTED, sha, table_trace
import importlib.util


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('name')
    a = p.parse_args()
    assert Path(a.name).name == a.name
    for module, digest in EXPECTED.items():
        assert sha(Path(importlib.util.find_spec(module).origin).read_bytes()) == digest
    from dsw.document_worker.documents import DocumentFile, FileFormats
    from dsw.document_worker.templates.steps.conversion import WeasyPrintStep
    data = (Path('/input') / (a.name + '.html')).read_bytes()
    trace = []
    step = WeasyPrintStep(SimpleNamespace(template_dir=Path('/input')), {})
    try:
        sys.settrace(table_trace(trace))
        result = step.execute_follow(DocumentFile(FileFormats.HTML, data), {})
    finally:
        sys.settrace(None)
    (Path('/out') / (a.name + '.pdf')).write_bytes(result.content)
    report = {'input_sha256': sha(data), 'output_sha256': sha(result.content),
              'source_sha256': EXPECTED, 'runner_sha256': sha(Path(__file__).read_bytes()),
              'options': step.wp_options, 'zoom': step.wp_zoom, 'trace': trace}
    (Path('/out') / (a.name + '.trace.json')).write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
