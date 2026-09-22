"""Freeze public, previously sealed prototype packages; never read project data.

One-shot fixture generator. Inputs must match the existing immutable receipts.
Existing fixture files are never overwritten.
"""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BASE = 'reviews/2026-09-22-submission-reading-integration'
PROTO = 'reviews/2026-09-22-full-km-followups'
BASE_SEAL = '4ba35be94dd77fb33357084e1df8ab05ab8ccc282267d0115197da233feb2f79'
PROTO_SEAL = '94f866ebbea8e4172dda380b30e50c24076280612b74930faf3aec14ba6acd69'


def digest(data): return hashlib.sha256(data).hexdigest()


def write(name, value):
    path = ROOT / name; path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream: stream.write(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    return digest(path.read_bytes())


def sealed(archive, seal):
    root = ROOT / archive
    assert digest((root / 'checksums.json').read_bytes()) == seal
    for name, value in json.loads((root / 'checksums.json').read_text()).items():
        assert digest((root / name).read_bytes()) == value, name


def run(baseline, prototype):
    sealed(BASE, BASE_SEAL); sealed(PROTO, PROTO_SEAL)
    receipt = json.loads((ROOT / PROTO / 'build/manifest.json').read_text())
    result = dict(schema_version=1, baseline_archive=BASE, baseline_seal_sha256=BASE_SEAL,
        prototype_archive=PROTO, prototype_seal_sha256=PROTO_SEAL, languages={})
    for language in ['english', 'chinese']:
        phases = {}; metadata = {}; assets = {}
        for phase, root, expected in [('before', baseline, receipt['baseline_packages']),
                                      ('after', prototype, receipt['sha256'])]:
            path = root / (language + '.zip'); assert digest(path.read_bytes()) == expected[path.name]
            with zipfile.ZipFile(path) as archive:
                package = json.loads(archive.read('template/template.json'))
                source = {f['fileName']: digest(f['content'].encode()) for f in package['files']}
                members = {n: digest(archive.read(n)) for n in archive.namelist() if n != 'template/template.json'}
                source.update({n.removeprefix('template/assets/'): v for n, v in members.items()})
            phases[phase] = source; metadata[phase] = package; assets[phase] = members
        assert assets['before'] == assets['after']
        assert metadata['before'] == json.loads((ROOT / BASE / 'native' / (language + '.json')).read_text())
        assert not set(phases['before']) - set(phases['after'])
        changed = sorted(n for n in phases['before'] if phases['before'][n] != phases['after'][n])
        added = sorted(set(phases['after']) - set(phases['before']))
        assert changed == receipt['changed_source_files'] and added == receipt['added_source_files']
        name = f'tests/fixtures/full-km-followups/{language}.json'
        fixture_sha = write(name, metadata['after'])
        result['languages'][language] = dict(**phases, changed=changed, added=added,
            prototype_fixture=name, prototype_fixture_sha256=fixture_sha,
            asset_sha256=assets['after'], prototype_zip_sha256=receipt['sha256'][language + '.zip'])
    write('docs/full-km-followups-prepared-delta.json', result)
    pairs = receipt['translation_delta']['added_pairs']
    write('docs/full-km-followups-translation-delta.json', dict(
        baseline='0b14a4ead11bbd1c2b77888d94639740409fc6f4', baseline_units=767,
        current_units=773, retained_units=767, removed=[], added=pairs))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline', type=Path, required=True); p.add_argument('--prototype', type=Path, required=True)
    args = p.parse_args(); run(args.baseline, args.prototype)
