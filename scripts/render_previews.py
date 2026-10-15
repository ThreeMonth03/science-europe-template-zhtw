"""Render local native receipts for human review, never release acceptance."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def contained(root, name):
    path = root / name
    if Path(name).is_absolute() or path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Native output must be a relative file inside its receipt directory')
    if not path.is_file():
        raise ValueError('Native output is missing')
    return path


def run(command, log, env=None):
    with log.open('xb') as stream:
        subprocess.run(list(map(str, command)), stdout=stream, stderr=subprocess.STDOUT,
                       env=env, check=True, timeout=180)


def render(args):
    native = args.native.resolve()
    receipt_path = native / 'receipt.json'
    receipt_sha = sha(receipt_path)
    receipt = json.loads(receipt_path.read_text())
    if (receipt.get('kind') != 'local-native-preview' or receipt.get('render_passed') is not True
            or receipt.get('accepted') is not False or not receipt.get('outputs')):
        raise ValueError('A successful local-native-preview receipt is required, not an acceptance report')
    inputs = [(row, contained(native, row['path'])) for row in receipt['outputs']]
    if len({path.resolve() for _, path in inputs}) != len(inputs):
        raise ValueError('Duplicate native output')
    for row, path in inputs:
        if row['kind'] not in ('PDF', 'Word') or sha(path) != row['sha256']:
            raise ValueError('Native kind or hash differs from receipt')
    args.output.mkdir(parents=True, mode=0o700)  # Never reuse a failed/earlier preview.
    report = {'schema_version': 1, 'kind': 'local-render-preview', 'render_passed': False,
              'accepted': False, 'visual_review_complete': False, 'microsoft_word_tested': False,
              'native_receipt_sha256': receipt_sha, 'outputs': []}
    try:
        env = dict(os.environ, PATH=str(args.pdftoppm.parent) + os.pathsep + os.environ.get('PATH', ''))
        for number, (row, source) in enumerate(inputs, 1):
            folder = args.output / f'{number:03d}'
            folder.mkdir()
            preview_pdf = source
            if row['kind'] == 'Word':
                if args.docx_renderer:
                    # Select the caller's binary without modifying the external
                    # canonical renderer or silently falling back to desktop LO.
                    code = ('import importlib.util,sys; '
                        f's=importlib.util.spec_from_file_location("renderer", {str(args.docx_renderer)!r}); '
                        'm=importlib.util.module_from_spec(s); s.loader.exec_module(m); '
                        f'm._resolve_soffice=lambda: {str(args.soffice)!r}; '
                        f'sys.argv=[{str(args.docx_renderer)!r}, {str(source)!r}, "--output_dir", '
                        f'{str(folder)!r}, "--emit_pdf"]; m.main()')
                    run([args.renderer_python, '-c', code], folder / 'render.log', env)
                else:
                    with tempfile.TemporaryDirectory(prefix='dsw-lo-') as profile:
                        run([args.soffice, '--headless', '-env:UserInstallation=' + Path(profile).as_uri(),
                             '--convert-to', 'pdf', '--outdir', folder.resolve(), source], folder / 'render.log', env)
                preview_pdf = folder / (source.stem + '.pdf')
            if not preview_pdf.is_file() or not preview_pdf.stat().st_size:
                raise ValueError('Preview PDF is missing')
            images = list(folder.glob('page-*.png'))
            if not images:
                run([args.pdftoppm, '-r', '150', '-png', preview_pdf, folder / 'page'], folder / 'pages.log', env)
                images = list(folder.glob('page-*.png'))
            info = subprocess.check_output([str(args.pdfinfo), str(preview_pdf)], text=True, env=env, timeout=30)
            pages = next(int(line.split(':', 1)[1]) for line in info.splitlines() if line.startswith('Pages:'))
            images.sort(key=lambda path: int(path.stem.rsplit('-', 1)[1]))
            if pages != len(images) or not all(path.stat().st_size for path in images):
                raise ValueError('Preview page inventory is incomplete')
            if sha(source) != row['sha256']:
                raise ValueError('Renderer changed a native document')
            report['outputs'].append({**row, 'pages': pages,
                'preview_route': 'native-pdf' if row['kind'] == 'PDF' else 'libreoffice-docx-preview',
                'preview_pdf_sha256': sha(preview_pdf),
                'page_sha256': {path.relative_to(args.output).as_posix(): sha(path) for path in images}})
        if sha(receipt_path) != receipt_sha or any(sha(path) != row['sha256'] for row, path in inputs):
            raise ValueError('Native evidence changed during preview')
        report['render_passed'] = True
    except Exception as exc:
        report['error_type'] = type(exc).__name__
        raise
    finally:
        with (args.output / 'preview-receipt.json').open('x') as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pdftoppm', type=Path, required=True)
    parser.add_argument('--pdfinfo', type=Path, help='Defaults to pdfinfo beside the selected pdftoppm')
    parser.add_argument('--soffice', type=Path, required=True, help='Explicit LibreOffice executable; no PATH fallback')
    parser.add_argument('--docx-renderer', type=Path, help='Optional canonical render_docx.py with --output_dir/--emit_pdf')
    parser.add_argument('--renderer-python', type=Path, help='Python for --docx-renderer')
    args = parser.parse_args()
    if not args.pdfinfo:
        args.pdfinfo = args.pdftoppm.absolute().with_name('pdfinfo')
    if bool(args.docx_renderer) != bool(args.renderer_python):
        parser.error('--docx-renderer and --renderer-python must be used together')
    for path in (args.pdftoppm, args.pdfinfo, args.soffice, args.docx_renderer, args.renderer_python):
        if path is not None and (not path.is_absolute() or not path.is_file()):
            parser.error('Renderer paths must be absolute existing files')
    report = render(args)
    print(json.dumps({'render_passed': True, 'accepted': False, 'documents': len(report['outputs']),
                      'pages': sum(row['pages'] for row in report['outputs'])}))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'Preview failed ({type(exc).__name__}); inspect the private output directory.', file=sys.stderr)
        sys.exit(1)
