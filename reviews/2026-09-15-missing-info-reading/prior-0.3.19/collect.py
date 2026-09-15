"""Collect this diagnostic report without changing template repositories or releases."""
import json
from pathlib import Path
import shutil
from audit import HERE, ROOT, EN, digest

report = json.loads((HERE / 'missing-info-report.json').read_text())
assert report['checker_sha256'] == digest(HERE / 'check.py')
assert report['fixture_script_sha256'] == digest(HERE / 'audit.py')
assert report['extra_fixture_script_sha256'] == digest(HERE / 'extra_case.py')
assert report['all_renders_succeeded'] and report['native_pdf_count'] == 18
assert not report['all_selected_content_checks_passed'] and not report['all_selected_reading_checks_passed']
for name, value in report['helper_sha256'].items(): assert digest(ROOT / 'scripts' / name) == value
for name, script in [('fixture-validation.json', 'audit.py'), ('extra-fixture-validation.json', 'extra_case.py')]:
    data = json.loads((HERE / name).read_text()); assert data['script_sha256'] == digest(HERE / script)
    assert all(not row['errors'] for row in data['rows'])
build = ROOT / 'outputs/runtime-tables-pgueiskk'
manifest = json.loads((build / 'manifest.json').read_text())
assert manifest['status'] == 'runtime-experiment' and manifest['source']['version'] == '0.3.19'
assert all(not state['dirty'] for state in manifest['checkouts'].values())
assert report['package_sha256'] == manifest['identical_package_sha256']
for name, value in report['package_sha256'].items(): assert digest(build / name) == value
target = HERE / 'native'; assert not target.exists(); target.mkdir()
for row in report['rows']:
    for name, value in row['artifact_sha256'].items(): assert digest(build / name) == value
    filename = row['case'] + '-' + row['language'] + '.pdf'
    for suffix in ['', '.fixture.json']:
        shutil.copy2(build / 'renders' / (filename + suffix), target / (filename + suffix))
shutil.copy2(build / 'manifest.json', HERE / 'runtime-manifest.json')
files = [p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.log' and p.name != 'checksums.json']
checksums = {str(p.relative_to(HERE)): digest(p) for p in sorted(files)}
assert not (HERE / 'checksums.json').exists()
(HERE / 'checksums.json').write_text(json.dumps(checksums, indent=2) + '\n')
print(json.dumps({'hashed_files': len(files), 'pdfs': len(list(target.glob('*.pdf'))), 'bytes': sum(p.stat().st_size for p in files)}))
