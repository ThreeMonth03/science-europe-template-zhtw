"""Renderer-neutral Q3 policy prose through the locked EN -> ZH pipeline."""
import argparse
import copy
from dataclasses import asdict
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import uuid
import zipfile
import yaml
import dsw_document_template_tool
from dsw_document_template_tool.template_transform import expand_template_dir
from dsw_document_template_tool.translation_tree import (export_translation_tree, merge_translation_tree,
    sync_translation_tree, audit_translation_tree, audit_translated_template_structure)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from artifact_utils import sha, canonicalize_zip
from build import git, localize_format_names
from submission_flow_integration import check_package

BASELINE_HASHES = {
    'english.zip': '4f26c8cf53bc8bb4870ddb0aac5ac494948508e67bf295e34179458fde8c4a36',
    'chinese.zip': '99648e6f99ae8d8467dad177acc87cb741f311a2212919d6a9ef94cda6f73497'}
QUESTION = 'src/questions/03-docs-metadata.html.j2'
HELPER = 'src/metadata-prose.html.j2'
VERSION = '0.3.50'
IDENTITY = 'science-europe-q3-shared-prose-prototype'
NAMES = {'english': 'Science Europe — Q3 shared prose prototype (not for submission)',
         'chinese': 'Science Europe 第 3 題共用段落原型（非提交版）'}


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def sources(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in (root / 'src').rglob('*') if p.is_file()}


def translation_unchanged(old, new):
    inventories = [{str(p.relative_to(root)): sha(p) for p in root.rglob('translation.md')} for root in [old, new]]
    assert len(inventories[0]) == 775 and inventories[0] == inventories[1], 'Translation text or unit metadata changed'
    return dict(total=775, byte_identical=775, changed=0)


def compare_package(before, after, changed, language):
    restored = copy.deepcopy(after)
    template_id = IDENTITY + ('-zhtw' if language == 'chinese' else '')
    assert after['templateId'] == template_id and after['version'] == VERSION
    assert after['id'] == before['organizationId'] + ':' + template_id + ':' + VERSION
    assert after['name'] == NAMES[language]
    for key in ['id', 'templateId', 'version', 'name']: restored[key] = before[key]
    for kind in ['files', 'assets']:
        old = {v['fileName']: v for v in before[kind]}
        added = {HELPER} if kind == 'files' else set()
        assert HELPER not in old and len(restored[kind]) == len(old) + len(added)
        assert {v['fileName'] for v in restored[kind]} == set(old) | added
        for item in list(restored[kind]):
            assert item['uuid'] == str(uuid.uuid5(uuid.NAMESPACE_URL, f"dsw-template/{after['id']}/{kind}/{item['fileName']}"))
            if item['fileName'] in added:
                assert item['content'] == changed[HELPER].decode()
                assert set(item) == {'uuid', 'fileName', 'content'}
                restored[kind].remove(item)
                continue
            item['uuid'] = old[item['fileName']]['uuid']
            if kind == 'files' and item['fileName'] == QUESTION:
                assert item['content'] == changed[QUESTION].decode()
                item['content'] = old[item['fileName']]['content']
    assert restored == before, 'Format steps, fonts, CSS, Word assets or unrelated source changed'


def original_spec(path):
    with zipfile.ZipFile(path) as package: return json.loads(package.read('template/template.json'))


def run(english, tooling, baseline, output):
    assert not output.exists(), 'Never overwrite an earlier trial'
    config = yaml.safe_load((ROOT / 'pipeline.yml').read_text())
    lock = json.loads((HERE / 'lock.json').read_text())
    assert lock['prototype_only'] and config['source']['commit'] == lock['production_source_commit']
    assert git(english, 'rev-parse', 'HEAD') == lock['english_recipe_commit']
    assert not git(english, 'status', '--porcelain') and not git(ROOT, 'status', '--porcelain')
    assert git(tooling, 'rev-parse', 'HEAD') == lock['tooling_commit'] == config['tooling']['commit']
    assert not git(tooling, 'status', '--porcelain')
    assert Path(dsw_document_template_tool.__file__).resolve().is_relative_to(tooling / 'src')
    assert config['source']['version'] == config['translation']['version'] == VERSION
    archive = ROOT / lock['baseline_review']
    assert sha(archive / 'checksums.json') == lock['baseline_review_seal']
    assert all(sha(archive / r['path']) == r['sha256'] for r in json.loads((archive / 'checksums.json').read_text())['files'])
    prior = json.loads((baseline / 'manifest.json').read_text())
    assert prior['source'] == config['source'] and prior['translation'] == config['translation']
    assert prior['status'] == 'candidate' and not prior['untranslated_units']
    assert all(not r['dirty'] for r in prior['checkouts'].values())
    assert prior['translation_tree_sha256'] == {str(p.relative_to(ROOT / 'translation')): sha(p) for p in (ROOT / 'translation').rglob('translation.md')}
    for language, folder in [('english', 'en'), ('chinese', 'translated')]:
        path = baseline / (language + '.zip')
        assert sha(path) == BASELINE_HASHES[path.name] == prior['sha256'][path.name]
        check_package(path, baseline / folder, language, prior['package_timestamp'])
    recipe = load(english / 'experiments/q3-shared-policy-prose/recipe.py', 'q3_shared_recipe')
    probe = load(english / 'experiments/q3-shared-policy-prose/probe.py', 'q3_shared_probe')
    assert recipe.BASELINE == lock['production_source_commit']
    changed = recipe.overlay(sources(english), english)
    output.mkdir(parents=True)
    for folder in ['en', 'zh-Hant']:
        shutil.copytree(baseline / folder, output / folder)
        assert (output / folder / QUESTION).read_bytes() == recipe.baseline_sources(english)[QUESTION]
        (output / folder / QUESTION).write_bytes(changed[QUESTION])
        assert not (output / folder / HELPER).exists()
        (output / folder / HELPER).write_bytes(changed[HELPER])
        path = output / folder / 'template.json'; metadata = json.loads(path.read_text())
        metadata.update(templateId=IDENTITY, version=VERSION, name=NAMES['english']); write(path, metadata)
    expanded, tree = output / 'expanded', output / 'translation'
    expand_template_dir(source_dir=output / 'zh-Hant', output_dir=expanded,
        profile=config['tooling']['profile'], exclude_profile_paths=tuple(config['tooling']['exclude_profile_paths']))
    export_translation_tree(source_dir=expanded, output_dir=output / 'fresh', source_lang='en', target_lang='zh_Hant')
    migration = merge_translation_tree(old_tree_dir=ROOT / 'translation', new_tree_dir=output / 'fresh',
        output_dir=tree, source_lang='en', target_lang='zh_Hant')
    write(output / 'migration.json', asdict(migration))
    delta = translation_unchanged(ROOT / 'translation', tree)
    assert not audit_translation_tree(tree_dir=tree, source_dir=expanded)
    sync_translation_tree(tree_dir=tree, source_dir=expanded, output_dir=output / 'translated',
        source_lang='en', target_lang='zh_Hant', template_organization_id=config['translation']['organization_id'],
        template_id=IDENTITY + '-zhtw', template_name=NAMES['chinese'], template_version=VERSION,
        public_readme_path=ROOT / 'PACKAGE_README.md')
    path = output / 'translated/template.json'; metadata = json.loads(path.read_text())
    localize_format_names(metadata, config['translation']['format_names']); write(path, metadata)
    assert not audit_translated_template_structure(source_dir=expanded, output_dir=output / 'translated')
    result = dict(status='prototype', prototype_only=True, source_integrated=False, release_acceptance=False,
        experiment_lock=lock, baseline_packages=BASELINE_HASHES, changed_source_files=[QUESTION], added_source_files=[HELPER],
        translation_delta=delta, checks={}, sha256={},
        checkouts={name: dict(commit=git(root, 'rev-parse', 'HEAD'), dirty=bool(git(root, 'status', '--porcelain')))
                   for name, root in [('english', english), ('chinese', ROOT), ('tooling', tooling)]})
    tdk = tooling / '.venv/bin/dsw-tdk'
    for language, folder in [('english', 'en'), ('chinese', 'translated')]:
        path = output / (language + '.zip')
        for command in [[str(tdk), '--no-config', 'verify', str(output / folder)],
                        [str(tdk), '--no-config', 'package', str(output / folder), '--output', str(path)]]:
            subprocess.run(command, check=True, capture_output=True)
        canonicalize_zip(path, prior['package_timestamp'])
        with zipfile.ZipFile(path) as package, zipfile.ZipFile(baseline / path.name) as original:
            assert set(package.namelist()) == set(original.namelist())
            assert all(package.read(n) == original.read(n) for n in original.namelist() if n != 'template/template.json')
            spec = json.loads(package.read('template/template.json'))
            compare_package(json.loads(original.read('template/template.json')), spec,
                            {n:(output / folder / n).read_bytes() for n in [QUESTION, HELPER]}, language)
        rows = probe.check(english, {f['fileName']: f['content'] for f in original_spec(baseline / path.name)['files']},
            {f['fileName']: f['content'] for f in spec['files']}, language)
        write(output / (language + '-checks.json'), rows)
        result['checks'][language] = len(rows); result['sha256'][path.name] = sha(path)
    write(output / 'manifest.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ['english', 'tooling', 'baseline', 'output']: parser.add_argument('--' + key, type=Path, required=True)
    args = parser.parse_args()
    result = run(**{key: value.resolve() for key, value in vars(args).items()})
    print(json.dumps(dict(passed=True, checks=result['checks'], translation_delta=result['translation_delta'])))
