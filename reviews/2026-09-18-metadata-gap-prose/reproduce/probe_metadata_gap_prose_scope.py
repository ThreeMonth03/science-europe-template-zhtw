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
from probe_personal_data_translation import verify_prose_translation_chain
ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', type=Path, required=True); p.add_argument('--english', type=Path, required=True)
    a = p.parse_args(); sys.path[:0] = [str(a.english.resolve()/n) for n in ['scripts', 'tests']]
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
    personal, following = verify_prose_translation_chain([pair(f.read_text()) for f in files])
    current = json.loads((a.build/'manifest.json').read_text()); assert current['untranslated_units'] == []
    hashes = {str(f.relative_to(ROOT/'translation')): sha(f) for f in files}
    assert hashes == current['translation_tree_sha256']
    baseline = '06513da10808ec93e69302a0cffa6a766168d09a'
    data = subprocess.check_output(['git', '-C', str(ROOT), 'archive', baseline, 'translation/tree'])
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        old = {f.name: archive.extractfile(f).read() for f in archive if f.isfile()}
    new = {str(f.relative_to(ROOT)): f.read_bytes() for f in files}
    changed = {n for n in old.keys() | new.keys() if old.get(n) != new.get(n)}
    assert changed and all(n.startswith('translation/tree/src/questions/03-docs-metadata.html.j2/') for n in changed), 'Non-Q3 translation file changed'
    prior = ROOT/'reviews/2026-09-17-metadata-gap-panel/probes/storage-context-scope.json'
    proof = json.loads(prior.read_text()); checks = []
    for old_row in proof['rows']:
        folder = old_row['language']; root = a.build/folder; before = old_row['after']
        after = {str(f.relative_to(root)): sha(f) for f in (root/'src').rglob('*') if f.is_file()}
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
        assert sha(prose_frozen) == before['src/questions/03-docs-metadata.html.j2']
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
    report = {'passed': True, 'release_acceptance': False, 'rows': checks, 'reviewed_deltas': following,
        'translation_units': len(files), 'translation_tree_sha256': hashes, 'checker_sha256': sha(Path(__file__)),
        'contract_sha256': sha(a.english/'scripts/metadata_gap_prose_contract.py'),
        'package_sha256': {n: sha(a.build/n) for n in ['english.zip', 'chinese.zip']}}
    target = a.build/'metadata-gap-prose-scope.json'; assert not target.exists()
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'passed': True, 'q5_checks': sum(r['q5_checks'] for r in checks), 'units': len(files)}))


if __name__ == '__main__': main()
