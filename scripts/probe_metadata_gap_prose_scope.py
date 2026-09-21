"""Exact 0.3.36 -> 0.3.37 Q3/CSS delta; retain prior Q2/Q3/Q5/Q11 gates."""
import argparse
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
from artifact_utils import sha
from probe_pdf_budget_translation import pair
from probe_personal_data_translation import verify_prose_translation_chain, verify_output_profile_translation_chain
ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', type=Path, required=True); p.add_argument('--english', type=Path, required=True)
    p.add_argument('--output-profiles', action='store_true', help='Exact 0.3.37→0.3.38 pilot delta; retain every prior review-profile contract')
    p.add_argument('--preservation-reading', action='store_true', help='Verify the exact 0.3.39 filter/style addition before running all historical gates')
    p.add_argument('--short-resources', action='store_true', help='Verify exact 0.3.40 PDF-entry-only addition first')
    p.add_argument('--resource-prose', action='store_true', help='Project the exact 0.3.41 owned Q15 pair before all historical gates')
    p.add_argument('--short-resource-rows', action='store_true', help='Project the exact 0.3.42 PDF-only short-row addition first')
    p.add_argument('--budget-grouping', action='store_true', help='Prove exact 0.3.43 source/prepared projection before every older gate')
    p.add_argument('--submission-preview', action='store_true', help='Validate 0.3.44, then run historical gates on exactly verified 0.3.43 source views')
    a = p.parse_args(); sys.path[:0] = [str(a.english.resolve()/n) for n in ['scripts', 'tests']]
    assert not a.preservation_reading or a.output_profiles
    assert not a.short_resources or a.preservation_reading
    assert not a.resource_prose or a.short_resources
    assert not a.short_resource_rows or a.resource_prose
    assert not a.budget_grouping or a.short_resource_rows
    assert not a.submission_preview or a.budget_grouping
    from storage_context_contract import check_roots as context_checks
    from probe_storage_context import strip
    from q5_word_join_contract import prior_lua
    from metadata_gap_panel_contract import historical_css
    from metadata_gap_prose_contract import check_roots as prose_checks
    import hashlib
    from storage_gap_contract import check_roots as storage_checks
    from metadata_followup_contract import check_roots as metadata_checks, expected as metadata_projection
    from format_reading_contract import check_roots as format_checks
    from archive_basis_contract import check_roots as archive_checks
    from probe_archive_gap_panels import rows, FIRST, LAST, PAIRS
    from bs4 import BeautifulSoup
    files = sorted((ROOT/'translation/tree').rglob('translation.md'))
    verifier = verify_output_profile_translation_chain if a.output_profiles else verify_prose_translation_chain
    if a.submission_preview:
        from probe_personal_data_translation import verify_submission_translation_chain
        verifier = verify_submission_translation_chain
    personal, following = verifier([pair(f.read_text()) for f in files])
    current = json.loads((a.build/'manifest.json').read_text()); assert current['untranslated_units'] == []
    hashes = {str(f.relative_to(ROOT/'translation')): sha(f) for f in files}
    assert hashes == current['translation_tree_sha256']
    baseline = 'ecda664c078d7e9dba6d48fcd3ca785027eb9746' if a.output_profiles else '06513da10808ec93e69302a0cffa6a766168d09a'
    data = subprocess.check_output(['git', '-C', str(ROOT), 'archive', baseline, 'translation/tree'])
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        old = {f.name: archive.extractfile(f).read() for f in archive if f.isfile()}
    new = {str(f.relative_to(ROOT)): f.read_bytes() for f in files}
    if a.submission_preview:
        from submission_preview_integration import historical_translation_documents
        new = historical_translation_documents()
    changed = {n for n in old.keys() | new.keys() if old.get(n) != new.get(n)}
    allowed_translation = ('translation/tree/src/quality-control.html.j2/', 'translation/tree/src/questions/03-docs-metadata.html.j2/') if a.output_profiles else ('translation/tree/src/questions/03-docs-metadata.html.j2/',)
    assert changed and all(n.startswith(allowed_translation) for n in changed), 'Unreviewed translation file changed'
    prior = ROOT/'reviews/2026-09-17-metadata-gap-panel/probes/storage-context-scope.json'
    proof = json.loads(prior.read_text()); checks = []
    for old_row in proof['rows']:
        folder = old_row['language']; root = a.build/folder; historic_before = old_row['after']; before = historic_before
        after = {str(f.relative_to(root)): sha(f) for f in (root/'src').rglob('*') if f.is_file()}
        actual_after = dict(after)
        if a.submission_preview:
            from submission_preview_integration import historical_view
            language = 'english' if folder == 'en' else 'chinese'
            root = historical_view(root, language, a.build / 'historical-0.3.43' / folder)
            after = {str(f.relative_to(root)): sha(f) for f in (root / 'src').rglob('*') if f.is_file()}
        if a.budget_grouping:
            from budget_grouping_contract import project_prepared as project_grouping
            after = project_grouping(root, after)
            frozen = json.loads((ROOT/'reviews/2026-09-18-short-resource-rows/provenance/candidate-short-resource-rows-scope.json').read_text())
            assert after == next(r['after'] for r in frozen['rows'] if r['language'] == folder), 'Grouping projection must restore every frozen 0.3.42 prepared byte'
        if a.short_resource_rows:
            from short_resource_rows_contract import project_prepared as project_rows
            after = project_rows(root, after)
            frozen = json.loads((ROOT/'reviews/2026-09-18-resource-prose-native/provenance/candidate-resource-prose-scope.json').read_text())
            assert after == next(r['after'] for r in frozen['rows'] if r['language'] == folder), 'Row projection must restore every frozen 0.3.41 prepared byte'
        if a.resource_prose:
            from resource_prose_contract import project_prepared as project_resource_prose
            after = project_resource_prose(root, after)
            frozen = json.loads((ROOT/'reviews/2026-09-18-short-resources/provenance/candidate-short-resources-scope.json').read_text())
            assert after == next(r['after'] for r in frozen['rows'] if r['language'] == folder), 'Q15 projection must restore every frozen 0.3.40 prepared byte'
        if a.short_resources:
            from short_resources_contract import project_prepared as project_pdf
            after = project_pdf(root, after)
            frozen = json.loads((ROOT/'reviews/2026-09-18-preservation-reading/provenance/candidate-preservation-reading-scope.json').read_text())
            assert after == next(r['after'] for r in frozen['rows'] if r['language'] == folder)
        if a.preservation_reading:
            from preservation_reading_contract import project_prepared, source_delta
            after = project_prepared(root, after, 'en' if folder == 'en' else 'zh-Hant')
            frozen_profile = json.loads((ROOT/'reviews/2026-09-18-output-profiles/provenance/output-profiles-scope.json').read_text())
            frozen_hashes = next(r['after'] for r in frozen_profile['rows'] if r['language'] == folder)
            assert after == frozen_hashes, 'After removing exactly the new filter/style, every 0.3.38 prepared source hash must match'
        if a.output_profiles:
            from output_profile_contract import CONTRACT, check as profile_checks
            previous = json.loads((ROOT/'reviews/2026-09-18-metadata-gap-prose/probes/metadata-gap-prose-scope.json').read_text())
            before = next(row['after'] for row in previous['rows'] if row['language'] == folder)
            assert set(after)-set(before) == set(CONTRACT['new_source_files'])
            assert not set(before)-set(after)
            differences = sorted(n for n in before if before[n] != after[n])
            assert differences == sorted(CONTRACT['changed_source_files']), differences
            profile_rows = profile_checks(root, a.english/'fixtures/pilot'/('en' if folder == 'en' else 'zh-Hant'), 'english' if folder == 'en' else 'chinese')
        else:
            assert before.keys() == after.keys()
            differences = sorted(n for n in before if before[n] != after[n])
            assert differences == ['src/layout.css', 'src/questions/03-docs-metadata.html.j2'], differences
            source = (root/'src/layout.css').read_text()
            assert hashlib.sha256(historical_css(source).encode()).hexdigest() == before['src/layout.css'], 'CSS delta is not the exact retired block'
        language = 'english' if folder == 'en' else 'chinese'
        fixtures = a.english/'tests/fixtures' if folder == 'en' else ROOT/'tests/fixtures'
        suffix = 'en' if folder == 'en' else 'zh-Hant'
        frozen = fixtures/f'storage-0.3.31.{suffix}.html.j2'
        assert sha(frozen) == ('0f929ac601ffb00aa6d8a7352fa4edcb2fd1ab0ed2d4a3daa3b07190bac7dded' if folder == 'en' else '682ba623c03082a9b7d25b616c1fd557d862a5fc3b552817f3d0492d1e5abce3')
        prose_frozen = fixtures/f'metadata-0.3.36.{suffix}.html.j2'
        assert sha(prose_frozen) == historic_before['src/questions/03-docs-metadata.html.j2']
        prose_count = prose_checks(root, prose_frozen, language)
        count = storage_checks(root, frozen, language, following_projection=metadata_projection)
        context_frozen = fixtures/f'storage-context-0.3.33.{suffix}.html.j2'
        context_proof = json.loads((ROOT/'reviews/2026-09-17-metadata-followups/probes/metadata-followup-scope.json').read_text())
        context_row = next(row for row in context_proof['rows'] if row['language'] == folder)
        assert sha(context_frozen) == context_row['after']['src/questions/05-store-backup.html.j2']
        context_rows = context_checks(root, a.english/'fixtures/pilot'/('en' if folder=='en' else 'zh-Hant'), context_frozen)
        metadata_frozen = fixtures/f'metadata-0.3.32.{suffix}.html.j2'
        assert sha(metadata_frozen) == ('47cc7a83c6dca520b730b314f794fd607a18811a167b5b511095f3b2b9c27b4c' if folder == 'en' else '291997e5be453d528ffb72dd2499c8c6e8f73d4923ca4f6708710db562ff58ee')
        metadata_count = metadata_checks(root, metadata_frozen, language)
        q2 = format_checks(root, fixtures/f'format-0.3.30.{suffix}.html.j2', language)
        q11 = archive_checks(root, fixtures/f'archive-0.3.28.{suffix}.html.j2', language)
        gaps = 0
        for _, html, expected in rows(root):
            soup = BeautifulSoup(html, 'html.parser'); found = []
            for ids, left, right in zip(PAIRS, FIRST, LAST):
                assert len(soup.select(left)) == len(soup.select(right))
                if soup.select(left): found.append(list(ids))
            assert found == expected; gaps += 1
        checks.append({'language': folder, 'before': before, 'after': after, 'changed': differences,
            'prose_checks': prose_count, 'q5_checks': len(context_rows), 'q5_eligible': sum(r['eligible'] for r in context_rows), 'q3_exact_dom_checks': metadata_count, 'q3_retained_capacity_checks': count, 'q2_exact_dom_checks': q2, 'q11_branch_checks': q11,
            'q11_gap_combinations': gaps, 'frozen_sha256': sha(frozen)})
        if a.output_profiles: checks[-1]['output_profile_checks'] = profile_rows
        if a.preservation_reading:
            checks[-1].update(historical_projection_after=after, after=actual_after,
                projected_changed=differences, source_delta=source_delta(),
                changed=sorted(n for n in before if before[n] != actual_after[n]),
                added=sorted(set(actual_after)-set(before)))
        if a.short_resources:
            checks[-1]['pdf_entry_delta'] = {'baseline_version': '0.3.39', 'version': '0.3.40',
                'entry_sha256': sha(root/'src/pdf/index.html.j2'),
                'helper_sha256': sha(root/'src/pdf/short-resources.html.j2')}
        if a.resource_prose:
            checks[-1]['resource_prose_delta'] = {'baseline_version':'0.3.40', 'version':'0.3.41',
                'question_sha256':sha(root/'src/questions/15-required-resources.html.j2'),
                'helper_sha256':sha(root/'src/resource-prose.html.j2')}
        if a.short_resource_rows:
            checks[-1]['short_resource_rows_delta'] = {'baseline_version':'0.3.41', 'version':'0.3.42',
                'entry_sha256':sha(root/'src/budget-reading.html.j2'),
                'helper_sha256':sha(root/'src/pdf/short-resource-rows.html.j2')}
        if a.budget_grouping:
            checks[-1]['budget_grouping_delta'] = {'baseline_version':'0.3.42', 'version':'0.3.43',
                'changed_files':['src/budget-reading.html.j2','src/word/pilot.lua','src/layout.css']}
        if a.submission_preview:
            checks[-1]['submission_preview_delta'] = {'baseline_version': '0.3.43', 'version': '0.3.44',
                'historical_checks_use_exact_verified_source_view': True,
                'current_behavior_checker': 'scripts/probe_submission_preview.py'}
    report = {'passed': True, 'release_acceptance': False, 'rows': checks, 'reviewed_deltas': following,
        'translation_units': len(files), 'translation_tree_sha256': hashes, 'checker_sha256': sha(Path(__file__)),
        'contract_sha256': sha(a.english/'scripts/metadata_gap_prose_contract.py'),
        'package_sha256': {n: sha(a.build/n) for n in ['english.zip', 'chinese.zip']}}
    target = a.build/('budget-grouping-scope.json' if a.budget_grouping else 'short-resource-rows-scope.json' if a.short_resource_rows else 'resource-prose-scope.json' if a.resource_prose else 'short-resources-scope.json' if a.short_resources else 'preservation-reading-scope.json' if a.preservation_reading else 'output-profiles-scope.json' if a.output_profiles else 'metadata-gap-prose-scope.json'); assert not target.exists()
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'passed': True, 'q5_checks': sum(r['q5_checks'] for r in checks), 'units': len(files)}))


if __name__ == '__main__': main()
