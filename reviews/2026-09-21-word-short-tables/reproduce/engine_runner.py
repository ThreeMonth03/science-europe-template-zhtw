"""Isolated pinned-engine harness, not an API/native-output replacement."""
import base64
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import zipfile
import jinja2
from dsw.document_worker.documents import DocumentFile, FileFormats
from dsw.document_worker.templates.steps.word import EnrichDocxStep
from dsw.document_worker.utils import JinjaEnvironment


def main():
    payload = json.load(sys.stdin); out = Path('/out')
    with tempfile.TemporaryDirectory() as folder:
        folder = Path(folder)
        for name, raw in payload['assets'].items(): (folder / name).write_bytes(base64.b64decode(raw))
        (folder / 'short-tables.xml.j2').write_text(payload['xml'])
        html = payload['html'].encode()
        common = ['pandoc', '--from=html', '--filter=pandoc-docx-pagebreakpy',
                  '--lua-filter=' + str(folder / 'pilot.lua'), '--lua-filter=' + str(folder / 'preservation-reading.lua')]
        for phase in ['before', 'marked']:
            command = common + (['--lua-filter=' + str(folder / 'short-tables.lua')] if phase == 'marked' else [])
            subprocess.run(command + ['--to=docx', '--reference-doc=' + str(folder / 'reference.docx'),
                                     '-o', str(out / (phase + '.docx'))], input=html, check=True)
            ast = subprocess.check_output(command + ['--to=json'], input=html)
            (out / (phase + '.ast.json')).write_bytes(ast)
        # Exercise the actual class's rewrite + repack implementation. Its app
        # configuration constructor is replaced only in this offline harness;
        # native local-DSW controls separately verify the complete pipeline.
        step = EnrichDocxStep.__new__(EnrichDocxStep)
        step.template = SimpleNamespace(template_dir=folder)
        step.rewrites = {'word/document.xml': 'render:short-tables.xml.j2'}
        step.j2_env = JinjaEnvironment(loader=jinja2.FileSystemLoader(folder), autoescape=True,
                                     extensions=['jinja2.ext.do', 'jinja2.ext.loopcontrols'])
        for source, target in [('before', 'noop'), ('marked', 'after')]:
            result = step.execute_follow(DocumentFile(FileFormats.DOCX, (out / (source + '.docx')).read_bytes()), {})
            (out / (target + '.docx')).write_bytes(result.content)
        hashes = {name: hashlib.sha256(Path(importlib.util.find_spec(name).origin).read_bytes()).hexdigest()
                  for name in ['dsw.document_worker.templates.steps.word', 'dsw.document_worker.templates.steps.template',
                               'dsw.document_worker.templates.steps.conversion', 'dsw.document_worker.utils']}
        (out / 'runtime.json').write_text(json.dumps(dict(pandoc=subprocess.check_output(['pandoc', '--version'], text=True).splitlines()[0],
                                                       sources=hashes, app_constructor_exercised=False), indent=2) + '\n')


if __name__ == '__main__': main()
