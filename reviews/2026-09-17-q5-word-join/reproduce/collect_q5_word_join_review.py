"""Archive exact native 0.3.35 outputs, linking the immutable 0.3.34 baseline."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
from bs4 import BeautifulSoup
from artifact_utils import sha
from check_storage_context_outputs import CASES
from collect_storage_context_review import verify_previews

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('build', 'prior', 'candidate', 'rebuild', 'english', 'readme', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args(); assert not a.output.exists()
    report = json.loads((a.build / 'q5-word-join-report.json').read_text())
    assert report['selected_checks_passed'] and not report['release_acceptance'] and len(report['rows']) == 20
    assert {(r['case'], r['language']) for r in report['rows']} == {(c, l) for c in CASES for l in ('english', 'chinese')}
    assert sha(ROOT / 'scripts/check_q5_word_join_outputs.py') == report['checker_sha256']
    assert sha(a.english / 'scripts/q5_word_join_contract.py') == report['word_contract_sha256']
    renders = json.loads((a.build / 'missing-info-render-report.json').read_text())
    assert renders['all_renders_succeeded'] and len(renders['renders']) == 60 and all(r['rendered'] for r in renders['renders'])
    verify_previews(a.build, [c + '-' + l for c in CASES for l in ('english', 'chinese')])
    pixels = json.loads((a.build / 'q5-word-join-pixels.json').read_text())
    assert pixels['passed'] and pixels['native_report_sha256'] == sha(a.build / 'q5-word-join-report.json')
    cleanup = json.loads((a.build / 'owned-test-template-cleanup.json').read_text())
    assert len(cleanup['deleted']) == 2 and cleanup['project_references'] == cleanup['document_references'] == 0
    for backup in cleanup['backups'].values(): assert sha(Path(backup['path'])) == backup['sha256']
    lifecycle = json.loads((a.build / 'worker-lifecycle.json').read_text())
    assert lifecycle['same_worker_before_and_after'] and lifecycle['before'] == lifecycle['after']
    assert json.loads((a.build / 'runtime-restoration.json').read_text())['restored_stock_and_stopped']
    for name, digest in report['package_sha256'].items():
        assert sha(a.build / name) == sha(a.candidate / name) == sha(a.rebuild / name) == digest
    def copy(source, relative):
        target = a.output / relative; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    for row in report['rows']:
        assert row['passed'] and not row['errors'] and not row['reading_issues']
        for key, root in [('before_sha256', a.prior), ('after_sha256', a.build)]:
            for name, digest in row[key].items(): assert sha(root / name) == digest
        stem = row['case'] + '-' + row['language']
        for fmt in ('html', 'pdf', 'docx'):
            source = a.build / 'renders' / (stem + '.' + fmt)
            copy(source.with_suffix('.' + fmt + '.fixture.json'), 'native/' + stem + '.' + fmt + '.fixture.json')
            if fmt != 'html': copy(source, 'native/' + source.name)
            else:
                soup = BeautifulSoup(source.read_text(), 'html.parser')
                target = a.output / 'question-content' / source.name; target.parent.mkdir(exist_ok=True, parents=True)
                target.write_text('<!-- Native HTML SHA256: ' + sha(source) + ' -->\n' + str(soup.select_one('#dmp-content')) + '\n')
        copy(a.build / 'word-preview' / (stem + '.pdf'), 'word-preview/' + stem + '.pdf')
    for name in ('manifest.json', 'q5-word-join-report.json', 'q5-word-join-pixels.json', 'missing-info-render-report.json',
                 'worker-start.json', 'worker-lifecycle.json', 'runtime-restoration.json', 'owned-test-template-cleanup.json'):
        copy(a.build / name, name)
    for source in a.build.glob('word-preview-*.json'): copy(source, source.name)
    for name in ('storage-context-scope.json', 'q5-word-join-engine-en.json', 'q5-word-join-engine-zh.json'):
        assert json.loads((a.candidate / name).read_text())['passed']
        copy(a.candidate / name, 'probes/' + name)
    for label, root in [('candidate', a.candidate), ('rebuild', a.rebuild)]: copy(root / 'manifest.json', label + '-manifest.json')
    for folder in ('en', 'translated'): copy(a.candidate / folder / 'src/word/pilot.lua', 'source/' + folder + '/pilot.lua')
    for name in ('q5_word_join_contract.py', 'probe_q5_word_join.py'): copy(a.english / 'scripts' / name, 'reproduce/' + name)
    for name in ('check_q5_word_join_outputs.py', 'check_q5_word_join_pixels.py', 'collect_q5_word_join_review.py', 'probe_storage_context_scope.py'):
        copy(ROOT / 'scripts' / name, 'reproduce/' + name)
    copy(ROOT / 'pipeline.yml', 'reproduce/pipeline.yml'); copy(a.readme, 'README.md')
    (a.output / 'visual').mkdir()
    visuals = [('before-chinese', a.prior / 'word-preview/metadata-partial-chinese.pdf', [3, 4]),
               ('after-chinese', a.build / 'word-preview/metadata-partial-chinese.pdf', [3, 4]),
               ('before-english', a.prior / 'word-preview/metadata-partial-english.pdf', [3]),
               ('after-english', a.build / 'word-preview/metadata-partial-english.pdf', [3]),
               ('negative-chinese', a.build / 'word-preview/negative-chinese.pdf', [2, 3]),
               ('negative-english', a.build / 'word-preview/negative-english.pdf', [2, 3])]
    for name, pdf, pages in visuals:
        for page in pages:
            subprocess.run(['pdftoppm', '-f', str(page), '-l', str(page), '-r', '95', '-singlefile', '-png',
                            str(pdf), str(a.output / 'visual' / (name + '-page' + str(page)))], check=True, capture_output=True)
    hashes = {str(f.relative_to(a.output)): sha(f) for f in sorted(a.output.rglob('*')) if f.is_file()}
    (a.output / 'checksums.json').write_text(json.dumps(hashes, indent=2) + '\n')
    print(json.dumps(dict(archived=str(a.output), files=len(hashes), native_outputs=60, word_previews=20, release_acceptance=False)))


if __name__ == '__main__': main()
