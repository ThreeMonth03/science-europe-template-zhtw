"""Read-only A/B probe using the installed worker parser; never patch the worker."""

import argparse
import json
import subprocess
from pathlib import Path

PROBE = r'''
import hashlib, inspect, json
import markdown
from dsw.document_worker.model.utils import DSWMarkdownExt, render_markdown
cases = {
    'pipe_table': '| Record | Retention |\n|---|---|\n| Processing log | 10 years |',
    'list': 'Training:\n- Metadata checks\n- Version control',
    'hard_break': 'First line\\\nSecond line',
}
results = {}
for name, value in cases.items():
    current = str(render_markdown(value))
    with_tables = markdown.markdown(text=value, extensions=[DSWMarkdownExt(), 'tables'])
    results[name] = {'current': current, 'with_tables': with_tables,
                     'unchanged': current == with_tables}
print(json.dumps({'markdown_version': markdown.__version__,
    'worker_parser_sha256': hashlib.sha256(inspect.getsource(render_markdown).encode()).hexdigest(),
    'results': results}))
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    container = 'science-europe-pilot-docworker-1'
    report = json.loads(subprocess.check_output(['docker', 'exec', '-i', container, 'python', '-'], input=PROBE, text=True))
    report['image_id'] = subprocess.check_output(['docker', 'inspect', '--format', '{{.Image}}', container], text=True).strip()
    report['worker_modified'] = False
    report['end_to_end_acceptance'] = False
    report['limits'] = ['Parser-only comparison, not a deployed change', 'PDF/DOCX and supported rich-text input contract still need end-to-end tests']
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    assert '<table>' not in report['results']['pipe_table']['current']
    assert '<table>' in report['results']['pipe_table']['with_tables']
    assert report['results']['list']['unchanged'] and report['results']['hard_break']['unchanged']
    print(json.dumps({'output': str(args.output), 'parser_comparison_passed': True, 'worker_modified': False}))


if __name__ == '__main__':
    main()
