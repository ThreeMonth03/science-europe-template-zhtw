"""Archive a verified diagnostic excerpt; never turn its success into release acceptance."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
from diagnose_word_import_layout import sha

ROOT = Path(__file__).resolve().parents[1]


def collect(source, readme, output):
    if output.exists():
        raise FileExistsError(output)
    report = json.loads((source / 'report.json').read_text())
    assert report['completed'] and report['diagnostic_not_native'] and not report['release_acceptance']
    assert report['script_sha256'] == sha(ROOT / 'scripts/reduce_word_layout_case.py')
    assert report['helper_sha256'] == sha(ROOT / 'scripts/diagnose_word_import_layout.py')
    assert [row['language'] for row in report['rows']] == ['chinese', 'english']
    baseline = ROOT / 'reviews/2026-09-17-storage-context-pagination/after'
    for row in report['rows']:
        language = row['language']
        assert row['source_unchanged'] and row['kept_paragraph_table_xml_unchanged']
        assert row['reproduces_native_q5_pagination'] and row['pre_q5_line_geometry_unchanged']
        assert sha(baseline / 'native' / f'metadata-partial-{language}.docx') == row['source_sha256']
        assert sha(baseline / 'word-preview' / f'metadata-partial-{language}.pdf') == row['before']['pdf_sha256']
        assert sha(source / f'reduced-{language}.docx') == row['docx_sha256']
        assert sha(source / f'reduced-{language}.pdf') == row['after']['pdf_sha256']
    def copy(file, relative):
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file, target)
    copy(readme, 'README.md')
    copy(source / 'report.json', 'reduced/report.json')
    for language in ('chinese', 'english'):
        for suffix in ('docx', 'pdf'):
            name = f'reduced-{language}.{suffix}'
            copy(source / name, 'reduced/' + name)
    for name in ('reduce_word_layout_case.py', 'diagnose_word_import_layout.py', 'collect_word_reduction_review.py'):
        copy(ROOT / 'scripts' / name, 'reproduce/' + name)
    (output / 'visual').mkdir()
    for language, pages in [('chinese', [3, 4]), ('english', [3])]:
        for page in pages:
            subprocess.run(['pdftoppm', '-f', str(page), '-l', str(page), '-r', '95', '-singlefile', '-png',
                            str(source / f'reduced-{language}.pdf'), str(output / 'visual' / f'{language}-page{page}')],
                           check=True, capture_output=True)
    hashes = {str(file.relative_to(output)): sha(file) for file in sorted(output.rglob('*')) if file.is_file()}
    (output / 'checksums.json').write_text(json.dumps(hashes, indent=2) + '\n')
    print(json.dumps(dict(archived=str(output), files=len(hashes), release_acceptance=False)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'readme', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    collect(args.source, args.readme, args.output)
