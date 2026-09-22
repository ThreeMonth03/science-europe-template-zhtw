"""Build empty-heading layout on the verified Q1 prototype, preserving all translations."""
import argparse
from collections import Counter
from dataclasses import asdict
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile
import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from artifact_utils import sha, canonicalize_zip
from build import git, localize_format_names
from probe_pdf_budget_translation import pair
from dsw_document_template_tool.template_transform import expand_template_dir
from dsw_document_template_tool.translation_tree import (export_translation_tree, merge_translation_tree,
    sync_translation_tree, audit_translation_tree, audit_translated_template_structure)
import dsw_document_template_tool

BASELINE_HASHES = {'english.zip':'c6d6bcb7e18cd6733107b24894e4bd23513e205e9b310e994cf477062d53dcf0',
    'chinese.zip':'bf1151e7c2b2a436f4dd47177bda2294bc2f2b342cd9757eaaa3891dcad6b45b'}


def write(path, value): path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def package_sources(path, prepared):
    with zipfile.ZipFile(path) as package:
        spec = json.loads(package.read('template/template.json'))
        for kind in ['files', 'assets']:
            for item in spec[kind]:
                value = item['content'].encode() if kind == 'files' else package.read('template/assets/' + item['fileName'])
                assert (prepared / item['fileName']).read_bytes() == value
    return spec, {f['fileName']:f['content'] for f in spec['files']}


def run(english, tooling, baseline, output):
    assert not output.exists(), 'Never overwrite previous evidence'
    config = yaml.safe_load((ROOT / 'pipeline.yml').read_text())
    assert git(tooling, 'rev-parse', 'HEAD') == config['tooling']['commit'] and not git(tooling, 'status', '--porcelain')
    assert Path(dsw_document_template_tool.__file__).resolve().is_relative_to(tooling / 'src')
    previous = json.loads((baseline / 'manifest.json').read_text())
    assert previous['status'] == 'prototype' and previous['sha256'] == BASELINE_HASHES
    assert previous['checks'] == {'english':1844, 'chinese':1844}
    assert Counter(pair(p.read_text()) for p in (baseline / 'translation').rglob('translation.md')).total() == 775
    for name, digest in previous['recipes'].items():
        # The historical flat manifest stores the Chinese README on this shared
        # path. All executable recipe paths are unique; do not guess by existence.
        root = ROOT if name.endswith('/README.md') or name.endswith('/build_prototype.py') or name.endswith('.json') else english
        assert sha(root / name) == digest, ('Original prototype recipe changed', name)
    bases = {}
    for language, folder in [('english','en'), ('chinese','translated')]:
        assert sha(baseline / (language + '.zip')) == BASELINE_HASHES[language + '.zip']
        bases[language] = package_sources(baseline / (language + '.zip'), baseline / folder)
    recipe = load(english / 'experiments/empty-question-spacing/recipe.py', 'spacing_recipe')
    probe = load(english / 'experiments/empty-question-spacing/probe.py', 'spacing_probe')
    reuse = recipe.load_reuse(english)
    raw = {str(p.relative_to(english)):p.read_bytes() for p in (english / 'src').rglob('*') if p.is_file()}
    raw = reuse.overlay(raw, english); changed = recipe.overlay(raw, english)
    output.mkdir(parents=True)
    for folder in ['en', 'zh-Hant']:
        shutil.copytree(baseline / folder, output / folder)
        for name in [recipe.CONTENT, 'src/layout.css', *recipe.HELPERS]:
            target = output / folder / name; target.parent.mkdir(parents=True, exist_ok=True)
            if name == 'src/layout.css': target.write_bytes(target.read_bytes() + recipe.CSS)
            else:
                if name in raw: assert target.read_bytes() == raw[name]
                target.write_bytes(changed[name])
        path = output / folder / 'template.json'; spec = recipe.metadata(json.loads(path.read_text()))
        spec.update(templateId='science-europe-empty-question-prototype', version='0.3.47',
            name='Science Europe — empty question spacing prototype (not for submission)')
        write(path, spec)
    expanded = output / 'expanded'
    expand_template_dir(source_dir=output / 'zh-Hant', output_dir=expanded,
        profile=config['tooling']['profile'], exclude_profile_paths=tuple(config['tooling']['exclude_profile_paths']))
    export_translation_tree(source_dir=expanded, output_dir=output / 'fresh', source_lang='en', target_lang='zh_Hant')
    tree = output / 'translation'
    migration = merge_translation_tree(old_tree_dir=baseline / 'translation', new_tree_dir=output / 'fresh',
        output_dir=tree, source_lang='en', target_lang='zh_Hant')
    write(output / 'migration.json', asdict(migration))
    before = Counter(pair(p.read_text()) for p in (baseline / 'translation').rglob('translation.md'))
    after = Counter(pair(p.read_text()) for p in tree.rglob('translation.md'))
    assert before == after and after.total() == 775, 'Any translation change is out of scope'
    assert not audit_translation_tree(tree_dir=tree, source_dir=expanded)
    sync_translation_tree(tree_dir=tree, source_dir=expanded, output_dir=output / 'translated',
        source_lang='en', target_lang='zh_Hant', template_organization_id=config['translation']['organization_id'],
        template_id='science-europe-empty-question-prototype-zhtw', template_name='Science Europe 空題間距原型（非提交版）',
        template_version='0.3.47', public_readme_path=ROOT / 'PACKAGE_README.md')
    path = output / 'translated/template.json'; spec = json.loads(path.read_text())
    localize_format_names(spec, config['translation']['format_names']); write(path, spec)
    assert not audit_translated_template_structure(source_dir=expanded, output_dir=output / 'translated')
    timestamp = bases['english'][0]['createdAt']
    result = dict(status='prototype', prototype_only=True, source_integrated=False, release_acceptance=False,
        baseline_packages=BASELINE_HASHES, translation_units=775, translation_pairs_unchanged=True,
        tooling_commit=config['tooling']['commit'], checks={}, sha256={},
        source_changes=[recipe.CONTENT, 'src/layout.css', *recipe.HELPERS],
        metadata_change='Only submission Word filter and document.xml rewrite; separate prototype identity',
        recipes={label:{str(p.relative_to(root)):sha(p) for p in (root / 'experiments/empty-question-spacing').rglob('*') if p.is_file() and '__pycache__' not in p.parts} for label,root in [('english',english),('chinese',ROOT)]},
        checkouts={name:dict(commit=git(root, 'rev-parse', 'HEAD'), dirty=bool(git(root, 'status', '--porcelain'))) for name,root in [('english',english),('chinese',ROOT)]})
    tdk = tooling / '.venv/bin/dsw-tdk'
    for language, folder in [('english','en'), ('chinese','translated')]:
        for command in [[str(tdk), '--no-config', 'verify', str(output / folder)],
                [str(tdk), '--no-config', 'package', str(output / folder), '--output', str(output / (language + '.zip'))]]:
            subprocess.run(command, check=True, capture_output=True)
        canonicalize_zip(output / (language + '.zip'), timestamp)
        spec, sources = package_sources(output / (language + '.zip'), output / folder)
        with zipfile.ZipFile(output / (language + '.zip')) as current, zipfile.ZipFile(baseline / (language + '.zip')) as prior:
            assets = set(current.namelist()) - {'template/template.json'}
            assert assets - set(prior.namelist()) == {'template/assets/src/word/question-spacing.lua', 'template/assets/src/word/question-spacing.xml'}
            assert set(prior.namelist()) - set(current.namelist()) == set()
            for name in set(prior.namelist()) - {'template/template.json'}:
                expected = prior.read(name) + (recipe.CSS if name == 'template/assets/src/layout.css' else b'')
                assert current.read(name) == expected, ('Unrelated asset drift', name)
        rows = probe.check(english, bases[language][1], sources)
        write(output / (language + '-checks.json'), rows)
        result['checks'][language] = len(rows); result['sha256'][language + '.zip'] = sha(output / (language + '.zip'))
    write(output / 'manifest.json', result)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for key in ['english','tooling','baseline','output']: p.add_argument('--' + key, type=Path, required=True)
    a = p.parse_args(); result = run(a.english.resolve(), a.tooling.resolve(), a.baseline.resolve(), a.output.resolve())
    print(json.dumps(dict(passed=True, prototype_only=True, checks=result['checks'], translations_unchanged=775)))
