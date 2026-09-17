"""Archive read-only Word import observations without altering native acceptance."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
from artifact_utils import sha

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('chinese', 'english', 'engines', 'readme', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    args = p.parse_args()
    assert not args.output.exists()
    baseline = ROOT / 'reviews/2026-09-17-storage-context-pagination/after'
    reports = {}
    for language in ('chinese', 'english'):
        folder = getattr(args, language)
        report = json.loads((folder / 'report.json').read_text())
        assert report['completed'] and report['source_unchanged'] and report['diagnostic_not_native']
        assert not report['release_acceptance'] and report['all_memory_exports_same_normalized_text']
        assert report['source_sha256'] == sha(baseline / 'native' / ('metadata-partial-' + language + '.docx'))
        assert report['script_sha256'] == sha(ROOT / 'scripts/diagnose_word_import_layout.py')
        assert len(report['rows']) == 11
        for row in report['rows']:
            assert sha(folder / (row['mode'] + '.pdf')) == row['pdf_sha256']
            if 'saved_docx_sha256' in row:
                assert sha(folder / (row['mode'] + '-saved.docx')) == row['saved_docx_sha256']
        reports[language] = report
    engine = json.loads((args.engines / 'report.json').read_text())
    assert engine['completed'] and engine['native_inputs_unchanged'] and len(engine['rows']) == 20
    assert engine['script_sha256'] == sha(ROOT / 'scripts/compare_word_preview_engines.py')
    assert not engine['release_acceptance']
    for name, digest in engine['helpers_sha256'].items(): assert sha(ROOT / 'scripts' / name) == digest
    for row in engine['rows']:
        stem = row['case'] + '-' + row['language']
        assert sha(baseline / 'native' / (stem + '.docx')) == row['native_docx_sha256']
        assert sha(baseline / 'word-preview' / (stem + '.pdf')) == row['before']['pdf_sha256']
        assert sha(args.engines / (stem + '.pdf')) == row['after']['pdf_sha256']
        assert row['body_paragraphs_retained'] > 0
    acceptance = json.loads((baseline / 'storage-context-report.json').read_text())
    assert not acceptance['pagination_checks_passed'] and not acceptance['release_acceptance']
    assert sha(baseline / 'storage-context-report.json') == engine['native_report_sha256']
    def copy(source, relative):
        target = args.output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    for language in ('chinese', 'english'):
        for file in sorted(getattr(args, language).iterdir()): copy(file, 'memory-and-reopen/' + language + '/' + file.name)
    for file in sorted(args.engines.iterdir()): copy(file, 'engine-comparison/' + file.name)
    for name in ('diagnose_word_import_layout.py', 'compare_word_preview_engines.py', 'collect_word_import_review.py'):
        copy(ROOT / 'scripts' / name, 'reproduce/' + name)
    copy(args.readme, 'README.md')
    visuals = [
        ('native-chinese', baseline / 'word-preview/metadata-partial-chinese.pdf', [3, 4]),
        ('memory-chinese', args.chinese / 'same-policy.pdf', [3, 4]),
        ('reopened-chinese', args.chinese / 'same-policy-reopened.pdf', [3, 4]),
        ('engine26-chinese', args.engines / 'metadata-partial-chinese.pdf', [2, 3, 4]),
        ('native-english', baseline / 'word-preview/metadata-partial-english.pdf', [3]),
        ('engine26-english', args.engines / 'metadata-partial-english.pdf', [3]),
    ]
    (args.output / 'visual').mkdir()
    for name, pdf, pages in visuals:
        for page in pages:
            subprocess.run(['pdftoppm', '-f', str(page), '-l', str(page), '-r', '95', '-singlefile',
                            '-png', str(pdf), str(args.output / 'visual' / f'{name}-page{page}')],
                           check=True, capture_output=True)
    hashes = {str(file.relative_to(args.output)): sha(file) for file in sorted(args.output.rglob('*')) if file.is_file()}
    (args.output / 'checksums.json').write_text(json.dumps(hashes, indent=2) + '\n')
    print(json.dumps(dict(archived=str(args.output), files=len(hashes), release_acceptance=False)))


if __name__ == '__main__': main()
