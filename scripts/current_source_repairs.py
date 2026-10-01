"""Strictly project the current prepared bilingual sources to frozen 0.3.51.

The candidate is validated byte-for-byte before the committed English source
and layout preparation script reconstruct the historical prepared tree.  This
keeps old integration proofs meaningful for the registered current candidate.
"""
import hashlib
import json
from pathlib import Path
import tempfile
from copy import deepcopy
from check_budget_grouping_integration import asset_uuid

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads((ROOT / 'docs/current-source-repairs-delta.json').read_text())
Q3 = json.loads((ROOT / 'docs/q3-policy-prose-delta.json').read_text())


def is_current_version(version):
    return version == CONTRACT['candidate_version']


def is_q3_version(version):
    """Route the frozen Q3 version and only the registered current candidate."""
    return version == Q3['version'] or is_current_version(version)


def sha(value):
    return hashlib.sha256(value).hexdigest()


def tree_sha(values):
    digest = hashlib.sha256()
    for name, value in sorted(values.items()):
        digest.update(name.encode())
        digest.update(b'\0')
        digest.update(value)
    return digest.hexdigest()


def _validate_candidate(current, language):
    record = CONTRACT['languages'][language]
    baseline = Q3['languages'][language]['after']
    assert CONTRACT['release_approved'] is False, 'Development delta cannot approve release'
    assert len(current) == record['candidate_files'], 'Unexpected candidate source count'
    assert tree_sha(current) == record['candidate_tree_sha256'], 'Unreviewed current prepared source or asset'
    current_names, old_names = set(current), set(baseline)
    assert sorted(current_names - old_names) == CONTRACT['added'], 'Unexpected added prepared source'
    assert sorted(old_names - current_names) == CONTRACT['deleted'], 'Unexpected deleted prepared source'
    changed = sorted(
        name for name in current_names & old_names if sha(current[name]) != baseline[name]
    )
    assert changed == CONTRACT['changed'], 'Unexpected changed prepared source scope'


def project_sources(current, language, historical_files):
    """Return exact Q3-era prepared bytes after validating the current tree."""
    _validate_candidate(current, language)
    expected = Q3['languages'][language]['after']
    assert len(expected) == CONTRACT['languages'][language]['baseline_files']

    # q3_policy_prose_integration adds the English scripts directory to
    # sys.path and verifies this development contract before reaching here.
    import current_repairs_contract as english_contract

    raw, _ = english_contract.project_source()
    with tempfile.TemporaryDirectory(prefix='dsw-historical-layout-') as directory:
        temporary = Path(directory)
        template = temporary / 'template'
        for name, value in raw.items():
            path = template / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(value)
        font = temporary / 'PilotTC.ttf'
        font.write_bytes(current['src/fonts/PilotTC.ttf'])
        namespace = {'__name__': 'historical_prepare_layout'}
        source = english_contract.historical('scripts/prepare_layout.py')
        exec(compile(source, 'historical_prepare_layout.py', 'exec'), namespace)
        namespace['prepare_layout'](
            template, font, 'en' if language == 'english' else 'zh-Hant'
        )
        previous = {
            str(path.relative_to(template)): path.read_bytes()
            for path in (template / 'src').rglob('*') if path.is_file()
        }

    for item in historical_files:
        previous[item['fileName']] = item['content'].encode()
    # Chinese expansion adds the source font as an asset; it is unchanged and
    # therefore safe only when it matches the frozen historical digest.
    for name in set(expected) - set(previous):
        assert name in current and sha(current[name]) == expected[name]
        previous[name] = current[name]
    previous = {name: previous[name] for name in expected}
    assert {name: sha(value) for name, value in previous.items()} == expected, \
        'Historical prepared source did not reproduce exactly'
    return previous, {
        'current_files': len(current),
        'historical_files': len(previous),
        'current_tree_sha256': tree_sha(current),
        'added': CONTRACT['added'],
        'changed': CONTRACT['changed'],
    }


def project_package(candidate, language, timestamp, historical):
    """Seal current metadata, then restore the exact frozen identity and files."""
    record = CONTRACT['languages'][language]
    assert CONTRACT['release_approved'] is False, 'Development delta cannot approve release'
    assert candidate['createdAt'] == candidate['updatedAt'] == timestamp
    normalized = deepcopy(candidate)
    normalized['createdAt'] = normalized['updatedAt'] = '<timestamp>'
    encoded = json.dumps(
        normalized, ensure_ascii=False, sort_keys=True, separators=(',', ':')
    ).encode()
    assert sha(encoded) == record['candidate_metadata_sha256'], \
        'Unreviewed current package identity, source, UUID, format or asset metadata'
    assert is_current_version(candidate['version']), 'Unregistered candidate version'
    assert historical['version'] == CONTRACT['baseline_version'] == Q3['version']
    assert historical['id'].endswith(':' + historical['version'])
    assert candidate['id'] == historical['id'][:-len(historical['version'])] + candidate['version'], \
        'Candidate package identity is not the registered version-only change'
    previous = deepcopy(candidate)
    for kind in ['files', 'assets']:
        assert len({item['fileName'] for item in candidate[kind]}) == len(candidate[kind])
        for item in previous[kind]:
            assert item['uuid'] == asset_uuid(candidate['id'], kind, item['fileName']), \
                'Candidate file or asset UUID is not deterministic'
            item['uuid'] = asset_uuid(historical['id'], kind, item['fileName'])
        for item in historical[kind]:
            assert item['uuid'] == asset_uuid(historical['id'], kind, item['fileName'])
    previous['id'], previous['version'] = historical['id'], historical['version']
    current_files = {item['fileName']: item for item in previous['files']}
    old_files = {item['fileName']: item for item in historical['files']}
    assert sorted(set(current_files) - set(old_files)) == CONTRACT['added']
    assert not set(old_files) - set(current_files)
    assert sorted(
        name for name in old_files if current_files[name] != old_files[name]
    ) == [name for name in CONTRACT['changed'] if name in old_files]
    previous['files'] = deepcopy(historical['files'])
    assert previous == historical, 'Current package cannot project exactly to frozen 0.3.51'
    return previous, {
        'current_file_records': len(candidate['files']),
        'historical_file_records': len(historical['files']),
        'candidate_version': candidate['version'],
        'historical_version': historical['version'],
        'candidate_metadata_sha256': record['candidate_metadata_sha256'],
    }
