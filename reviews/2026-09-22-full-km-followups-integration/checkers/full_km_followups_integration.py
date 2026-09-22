"""Validate actual 0.3.46 packages, then offer exact historical regression views.

The projection is test-only: it is never published or used as current output.
All new source, translations, assets, UUIDs and conversion steps are checked first.
"""
import argparse
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

from artifact_utils import sha
from check_budget_grouping_integration import asset_uuid

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads((ROOT / 'docs/full-km-followups-prepared-delta.json').read_text())
ADDED = {'src/full-km-followups.j2', 'src/project-file-naming.html.j2',
         'src/reference-publication-plan.html.j2', 'src/reference-maintenance-plan.html.j2'}


@lru_cache(maxsize=2)
def receipt(prototype):
    key = 'prototype' if prototype else 'baseline'
    root = ROOT / CONTRACT[key + '_archive']
    assert sha(root / 'checksums.json') == CONTRACT[key + '_seal_sha256']
    inventory = json.loads((root / 'checksums.json').read_text())
    for name, digest in inventory.items(): assert sha(root / name) == digest, name
    return root


def baseline_package(language):
    return json.loads((receipt(False) / 'native' / (language + '.json')).read_text())


def prototype_package(language):
    record = CONTRACT['languages'][language]
    path = ROOT / record['prototype_fixture']
    assert sha(path) == record['prototype_fixture_sha256']
    manifest = json.loads((receipt(True) / 'build/manifest.json').read_text())
    assert record['prototype_zip_sha256'] == manifest['sha256'][language + '.zip']
    return json.loads(path.read_text())


def sources(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in (root / 'src').rglob('*') if p.is_file()}


def project_sources(current, language):
    expected = CONTRACT['languages'][language]
    hashes = lambda values: {n: hashlib.sha256(v).hexdigest() for n, v in values.items()}
    assert hashes(current) == expected['after'], 'Unreviewed 0.3.46 prepared source or asset'
    assert set(expected['after']) - set(expected['before']) == ADDED == set(expected['added'])
    assert not set(expected['before']) - set(expected['after'])
    assert expected['changed'] == sorted(n for n in expected['before'] if expected['before'][n] != expected['after'][n])
    previous = {n: v for n, v in current.items() if n not in ADDED}
    for file in baseline_package(language)['files']: previous[file['fileName']] = file['content'].encode()
    assert hashes(previous) == expected['before'], 'Projection must restore every 0.3.45 byte'
    return previous


def integrated_package(language, timestamp):
    """Exact prototype content, with the existing production identity and canonical IDs."""
    result = prototype_package(language); previous = baseline_package(language)
    for key in ['name', 'templateId']: result[key] = previous[key]
    result['version'] = '0.3.46'; result['id'] = previous['id'].removesuffix('0.3.45') + '0.3.46'
    result['createdAt'] = result['updatedAt'] = timestamp
    for kind in ['files', 'assets']:
        for item in result[kind]: item['uuid'] = asset_uuid(result['id'], kind, item['fileName'])
    return result


def project_package(candidate, language, timestamp):
    assert candidate == integrated_package(language, timestamp), 'Unreviewed content, identity, assets or conversion steps'
    return baseline_package(language)


def check_package(path, prepared, language, timestamp):
    current = sources(prepared); project_sources(current, language)
    members = CONTRACT['languages'][language]['asset_sha256']
    with zipfile.ZipFile(path) as package:
        assert len(package.namelist()) == len(members) + 1
        assert set(package.namelist()) == set(members) | {'template/template.json'}
        for name, digest in members.items():
            assert hashlib.sha256(package.read(name)).hexdigest() == digest
            assert package.read(name) == current[name.removeprefix('template/assets/')]
        candidate = json.loads(package.read('template/template.json'))
    project_package(candidate, language, timestamp)
    for file in candidate['files']: assert file['content'].encode() == current[file['fileName']]
    return dict(package_sha256=sha(path), prototype_content_and_assets_identical=True,
                deterministic_identity_verified=True, prepared_source_verified=True)


def historical_build(build, destination):
    """Validate both actual packages before writing old ZIPs for the old byte oracle."""
    manifest = json.loads((build / 'manifest.json').read_text())
    assert manifest['source']['version'] == manifest['translation']['version'] == '0.3.46'
    destination.mkdir(parents=True, exist_ok=False)
    for language, folder in [('english', 'en'), ('chinese', 'translated')]:
        path = build / (language + '.zip')
        assert sha(path) == manifest['sha256'][path.name]
        check_package(path, build / folder, language, manifest['package_timestamp'])
        with zipfile.ZipFile(path) as current, zipfile.ZipFile(destination / path.name, 'x') as previous:
            for name in current.namelist():
                value = (json.dumps(baseline_package(language), ensure_ascii=False).encode()
                         if name == 'template/template.json' else current.read(name))
                previous.writestr(name, value)
    return destination


def check(build, english, preview=False):
    from build import package_timestamp
    from probe_pdf_budget_translation import pair
    from probe_personal_data_translation import verify_submission_translation_chain
    sys.path[:0] = [str(english / 'scripts'), str(english / 'experiments/full-km-followups')]
    from full_km_followups_contract import project_source
    from followup_probe import check as branches
    project_source()
    manifest = json.loads((build / 'manifest.json').read_text())
    assert manifest['status'] == ('preview' if preview else 'candidate')
    assert manifest['source']['version'] == manifest['translation']['version'] == '0.3.46'
    if not preview:
        assert all(not state['dirty'] for state in manifest['checkouts'].values())
        head = subprocess.check_output(['git', '-C', str(english), 'rev-parse', 'HEAD'], text=True).strip()
        assert manifest['source']['commit'] == manifest['checkouts']['english']['commit'] == head
    files = list((ROOT / 'translation/tree').rglob('translation.md'))
    _, chain = verify_submission_translation_chain([pair(p.read_text()) for p in files])
    assert manifest['translation_units'] == len(files) == 773 and not manifest['untranslated_units']
    assert manifest['translation_tree_sha256'] == {str(p.relative_to(ROOT / 'translation')): sha(p) for p in files}
    assert manifest['package_timestamp'] == package_timestamp(english)
    packages = {}; checks = {}
    for language, folder in [('english', 'en'), ('chinese', 'translated')]:
        path = build / (language + '.zip'); assert sha(path) == manifest['sha256'][path.name]
        packages[language] = check_package(path, build / folder, language, manifest['package_timestamp'])
        actual = sources(build / folder)
        checks[language] = len(branches(english, actual)); assert checks[language] == 240
    return dict(passed=True, preview=preview, source_integrated=True, release_acceptance=False,
        native_integrated_render_checked=False, global_switch_complete=False,
        translation_delta=chain['full_km_followups'], packages=packages, branch_checks=checks)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', type=Path, required=True); p.add_argument('--english', type=Path, required=True)
    p.add_argument('--preview', action='store_true')
    args = p.parse_args(); result = check(args.build.resolve(), args.english.resolve(), args.preview)
    with (args.build / 'full-km-followups-integration.json').open('x') as stream:
        stream.write(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False))
