"""Exact paired 0.3.50 Word assets, unchanged translations and bounded engine cases."""
import argparse
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import zipfile
from artifact_utils import sha
from check_budget_grouping_integration import asset_uuid

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads((ROOT / 'docs/word-empty-section-delta.json').read_text())

@lru_cache(maxsize=2)
def archive(phase):
    root = ROOT / CONTRACT[phase + '_archive']
    assert sha(root / 'checksums.json') == CONTRACT[phase + '_seal']
    assert all(sha(root / r['path']) == r['sha256'] for r in json.loads((root / 'checksums.json').read_text())['files'])
    return root

def helpers(phase):
    archive('prototype'); archive('baseline')
    result = {}
    for name, phases in CONTRACT['helpers'].items():
        record = phases[phase]; path = ROOT / record['fixture']
        assert sha(path) == record['sha256'], 'Changed Word fixture'
        result[name] = path.read_bytes()
    return result

def needs_projection(current):
    return any(name in current and hashlib.sha256(current[name]).hexdigest() != phases['before']['sha256']
               for name, phases in CONTRACT['helpers'].items())

def project_sources(current, language):
    from q3_policy_prose_integration import HELPER, project_sources as before_q3
    if HELPER in current: current = before_q3(current, language)
    from reuse_preparation_integration import CONTRACT as previous
    expected = dict(previous['languages'][language]['after'])
    before_helpers, after_helpers = helpers('before'), helpers('after')
    assert all(expected[n] == hashlib.sha256(v).hexdigest() for n,v in before_helpers.items())
    expected.update({n: hashlib.sha256(v).hexdigest() for n,v in after_helpers.items()})
    assert {n: hashlib.sha256(v).hexdigest() for n,v in current.items()} == expected, 'Unreviewed 0.3.50 prepared source or asset'
    before = {**current, **before_helpers}
    assert {n: hashlib.sha256(v).hexdigest() for n,v in before.items()} == previous['languages'][language]['after']
    assert {n for n in before if before[n] != current[n]} == set(CONTRACT['helpers'])
    return before

def integrated_package(language, timestamp):
    from reuse_preparation_integration import integrated_package as old
    result = old(language, timestamp)
    result['version'] = '0.3.50'; result['id'] = result['id'].removesuffix('0.3.49') + '0.3.50'
    for kind in ['files', 'assets']:
        for item in result[kind]:
            item['uuid'] = asset_uuid(result['id'], kind, item['fileName'])
    return result

def project_package(candidate, language, timestamp):
    if candidate['version'] == '0.3.51':
        from q3_policy_prose_integration import project_package as before_q3
        candidate = before_q3(candidate, language, timestamp)
    from reuse_preparation_integration import integrated_package as old
    assert candidate == integrated_package(language, timestamp), 'Unreviewed identity, source, asset metadata, UUID, timestamp or step'
    return old(language, timestamp)

def check_package(path, prepared, language, timestamp):
    with zipfile.ZipFile(path) as z:version = json.loads(z.read('template/template.json'))['version']
    if version == '0.3.51':
        from q3_policy_prose_integration import check_package as check_current
        return check_current(path, prepared, language, timestamp)
    from submission_flow_integration import sources, CONTRACT as old
    current = sources(prepared); previous = project_sources(current, language)
    members = old['languages'][language]['prototype']['assets']
    with zipfile.ZipFile(path) as z:
        assert len(z.namelist()) == len(members) + 1 and set(z.namelist()) == set(members) | {'template/template.json'}
        for name, digest in members.items():
            source_name = name.removeprefix('template/assets/')
            assert z.read(name) == current[source_name], 'ZIP asset differs from verified prepared bytes'
            assert hashlib.sha256(previous[source_name]).hexdigest() == digest
        metadata = json.loads(z.read('template/template.json'))
    project_package(metadata, language, timestamp)
    for item in metadata['files']: assert item['content'].encode() == current[item['fileName']]
    return dict(package_sha256=sha(path),prepared_source_verified=True,deterministic_identity_verified=True,
                exact_reviewed_word_assets=True,unchanged_nonword_assets=True)

def check(build, english, preview=False):
    from build import git, package_timestamp
    from submission_flow_integration import sources
    sys.path.insert(0, str(english / 'scripts'))
    from word_empty_section_contract import project_source, load
    prior_source, _ = project_source()
    assert helpers('before') == {n:prior_source[n] for n in CONTRACT['helpers']}
    assert helpers('after') == {n:(english / n).read_bytes() for n in CONTRACT['helpers']}
    manifest = json.loads((build / 'manifest.json').read_text())
    assert manifest['status'] == ('preview' if preview else 'candidate')
    version = manifest['source']['version']
    assert version == manifest['translation']['version'] and version in ['0.3.50', '0.3.51']
    if not preview:
        assert all(not row['dirty'] for row in manifest['checkouts'].values())
        assert manifest['source']['commit'] == manifest['checkouts']['english']['commit'] == git(english, 'rev-parse', 'HEAD')
    assert manifest['package_timestamp'] == package_timestamp(english)
    old_manifest = json.loads((archive('baseline') / 'build-manifest.json').read_text())
    tree = {str(p.relative_to(ROOT / 'translation')):sha(p) for p in (ROOT / 'translation/tree').rglob('translation.md')}
    assert len(tree) == manifest['translation_units'] == 775 and not manifest['untranslated_units']
    assert tree == manifest['translation_tree_sha256'] == old_manifest['translation_tree_sha256']
    packages, engines = {}, {}
    for language, folder in [('english','en'), ('chinese','translated')]:
        path = build / (language + '.zip'); assert sha(path) == manifest['sha256'][path.name]
        packages[language] = check_package(path, build / folder, language, manifest['package_timestamp'])
        before = project_sources(sources(build / folder), language)
        with tempfile.TemporaryDirectory(prefix='se-word-section-prior-') as temp:
            baseline = Path(temp)
            for name, value in before.items():
                p = baseline / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(value)
            rows = load('engine').run(baseline, build / folder, build / ('word-empty-section-engine-' + language + '.json'))
        engines[language] = len(rows['rows']); assert engines[language] == 121
    return dict(passed=True,source_integrated=True,version=version,comparison_version='0.3.50',
                historical_scope=version=='0.3.51',baseline_version='0.3.49',
                translation_units=775,translation_file_bytes_unchanged=True,changed_assets=sorted(CONTRACT['helpers']),
                packages=packages,engine_cases=engines,native_integrated_render_checked=False,release_acceptance=False)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True); parser.add_argument('--english', type=Path, required=True)
    parser.add_argument('--preview', action='store_true'); args = parser.parse_args()
    result = check(args.build.resolve(), args.english.resolve(), args.preview)
    with (args.build / 'word-empty-section-integration.json').open('x') as f:
        json.dump(result, f, indent=2); f.write('\n')
    print(json.dumps(result))
