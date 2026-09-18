"""Archive bounded bilingual PDF/Word prose improvement and reproducible inputs."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
from bs4 import BeautifulSoup
from artifact_utils import sha
from check_metadata_gap_prose_outputs import CASES
from collect_storage_context_review import verify_previews

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('build', 'prior', 'candidate', 'rebuild', 'english', 'readme', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    proof = json.loads((args.build / 'metadata-gap-prose-report.json').read_text())
    assert proof['selected_checks_passed'] and not proof['release_acceptance']
    expected = {(case, language) for case in CASES for language in ('english', 'chinese')}
    assert {(r['case'], r['language']) for r in proof['rows']} == expected and len(proof['rows']) == 10
    assert sha(ROOT / 'scripts/check_metadata_gap_prose_outputs.py') == proof['checker_sha256']
    assert sha(args.english/'scripts/probe_metadata_gap_prose.py') == proof['word_contract_sha256']
    assert sha(args.english/'scripts/metadata_gap_prose_contract.py') == proof['prose_contract_sha256']
    renders = json.loads((args.build / 'missing-info-render-report.json').read_text())
    assert renders['all_renders_succeeded'] and len(renders['renders']) == 30 and all(r['rendered'] for r in renders['renders'])
    verify_previews(args.build, [case + '-' + language for case, language in expected])
    pixels = json.loads((args.build / 'unchanged-control-pixels.json').read_text())
    assert pixels['passed'] and len(pixels['rows']) == 8
    for row in pixels['rows']:
        for key, root in [('before_pdf_sha256', args.prior), ('after_pdf_sha256', args.build)]:
            assert sha(root / row['format'] / (row['case'] + '-' + row['language'] + '.pdf')) == row[key]
    cleanup = json.loads((args.build / 'owned-test-template-cleanup.json').read_text())
    assert len(cleanup['deleted']) == 2 and cleanup['project_references'] == cleanup['document_references'] == 0
    for backup in cleanup['backups'].values():
        assert sha(Path(backup['path'])) == backup['sha256']
    lifecycle = json.loads((args.build / 'worker-lifecycle.json').read_text())
    assert lifecycle['same_worker_before_and_after'] and lifecycle['before'] == lifecycle['after']
    assert json.loads((args.build / 'runtime-restoration.json').read_text())['restored_stock_and_stopped']
    for name, digest in proof['package_sha256'].items():
        assert sha(args.build / name) == sha(args.candidate / name) == sha(args.rebuild / name) == digest
    def copy(source, relative):
        target = args.output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    for row in proof['rows']:
        assert row['passed'] and row['word_joins'] == int(row['selected']) and not row['errors'] and not row['reading_issues']
        for key, root in [('before_sha256', args.prior), ('after_sha256', args.build)]:
            for name, digest in row[key].items():
                assert sha(root / name) == digest
        stem = row['case'] + '-' + row['language']
        for fmt in ('html', 'pdf', 'docx'):
            source = args.build / 'renders' / (stem + '.' + fmt)
            copy(source.with_suffix('.' + fmt + '.fixture.json'), 'native/' + stem + '.' + fmt + '.fixture.json')
            if fmt != 'html':
                copy(source, 'native/' + source.name)
            else:
                soup = BeautifulSoup(source.read_text(), 'html.parser')
                target = args.output / 'question-content' / source.name
                target.parent.mkdir(exist_ok=True, parents=True)
                target.write_text('<!-- Extracted question content; native full HTML SHA256: ' + sha(source) + ' -->\n' + str(soup.select_one('#dmp-content')) + '\n')
        copy(args.build / 'word-preview' / (stem + '.pdf'), 'word-preview/' + stem + '.pdf')
    for name in ('manifest.json', 'metadata-gap-prose-report.json', 'unchanged-control-pixels.json', 'missing-info-render-report.json',
                 'worker-start.json', 'worker-lifecycle.json', 'runtime-restoration.json', 'owned-test-template-cleanup.json'):
        copy(args.build / name, name)
    for source in args.build.glob('word-preview-*.json'):
        copy(source, source.name)
    for name in ('metadata-gap-prose-scope.json', 'metadata-gap-prose-engine-en.json', 'metadata-gap-prose-engine-zh.json'):
        assert json.loads((args.candidate / name).read_text())['passed']
        copy(args.candidate / name, 'probes/' + name)
    for label, root in [('candidate', args.candidate), ('rebuild', args.rebuild)]:
        copy(root / 'manifest.json', label + '-manifest.json')
    for folder in ('en', 'translated'):
        for name in ('src/layout.css', 'src/questions/03-docs-metadata.html.j2'):
            copy(args.candidate / folder / name, 'source/' + folder + '/' + name)
    trial = ROOT/'outputs/build-ls2zx9fx'
    audit = json.loads((trial/'structure-audit.json').read_text())
    assert any(row['code'] == 'changed-html-structure' for row in audit)
    copy(trial/'structure-audit.json', 'conversion-trial/structure-audit.json')
    for folder in ('expanded', 'translated'):
        copy(trial/folder/'src/questions/03-docs-metadata.html.j2', 'conversion-trial/'+folder+'-q3.html.j2')
    for source in (args.build/'diagnostics').rglob('*') if (args.build/'diagnostics').exists() else []:
        if source.is_file():
            copy(source, 'checker-diagnostics/'+str(source.relative_to(args.build/'diagnostics')))
    for name in ('metadata_gap_prose_contract.py', 'probe_metadata_gap_prose.py'):
        copy(args.english / 'scripts' / name, 'reproduce/' + name)
    for name in ('check_metadata_gap_prose_outputs.py', 'collect_metadata_gap_prose_review.py', 'check_unchanged_control_pixels.py', 'probe_metadata_gap_prose_scope.py', 'render.py', 'run_missing_info.py', 'cleanup_owned_runtime_templates.py'):
        copy(ROOT / 'scripts' / name, 'reproduce/' + name)
    copy(ROOT / 'pipeline.yml', 'reproduce/pipeline.yml')
    copy(ROOT/'docs/metadata-gap-prose-translation-delta.json', 'reproduce/translation-delta.json')
    copy(args.readme, 'README.md')
    for language in ('english', 'chinese'):
        stem = 'metadata-partial-' + language
        copy(args.prior / 'renders' / (stem + '.pdf'), 'before/' + stem + '.pdf')
        row = next(r for r in proof['rows'] if r['case'] == 'metadata-partial' and r['language'] == language)
        for label, root, key in [('before', args.prior, 'before'), ('after', args.build, 'after')]:
            geometry = row['prose_geometry'][key]
            page = geometry[0]['page'] if key == 'before' else geometry['page']
            target = args.output / 'visual' / (label + '-' + language + '-page' + str(page))
            target.parent.mkdir(exist_ok=True)
            subprocess.run(['pdftoppm', '-f', str(page), '-l', str(page), '-r', '105', '-singlefile', '-png',
                str(root / 'renders' / (stem + '.pdf')), str(target)], check=True, capture_output=True)
    hashes = {str(path.relative_to(args.output)): sha(path) for path in sorted(args.output.rglob('*')) if path.is_file()}
    (args.output / 'checksums.json').write_text(json.dumps(hashes, indent=2) + '\n')
    print(json.dumps(dict(archived=str(args.output), files=len(hashes), native_outputs=30, word_previews=10, release_acceptance=False)))


if __name__ == '__main__':
    main()
