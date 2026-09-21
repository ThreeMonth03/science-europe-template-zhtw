"""Exact prepared-source and package proof for the paired 0.3.44 integration."""
import copy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import zipfile
from artifact_utils import sha
from probe_pdf_budget_translation import pair
from probe_personal_data_translation import verify_submission_translation_chain

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads((ROOT / 'docs/submission-preview-prepared-delta.json').read_text())
ARCHIVE = ROOT / CONTRACT['prototype_archive']
TRANSLATION_BASE = '408bbbd1f7d162f6c0c3e31a00456130298618c9'


def frozen_package(language):
    assert sha(ARCHIVE / 'checksums.json') == CONTRACT['prototype_seal_sha256']
    checksums = json.loads((ARCHIVE / 'checksums.json').read_text())
    name = 'package/before-' + language + '.json'
    assert sha(ARCHIVE / name) == checksums[name]
    return json.loads((ARCHIVE / name).read_text())


def verified_sources(root, language):
    current = {str(p.relative_to(root)): p.read_bytes() for p in (root / 'src').rglob('*') if p.is_file()}
    expected = CONTRACT['languages'][language]
    assert {name: hashlib.sha256(value).hexdigest() for name, value in current.items()} == expected['after'], 'Unreviewed prepared source or asset'
    assert expected['before'].keys() == expected['after'].keys()
    assert expected['changed'] == sorted(name for name in expected['before'] if expected['before'][name] != expected['after'][name])
    assert all(name.endswith('.j2') for name in expected['changed']), 'Rendering assets may not change'
    previous = dict(current)
    for file in frozen_package(language)['files']:
        assert file['fileName'] in previous
        previous[file['fileName']] = file['content'].encode()
    assert {name: hashlib.sha256(value).hexdigest() for name, value in previous.items()} == expected['before'], 'Projection did not restore exact 0.3.43 bytes'
    return current, previous


def historical_view(root, language, destination):
    """Verified test-only source view; no rendered text or current source edits."""
    _, previous = verified_sources(root, language)
    destination.mkdir(parents=True, exist_ok=False)
    for name, value in previous.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(value)
    return destination


def historical_translation_documents():
    current = [pair(p.read_text()) for p in (ROOT / 'translation/tree').rglob('translation.md')]
    verify_submission_translation_chain(current)
    raw = subprocess.check_output(['git', '-C', str(ROOT), 'archive', TRANSLATION_BASE, 'translation/tree'])
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        return {f.name: archive.extractfile(f).read() for f in archive if f.isfile()}


def check_package(path, prepared, language, timestamp):
    from check_budget_grouping_integration import project_metadata
    current, _ = verified_sources(prepared, language)
    baseline = frozen_package(language)
    with zipfile.ZipFile(path) as package:
        candidate = json.loads(package.read('template/template.json'))
        members = json.loads((ARCHIVE / 'provenance/package-members.json').read_text())['before'][language]
        assert len(package.namelist()) == len(members) and set(package.namelist()) == set(members)
        for name, digest in members.items():
            if name != 'template/template.json':
                assert hashlib.sha256(package.read(name)).hexdigest() == digest, name
    projected = copy.deepcopy(candidate)
    originals = {f['fileName']: f for f in baseline['files']}
    assert len(candidate['files']) == len(originals) == len({f['fileName'] for f in candidate['files']})
    for file in projected['files']:
        name = file['fileName']
        assert file['content'].encode() == current[name], 'Packaged Jinja differs from verified build source'
        file['content'] = originals[name]['content']
    project_metadata(projected, baseline, timestamp, versions=('0.3.43', '0.3.44'))
    return dict(package_sha256=sha(path), prepared_source_verified=True,
        rendering_assets_unchanged=True, deterministic_identity_verified=True,
        changed_source_files=CONTRACT['languages'][language]['changed'])


def check(build, english, preview=False):
    from build import package_timestamp
    import sys
    sys.path.insert(0, str(english / 'scripts'))
    from submission_preview_contract import project_source
    project_source()
    manifest = json.loads((build / 'manifest.json').read_text())
    assert manifest['status'] == ('preview' if preview else 'candidate')
    assert manifest['source']['version'] == manifest['translation']['version'] == '0.3.44'
    if not preview:
        assert all(not state['dirty'] for state in manifest['checkouts'].values())
        head = subprocess.check_output(['git', '-C', str(english), 'rev-parse', 'HEAD'], text=True).strip()
        assert manifest['source']['commit'] == manifest['checkouts']['english']['commit'] == head
    files = list((ROOT / 'translation/tree').rglob('translation.md'))
    _, chain = verify_submission_translation_chain([pair(p.read_text()) for p in files])
    assert manifest['translation_units'] == len(files) == 762 and not manifest['untranslated_units']
    assert manifest['translation_tree_sha256'] == {str(p.relative_to(ROOT / 'translation')): sha(p) for p in files}
    assert manifest['package_timestamp'] == package_timestamp(english)
    results = {}
    for language, folder in [('english', 'en'), ('chinese', 'translated')]:
        path = build / (language + '.zip')
        assert sha(path) == manifest['sha256'][path.name]
        results[language] = check_package(path, build / folder, language, manifest['package_timestamp'])
    return dict(passed=True, preview=preview, release_acceptance=False,
        native_integrated_render_checked=False, global_switch_complete=False,
        translation_delta=chain['submission_preview'], packages=results)
