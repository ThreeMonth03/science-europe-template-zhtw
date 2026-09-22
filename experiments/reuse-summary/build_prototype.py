"""Build a separate EN -> translation-tree -> ZH prototype; production stays locked."""
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
from submission_reading_integration import check_package
from dsw_document_template_tool.template_transform import expand_template_dir
from dsw_document_template_tool.translation_tree import (export_translation_tree, merge_translation_tree,
    sync_translation_tree, audit_translation_tree, audit_translated_template_structure)
from dsw_document_template_tool._translation_tree.document import (
    parse_sentence_text, parse_translation_document, replace_translation_text)
import dsw_document_template_tool

BASELINE_HASHES = {
    'english.zip': '2644ee2a3a1ec07be183a7f34c927729e13c7a09245a62874c1404c46bc31695',
    'chinese.zip': '0df6effa882bf7001ca545f8846bcae8689e2c1969516d399151222917628e5c'}


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def run(english, tooling, baseline, output):
    assert not output.exists(), 'Never overwrite earlier evidence'
    config = yaml.safe_load((ROOT / 'pipeline.yml').read_text())
    recipe = load(english / 'experiments/reuse-summary/recipe.py', 'reuse_recipe')
    probe = load(english / 'experiments/reuse-summary/probe.py', 'reuse_probe')
    assert config['source']['commit'] == recipe.BASELINE
    assert config['source']['version'] == config['translation']['version'] == '0.3.46'
    assert git(tooling, 'rev-parse', 'HEAD') == config['tooling']['commit']
    assert not git(tooling, 'status', '--porcelain')
    assert Path(dsw_document_template_tool.__file__).resolve().is_relative_to(tooling / 'src')
    manifest = json.loads((baseline / 'manifest.json').read_text())
    assert manifest['source'] == config['source'] and manifest['translation'] == config['translation']
    assert manifest['status'] == 'candidate' and manifest['translation_units'] == 773 and not manifest['untranslated_units']
    assert manifest['translation_tree_sha256'] == {str(p.relative_to(ROOT / 'translation')): sha(p) for p in (ROOT / 'translation').rglob('translation.md')}
    for language, folder in [('english', 'en'), ('chinese', 'translated')]:
        path = baseline / (language + '.zip')
        assert sha(path) == BASELINE_HASHES[path.name] == manifest['sha256'][path.name]
        check_package(path, baseline / folder, language, manifest['package_timestamp'])
    raw = {str(p.relative_to(english)): p.read_bytes() for p in (english / 'src').rglob('*') if p.is_file()}
    changed = recipe.overlay(raw, english)
    output.mkdir(parents=True)
    for folder in ['en', 'zh-Hant']:
        shutil.copytree(baseline / folder, output / folder)
        for name in [recipe.QUESTION, recipe.HELPER]:
            target = output / folder / name
            if name in raw: assert target.read_bytes() == raw[name]
            target.write_bytes(changed[name])
        metadata_path = output / folder / 'template.json'
        metadata = json.loads(metadata_path.read_text())
        metadata.update(templateId='science-europe-reuse-summary-prototype', version='0.3.47',
            name='Science Europe — reuse summary prototype (not for submission)')
        write(metadata_path, metadata)
    expanded = output / 'expanded'
    expand_template_dir(source_dir=output / 'zh-Hant', output_dir=expanded,
        profile=config['tooling']['profile'], exclude_profile_paths=tuple(config['tooling']['exclude_profile_paths']))
    export_translation_tree(source_dir=expanded, output_dir=output / 'fresh', source_lang='en', target_lang='zh_Hant')
    tree = output / 'translation'
    migration = merge_translation_tree(old_tree_dir=ROOT / 'translation', new_tree_dir=output / 'fresh',
        output_dir=tree, source_lang='en', target_lang='zh_Hant')
    write(output / 'migration.json', asdict(migration))
    words = json.loads((HERE / 'translations.json').read_text())
    for document in tree.rglob('translation.md'):
        source = parse_sentence_text(document_path=document, source_lang='en')
        translated = parse_translation_document(document_path=document, source_lang='en', target_lang='zh_Hant')
        if source in words:
            replace_translation_text(document_path=document, target_lang='zh_Hant', translation_text=words[source])
        else: assert translated.strip(), ('Unexpected untranslated unit', source)
    old = Counter(pair(p.read_text()) for p in (ROOT / 'translation').rglob('translation.md'))
    new = Counter(pair(p.read_text()) for p in tree.rglob('translation.md'))
    removed = Counter(json.loads((HERE / 'removed-translations.json').read_text()).items())
    added = Counter(words.items())
    write(output / 'observed-translation-delta.json', dict(removed=list((old-new).elements()), added=list((new-old).elements())))
    assert old - new == removed and new - old == added, 'Unexpected translation delta'
    assert sum(old.values()) == 773 and sum(new.values()) == 775
    assert not audit_translation_tree(tree_dir=tree, source_dir=expanded)
    sync_translation_tree(tree_dir=tree, source_dir=expanded, output_dir=output / 'translated',
        source_lang='en', target_lang='zh_Hant', template_organization_id=config['translation']['organization_id'],
        template_id='science-europe-reuse-summary-prototype-zhtw', template_name='Science Europe 資料再利用摘要原型（非提交版）',
        template_version='0.3.47', public_readme_path=ROOT / 'PACKAGE_README.md')
    metadata_path = output / 'translated/template.json'
    metadata = json.loads(metadata_path.read_text())
    localize_format_names(metadata, config['translation']['format_names']); write(metadata_path, metadata)
    assert not audit_translated_template_structure(source_dir=expanded, output_dir=output / 'translated')
    result = dict(status='prototype', prototype_only=True, source_integrated=False, release_acceptance=False,
        baseline_source_commit=recipe.BASELINE, tooling_commit=config['tooling']['commit'],
        baseline_packages=BASELINE_HASHES, changed_source_files=[recipe.QUESTION], added_source_files=[recipe.HELPER],
        translation_delta=dict(retained=763, removed=10, added=12, total=775), checks={}, sha256={},
        recipes={str(p.relative_to(root)): sha(p) for root in [english, ROOT]
            for p in (root / 'experiments/reuse-summary').rglob('*') if p.is_file() and '__pycache__' not in p.parts},
        checkouts={name: dict(commit=git(root, 'rev-parse', 'HEAD'), dirty=bool(git(root, 'status', '--porcelain')))
            for name, root in [('english', english), ('chinese', ROOT)]})
    tdk = tooling / '.venv/bin/dsw-tdk'
    for language, folder in [('english', 'en'), ('chinese', 'translated')]:
        for command in [[str(tdk), '--no-config', 'verify', str(output / folder)],
                        [str(tdk), '--no-config', 'package', str(output / folder), '--output', str(output / (language + '.zip'))]]:
            subprocess.run(command, check=True, capture_output=True)
        canonicalize_zip(output / (language + '.zip'), manifest['package_timestamp'])
        with zipfile.ZipFile(output / (language + '.zip')) as package, zipfile.ZipFile(baseline / (language + '.zip')) as prior:
            assets = set(package.namelist()) - {'template/template.json'}
            assert assets == set(prior.namelist()) - {'template/template.json'}
            assert all(package.read(n) == prior.read(n) for n in assets), 'CSS, fonts or Word assets drifted'
            spec = json.loads(package.read('template/template.json'))
        rows = probe.check(english, {f['fileName']: f['content'] for f in spec['files']}, words if language == 'chinese' else None)
        write(output / (language + '-checks.json'), rows)
        result['checks'][language] = len(rows)
        result['sha256'][language + '.zip'] = sha(output / (language + '.zip'))
    write(output / 'manifest.json', result)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for key in ['english', 'tooling', 'baseline', 'output']: p.add_argument('--' + key, type=Path, required=True)
    a = p.parse_args(); result = run(a.english.resolve(), a.tooling.resolve(), a.baseline.resolve(), a.output.resolve())
    print(json.dumps(dict(passed=True, prototype_only=True, checks=result['checks'], translation_delta=result['translation_delta'])))
