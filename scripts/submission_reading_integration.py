"""Exact 0.3.45 prepared/package proof and test-only 0.3.44 projection."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

from artifact_utils import sha
from probe_pdf_budget_translation import pair
from probe_personal_data_translation import verify_submission_translation_chain, project_submission_reading_translations

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads((ROOT / 'docs/submission-reading-prepared-delta.json').read_text())
ADDED = {'src/word/short-tables.lua', 'src/word/short-tables.xml'}


def frozen(name, prototype=True):
    key = 'prototype' if prototype else 'baseline'
    root = ROOT / CONTRACT[key + '_archive']
    assert sha(root / 'checksums.json') == CONTRACT[key + '_seal_sha256']
    inventory = json.loads((root / 'checksums.json').read_text())
    assert name in inventory and sha(root / name) == inventory[name], name
    return json.loads((root / name).read_text())


def frozen_package(language, prototype=True):
    return frozen(('source-rehearsal/' if prototype else 'package/') + language + '.json', prototype)


def project_sources(current, language):
    expected = CONTRACT['languages'][language]
    hashes = lambda sources: {n: hashlib.sha256(v).hexdigest() for n, v in sources.items()}
    assert hashes(current) == expected['after'], 'Unreviewed 0.3.45 prepared source or asset'
    assert set(expected['after']) - set(expected['before']) == ADDED == set(expected['added'])
    assert not set(expected['before']) - set(expected['after'])
    assert expected['changed'] == sorted(n for n in expected['before'] if expected['before'][n] != expected['after'][n])
    assert len(expected['changed']) == 5 and all(n.endswith('.j2') for n in expected['changed'])
    previous = {n: v for n, v in current.items() if n not in ADDED}
    for file in frozen_package(language, False)['files']:
        assert file['fileName'] in previous
        previous[file['fileName']] = file['content'].encode()
    assert hashes(previous) == expected['before'], 'Projection must restore every 0.3.44 byte'
    return previous


def sources(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in (root / 'src').rglob('*') if p.is_file()}


def historical_view(root, language, destination):
    previous = project_sources(sources(root), language)
    destination.mkdir(parents=True, exist_ok=False)
    for name, value in previous.items():
        path = destination / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(value)
    return destination


def check_package(path, prepared, language, timestamp):
    from check_budget_grouping_integration import project_metadata
    current = sources(prepared); project_sources(current, language)
    baseline = frozen_package(language)
    members = frozen('source-rehearsal/source-build.json')['packages'][language]['asset_sha256']
    with zipfile.ZipFile(path) as package:
        names = package.namelist()
        assert len(names) == len(members) + 1 and set(names) == set(members) | {'template/template.json'}
        for name, digest in members.items():
            assert hashlib.sha256(package.read(name)).hexdigest() == digest, name
            assert package.read(name) == current[name.removeprefix('template/assets/')]
        candidate = json.loads(package.read('template/template.json'))
    for file in candidate['files']:
        assert file['content'].encode() == current[file['fileName']]
    project_metadata(candidate, baseline, timestamp, versions=('0.3.44', '0.3.45'))
    return dict(package_sha256=sha(path), prepared_source_verified=True,
        prototype_content_and_assets_identical=True, deterministic_identity_verified=True,
        changed_source_files=CONTRACT['languages'][language]['changed'], added_assets=sorted(ADDED))


def check(build, english, preview=False):
    from build import package_timestamp
    sys.path.insert(0, str(english / 'scripts'))
    from submission_reading_contract import project_source
    project_source()
    manifest = json.loads((build / 'manifest.json').read_text())
    assert manifest['status'] == ('preview' if preview else 'candidate')
    assert manifest['source']['version'] == manifest['translation']['version'] == '0.3.45'
    if not preview:
        assert all(not state['dirty'] for state in manifest['checkouts'].values())
        head = subprocess.check_output(['git', '-C', str(english), 'rev-parse', 'HEAD'], text=True).strip()
        assert manifest['source']['commit'] == manifest['checkouts']['english']['commit'] == head
    files = list((ROOT / 'translation/tree').rglob('translation.md'))
    current = [pair(p.read_text()) for p in files]
    project_submission_reading_translations(current)
    _, chain = verify_submission_translation_chain(current)
    assert manifest['translation_units'] == len(files) == 767 and not manifest['untranslated_units']
    assert manifest['translation_tree_sha256'] == {str(p.relative_to(ROOT / 'translation')): sha(p) for p in files}
    assert manifest['package_timestamp'] == package_timestamp(english)
    results = {}
    for language, folder in [('english', 'en'), ('chinese', 'translated')]:
        path = build / (language + '.zip'); assert sha(path) == manifest['sha256'][path.name]
        results[language] = check_package(path, build / folder, language, manifest['package_timestamp'])
    return dict(passed=True, preview=preview, source_integrated=True, release_acceptance=False,
        native_integrated_render_checked=False, global_switch_complete=False,
        translation_delta=chain['submission_reading'], packages=results)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', type=Path, required=True); p.add_argument('--english', type=Path, required=True)
    p.add_argument('--preview', action='store_true')
    a = p.parse_args(); result = check(a.build.resolve(), a.english.resolve(), a.preview)
    with (a.build / 'submission-reading-integration.json').open('x') as stream:
        stream.write(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__': main()
