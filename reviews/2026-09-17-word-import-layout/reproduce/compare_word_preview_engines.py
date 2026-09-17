"""Compare archived native DOCX previews with an isolated, pinned local engine.

This is an observational upgrade experiment, not a passing release check. No
images are pulled, no network is enabled, and native inputs are mounted read-only.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
from bs4 import BeautifulSoup
from docx import Document
from artifact_utils import sha
from collect_storage_context_review import verify_previews
from diagnose_word_import_layout import q5_labels, snapshot
from check_word_short_budget_outputs import verify_preview_paragraphs


def image_id(value):
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', value):
        raise ValueError('Use an immutable, already installed image ID, not a tag')
    actual = subprocess.check_output(['docker', 'image', 'inspect', value, '--format', '{{.Id}}'], text=True).strip()
    if actual != value: raise ValueError('Image identity mismatch')
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--image', required=True)
    args = parser.parse_args()
    engine = image_id(args.image)
    build = args.build.resolve(); output = args.output.resolve()
    acceptance = json.loads((build / 'storage-context-report.json').read_text())
    names = [row['case'] + '-' + row['language'] for row in acceptance['rows']]
    if len(names) != 20 or len(set(names)) != 20: raise ValueError('Require the complete 20-case baseline')
    verify_previews(build, names)
    hashes = {name: sha(build / 'renders' / (name + '.docx')) for name in names}
    packages = {name: sha(build / name) for name in ('english.zip', 'chinese.zip')}
    if packages != acceptance['package_sha256']: raise ValueError('Native report/package mismatch')
    output.mkdir(parents=True, exist_ok=False)
    report = dict(diagnostic_not_native=True, release_acceptance=False, completed=False,
                  image=engine, script_sha256=sha(Path(__file__)),
                  helpers_sha256={name: sha(Path(__file__).with_name(name)) for name in
                                  ('diagnose_word_import_layout.py', 'check_word_short_budget_outputs.py', 'collect_storage_context_review.py')},
                  native_package_sha256=packages, native_report_sha256=sha(build / 'storage-context-report.json'), rows=[],
                  font_mounts=['/usr/share/fonts', '/etc/fonts'],
                  font_tree_sha256={str(p.relative_to('/usr/share/fonts')): sha(p)
                                    for p in sorted(Path('/usr/share/fonts').rglob('*')) if p.is_file()},
                  font_config_sha256={str(p.relative_to('/etc/fonts')): sha(p)
                                      for p in sorted(Path('/etc/fonts').rglob('*')) if p.is_file()},
                  limits=['Same host font/config files, but different engine and system libraries',
                          'Not Microsoft Word; Q5 co-location alone is not upgrade acceptance',
                          'Full-text comparison ignores whitespace and verified page footers only'])
    command = ['docker', 'run', '--rm', '--pull=never', '--network', 'none', '--read-only',
               '--cap-drop=ALL', '--security-opt=no-new-privileges', '--tmpfs', '/tmp:rw,mode=1777',
               '--user', f'{os.getuid()}:{os.getgid()}',
               '--mount', f'type=bind,src={build / "renders"},dst=/input,readonly',
               '--mount', f'type=bind,src={output},dst=/output',
               '--mount', 'type=bind,src=/usr/share/fonts,dst=/usr/share/fonts,readonly',
               '--mount', 'type=bind,src=/etc/fonts,dst=/etc/fonts,readonly',
               '--entrypoint', 'libreoffice', engine]
    try:
        report['engine_version'] = subprocess.check_output(command + ['--version'], text=True, timeout=30).strip()
        result = subprocess.run(command + ['-env:UserInstallation=file:///tmp/se-layout-profile', '--headless',
                                '--norestore', '--convert-to', 'pdf', '--outdir', '/output'] +
                                ['/input/' + name + '.docx' for name in names],
                                capture_output=True, text=True, check=True, timeout=300)
        report['conversion_stdout'] = result.stdout; report['conversion_stderr'] = result.stderr
        for native, name in zip(acceptance['rows'], names):
            source = build / 'renders' / (name + '.docx'); pdf = output / (name + '.pdf')
            baseline = build / 'word-preview' / (name + '.pdf')
            labels = q5_labels(source) if 'q5_locations' in native else []
            before, after = snapshot(baseline, labels), snapshot(pdf, labels)
            if not labels:
                for side in (before, after): side['q5_together'] = None
            row = dict(case=native['case'], language=native['language'], native_docx_sha256=hashes[name],
                       before=before, after=after, page_delta=after['pages'] - before['pages'],
                       unchanged_normalized_text=before['full_text_without_whitespace_and_verified_footers_sha256'] == after['full_text_without_whitespace_and_verified_footers_sha256'])
            soup = BeautifulSoup(source.with_suffix('.html').read_text(), 'html.parser')
            try:
                row['body_paragraphs_retained'] = verify_preview_paragraphs(Document(source), pdf, soup)
            except AssertionError as error:
                row['paragraph_retention_failure'] = str(error)
            report['rows'].append(row)
            print(json.dumps({k: row[k] for k in ('case', 'language', 'page_delta', 'unchanged_normalized_text')}), flush=True)
        report['completed'] = True
    except Exception as error:
        report['error'] = str(error)
        raise
    finally:
        report['native_inputs_unchanged'] = all(sha(build / 'renders' / (name + '.docx')) == value for name, value in hashes.items())
        (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        if not report['native_inputs_unchanged']: raise RuntimeError('Native DOCX changed')


if __name__ == '__main__': main()
