"""Freeze new evidence; reference, never rewrite or duplicate, the prior archive."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'experiments/mixed-budget-header'))
from artifact_utils import sha
from compact import compact_source
from word_budget_geometry import inspect


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for n in ['before', 'after', 'comparison', 'structure', 'lifecycle', 'output']: p.add_argument('--' + n, type=Path, required=True)
    a = p.parse_args(); assert not a.output.exists()
    comparison = json.loads(a.comparison.read_text()); structure = json.loads((a.structure / 'report.json').read_text())
    assert comparison['selected_checks_passed'] and len(comparison['rows']) == 8
    assert comparison['checker_sha256'] == sha(ROOT / 'scripts/check_large_resource_groups.py')
    assert comparison['word_oracle_sha256'] == sha(ROOT / 'scripts/word_budget_geometry.py')
    assert structure['passed'] and structure['checker_sha256'] == sha(Path(__file__).with_name('probe.py'))
    life = json.loads(a.lifecycle.read_text())
    assert life['deleted_owned_templates'] == 2 and life['stock_worker_restored']
    assert not life['production_touched'] and all(r['status'] == 'exited' for r in life['after'])
    renders = json.loads((a.after / 'missing-info-render-report.json').read_text())
    assert renders['all_renders_succeeded'] and len(renders['renders']) == 24
    baseline = ROOT / 'reviews/2026-09-21-mixed-boundary-controls'
    a.output.mkdir(parents=True)
    def keep(path, name):
        dest = a.output / name; dest.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(path, dest)
    def write(name, value):
        dest = a.output / name; dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    keep(a.comparison, 'provenance/comparison.json'); keep(a.lifecycle, 'provenance/lifecycle.json')
    keep(a.before / 'manifest.json', 'provenance/before-manifest.json')
    for name in ['manifest.json', 'prototype.json', 'missing-info-render-report.json', 'owned-test-template-cleanup.json']:
        keep(a.after / name, 'provenance/' + name)
    previews = {}
    for receipt in a.after.glob('word-preview-*.json'):
        value = json.loads(receipt.read_text()); assert value['completed']
        keep(receipt, 'provenance/' + receipt.name)
        for row in value['rows']:
            assert row['name'] not in previews
            assert row['docx_sha256'] == sha(a.after / 'renders' / (row['name'] + '.docx'))
            assert row['preview_sha256'] == sha(a.after / 'word-preview' / (row['name'] + '.pdf'))
            previews[row['name']] = row
    assert set(previews) == {r['stem'] for r in comparison['rows']}
    for row in comparison['rows']:
        stem = row['stem']
        for fmt in ['html', 'pdf', 'docx']:
            path = a.after / 'renders' / (stem + '.' + fmt)
            if fmt == 'html':
                compact, assets = compact_source(path.read_bytes())
                dest = a.output / 'after/renders' / path.name; dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes(compact)
                write('after/renders/' + path.name + '.compact.json', dict(original_html_sha256=sha(path), fonts=assets,
                    compact_html_sha256=sha(dest), native_pdf_entry_input=False))
                assert compact_source((a.before / 'renders' / path.name).read_bytes())[0] == (baseline / 'after/renders' / path.name).read_bytes()
            else:
                assert sha(a.before / 'renders' / path.name) == sha(baseline / 'after/renders' / path.name)
                keep(path, 'after/renders/' + path.name)
            keep(path.with_suffix('.' + fmt + '.fixture.json'), 'after/renders/' + path.name + '.fixture.json')
        assert sha(a.before / 'word-preview' / (stem + '.pdf')) == sha(baseline / 'after/word-preview' / (stem + '.pdf'))
        keep(a.after / 'word-preview' / (stem + '.pdf'), 'after/word-preview/' + stem + '.pdf')
    # Save the exact small package JSON and Lua, with hashes of every ZIP member.
    package_proof = {}
    spec = importlib.util.spec_from_file_location('large_collect_recipe', Path(__file__).with_name('prototype.py'))
    recipe = importlib.util.module_from_spec(spec); spec.loader.exec_module(recipe)
    for language in ['english', 'chinese']:
        values = []; members = []
        for phase, folder in [('before', a.before), ('after', a.after)]:
            with zipfile.ZipFile(folder / (language + '.zip')) as z:
                values.append(json.loads(z.read('template/template.json')))
                members.append({n: hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()})
                write(f'package/{phase}-{language}.json', values[-1])
                dest = a.output / 'package' / f'{phase}-{language}.lua'
                dest.write_bytes(z.read('template/assets/src/word/pilot.lua'))
        assert recipe.project(values[1]) == values[0]
        assert recipe.patch_word((a.output / 'package' / f'before-{language}.lua').read_text()) == (a.output / 'package' / f'after-{language}.lua').read_text()
        changed = {n for n in members[0] if members[0][n] != members[1][n]}
        assert set(members[0]) == set(members[1]) and changed == {'template/template.json', 'template/assets/src/word/pilot.lua'}
        package_proof[language] = dict(members=members, zip_sha256=[sha(folder / (language + '.zip')) for folder in [a.before, a.after]])
    write('provenance/package-projection.json', package_proof)
    prior_word = []
    for phase in ['before', 'after']:
        for pdf in sorted((baseline / phase / 'word-preview').glob('*.pdf')):
            stem = pdf.stem; folder = baseline / phase / 'renders'
            prior_word.append(dict(phase=phase, stem=stem, preview_sha256=sha(pdf),
                result=inspect(folder / (stem + '.docx'), pdf, (folder / (stem + '.html')).read_text())))
    assert len(prior_word) == 40
    write('provenance/prior-word-cell-proof.json', dict(oracle_sha256=sha(ROOT / 'scripts/word_budget_geometry.py'), rows=prior_word,
        layout_acceptance=False, microsoft_word_acceptance=False))
    write('provenance/baseline-reference.json', dict(archive=baseline.name, phase='after', checksums_sha256=sha(baseline / 'checksums.json')))
    for path in a.structure.glob('*.json'): keep(path, 'structure/' + path.name)
    for name in ['prototype.py', 'probe.py', 'finish.py', 'collect.py']: keep(Path(__file__).with_name(name), 'reproduce/experiment/' + name)
    for name in ['word_budget_geometry.py', 'check_large_resource_groups.py', 'mixed_row_content.py', 'preview_word_short_budget.py']:
        keep(ROOT / 'scripts' / name, 'reproduce/' + name)
    for path in (ROOT / 'outputs').glob('large-resource-*.png'): keep(path, 'visual/' + path.name)
    write('inventory.json', dict(prototype_only=True, release_acceptance=False, microsoft_word_acceptance=False,
        version='0.3.42', source_repo_modified=False, translation_modified=False, native_pairs=8,
        new_native_artifacts=24, new_word_previews=8, prior_word_previews_reverified=40,
        full_control_matrix_complete=False, collector_sha256=sha(Path(__file__))))
    print(a.output)


if __name__ == '__main__': main()
