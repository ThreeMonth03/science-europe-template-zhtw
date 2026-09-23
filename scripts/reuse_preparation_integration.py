"""Exact paired 0.3.49 packages and translations, then verified 0.3.48 test views."""
import argparse
from collections import Counter
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import sys
from artifact_utils import sha
from check_budget_grouping_integration import asset_uuid

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads((ROOT / 'docs/reuse-preparation-delta.json').read_text())
QUESTION = CONTRACT['question']


@lru_cache(maxsize=1)
def units():
    archive = ROOT / CONTRACT['prototype_archive']
    assert sha(archive / 'checksums.json') == CONTRACT['prototype_seal']
    assert all(sha(archive / r['path']) == r['sha256'] for r in json.loads((archive / 'checksums.json').read_text())['files'])
    assert (ROOT / 'experiments/reuse-preparation-prose/units.json').read_bytes() == (archive / 'units.json').read_bytes()
    return json.loads((archive / 'units.json').read_text())


def question(language):
    units()
    record = CONTRACT['languages'][language]; path = ROOT / record['question_fixture']
    assert sha(path) == record['question_sha256'] == record['after'][QUESTION]
    return path.read_bytes()


def needs_projection(current, language):
    value = current.get(QUESTION)
    return value is not None and hashlib.sha256(value).hexdigest() != CONTRACT['languages'][language]['before'][QUESTION]


def project_sources(current, language):
    from word_empty_section_integration import needs_projection, project_sources as before_word
    if needs_projection(current): current = before_word(current, language)
    record = CONTRACT['languages'][language]
    hashes = lambda values: {n: hashlib.sha256(v).hexdigest() for n, v in values.items()}
    assert hashes(current) == record['after'], 'Unreviewed 0.3.49 prepared source or asset'
    assert current[QUESTION] == question(language)
    from empty_section_spacing_integration import integrated_package as old
    before = dict(current)
    before[QUESTION] = next(f['content'].encode() for f in old(language, '2000-01-01T00:00:00Z')['files'] if f['fileName'] == QUESTION)
    assert hashes(before) == record['before'], 'Every 0.3.48 source byte must be restored'
    assert {n for n in before if before[n] != current[n]} == {QUESTION}
    return before


def integrated_package(language, timestamp):
    from empty_section_spacing_integration import integrated_package as old
    result = old(language, timestamp)
    result['version'] = '0.3.49'; result['id'] = result['id'].removesuffix('0.3.48') + '0.3.49'
    for kind in ['files', 'assets']:
        for item in result[kind]:
            item['uuid'] = asset_uuid(result['id'], kind, item['fileName'])
            if kind == 'files' and item['fileName'] == QUESTION:
                item['content'] = question(language).decode()
    return result


def project_package(candidate, language, timestamp):
    if candidate['version'] in ['0.3.50', '0.3.51']:
        from word_empty_section_integration import project_package as before_word
        candidate = before_word(candidate, language, timestamp)
    from empty_section_spacing_integration import integrated_package as old
    assert candidate == integrated_package(language, timestamp), 'Unreviewed identity, source, asset, UUID, timestamp or format step'
    return old(language, timestamp)


def has_new_translations(current):
    new_sources = {u['en'] for u in units()}
    return any(source in new_sources for source, _ in current)


def project_translations(current):
    from probe_personal_data_translation import archived_pairs
    previous = archived_pairs(CONTRACT['baseline_translation_commit'])
    old, new = Counter(previous), Counter(current)
    removed = Counter((u['old_en'], u['old_zh']) for u in units())
    added = Counter((u['en'], u['zh']) for u in units())
    assert old.total() == new.total() == 775
    assert old - new == removed and new - old == added, 'Unreviewed preparation translation delta'
    assert (old & new).total() == 766
    return previous, dict(baseline_units=775, current_units=775, retained_units=766, removed_units=9, added_units=9)


def check(build, english, preview=False):
    from build import package_timestamp, git
    from submission_flow_integration import sources, check_package
    from probe_pdf_budget_translation import pair
    sys.path.insert(0, str(english / 'scripts'))
    from reuse_preparation_contract import project_source, load
    project_source()
    manifest = json.loads((build / 'manifest.json').read_text())
    assert manifest['status'] == ('preview' if preview else 'candidate')
    version = manifest['source']['version']
    assert version == manifest['translation']['version'] and version in ['0.3.49', '0.3.50', '0.3.51']
    if not preview:
        assert all(not state['dirty'] for state in manifest['checkouts'].values())
        assert manifest['source']['commit'] == manifest['checkouts']['english']['commit'] == git(english, 'rev-parse', 'HEAD')
    assert manifest['package_timestamp'] == package_timestamp(english)
    documents = list((ROOT / 'translation/tree').rglob('translation.md'))
    pairs = [pair(p.read_text()) for p in documents]
    _, delta = project_translations(pairs)
    assert len(documents) == manifest['translation_units'] == 775 and not manifest['untranslated_units']
    assert manifest['translation_tree_sha256'] == {str(p.relative_to(ROOT / 'translation')): sha(p) for p in documents}
    packages, branches = {}, {}
    for language, folder in [('english', 'en'), ('chinese', 'translated')]:
        path = build / (language + '.zip'); assert sha(path) == manifest['sha256'][path.name]
        packages[language] = check_package(path, build / folder, language, manifest['package_timestamp'])
        after = sources(build / folder)
        if version in ['0.3.50', '0.3.51']:
            from word_empty_section_integration import project_sources as before_word
            after = before_word(after, language)
        before = project_sources(after, language)
        rows = load('probe').check(english, before, after,
            {u['en']: u['zh'] for u in units()} if language == 'chinese' else None,
            {u['en']: u['old_zh'] for u in units()} if language == 'chinese' else None)
        branches[language] = len(rows); assert len(rows) == 8208
    return dict(passed=True, source_integrated=True, release_acceptance=False, native_integrated_render_checked=False,
        version=version, comparison_version='0.3.49', historical_scope=version in ['0.3.50', '0.3.51'], baseline_version='0.3.48', translation_delta=delta,
        packages=packages, branch_checks=branches, css_and_word_steps_unchanged=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--english', type=Path, required=True)
    parser.add_argument('--preview', action='store_true')
    args = parser.parse_args(); result = check(args.build.resolve(), args.english.resolve(), args.preview)
    with (args.build / 'reuse-preparation-integration.json').open('x') as f:
        json.dump(result, f, indent=2); f.write('\n')
    print(json.dumps(result))
