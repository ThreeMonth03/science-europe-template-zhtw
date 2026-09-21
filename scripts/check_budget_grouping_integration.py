"""Verify 0.3.43 differs from the frozen native trial only by package identity."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import uuid
import zipfile

from artifact_utils import sha
from build import package_timestamp

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'reviews/2026-09-21-large-resource-groups'
SEAL = 'a4dc74ea334dfe5e4232e994e1c4955918f82284c9745baeaeec425b83b4c569'
TRANSLATION_BASE = '3cfa9ed46ea533332e6ab77017f863e3eb51da78'


def asset_uuid(package_id, kind, name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f'dsw-template/{package_id}/{kind}/{name}'))


def project_metadata(candidate, baseline, timestamp, versions=('0.3.42', '0.3.43')):
    """Do not discard UUIDs/timestamps: validate their exact deterministic values."""
    result = copy.deepcopy(candidate)
    old_version, new_version = versions
    assert baseline['version'] == old_version and candidate['version'] == new_version
    assert baseline['id'].endswith(':' + old_version)
    assert candidate['id'] == baseline['id'][:-len(old_version)] + new_version
    for field in ['createdAt', 'updatedAt']:
        assert candidate[field] == timestamp, field
        result[field] = baseline[field]
    for kind in ['files', 'assets']:
        original = {item['fileName']: item for item in baseline[kind]}
        assert len(original) == len(baseline[kind]) == len(candidate[kind])
        assert {item['fileName'] for item in candidate[kind]} == set(original)
        for item in result[kind]:
            name = item['fileName']
            assert item['uuid'] == asset_uuid(candidate['id'], kind, name), (kind, name)
            assert original[name]['uuid'] == asset_uuid(baseline['id'], kind, name)
            item['uuid'] = original[name]['uuid']
    result['id'], result['version'] = baseline['id'], baseline['version']
    assert result == baseline, 'Template, format, metadata or asset declaration drift'
    return result


def check_package(path, baseline, members, timestamp):
    with zipfile.ZipFile(path) as package:
        assert len(package.namelist()) == len(members) and set(package.namelist()) == set(members)
        for name, digest in members.items():
            if name != 'template/template.json':
                assert hashlib.sha256(package.read(name)).hexdigest() == digest, name
        candidate = json.loads(package.read('template/template.json'))
    project_metadata(candidate, baseline, timestamp)
    return dict(package_sha256=sha(path), files=len(candidate['files']), assets=len(candidate['assets']),
                content_and_asset_bytes_identical=True, deterministic_identity_verified=True)


def check(build, english):
    assert sha(ARCHIVE / 'checksums.json') == SEAL
    for name, digest in json.loads((ARCHIVE / 'checksums.json').read_text()).items():
        assert sha(ARCHIVE / name) == digest, name
    manifest = json.loads((build / 'manifest.json').read_text())
    assert manifest['status'] == 'candidate' and not manifest['untranslated_units']
    assert all(not state['dirty'] for state in manifest['checkouts'].values())
    assert manifest['translation_units'] == 748
    assert manifest['source']['version'] == manifest['translation']['version'] == '0.3.43'
    source_commit = subprocess.check_output(['git', '-C', str(english), 'rev-parse', 'HEAD'], text=True).strip()
    assert manifest['source']['commit'] == source_commit
    tree = lambda rev: subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', rev + ':translation'], text=True).strip()
    assert tree('HEAD') == tree(TRANSLATION_BASE), 'Translations changed during integration'
    assert not subprocess.check_output(['git', '-C', str(ROOT), 'status', '--porcelain', '--', 'translation'], text=True)
    proof = json.loads((ARCHIVE / 'provenance/package-projection.json').read_text())
    timestamp = package_timestamp(english)
    rows = {}
    for language in ['english', 'chinese']:
        path = build / (language + '.zip')
        assert sha(path) == manifest['sha256'][path.name]
        baseline = json.loads((ARCHIVE / f'package/after-{language}.json').read_text())
        rows[language] = check_package(path, baseline, proof[language]['members'][1], timestamp)
    return dict(selected_checks_passed=True, release_acceptance=False, native_integrated_render_checked=False,
                source_commit=source_commit, translation_tree=tree('HEAD'), frozen_seal=SEAL,
                checker_sha256=sha(Path(__file__)), packages=rows)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', type=Path, required=True); p.add_argument('--english', type=Path, required=True)
    a = p.parse_args(); result = check(a.build, a.english)
    target = a.build / 'budget-grouping-integration.json'
    with target.open('x') as stream: stream.write(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__': main()
