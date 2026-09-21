"""Ensure the two shared Word helpers survive the existing translation pipeline."""
import argparse
import json
from pathlib import Path
import shutil
from table_recipe import HERE, LUA, XML, sha
from dsw_document_template_tool.template_transform import expand_template_dir
from dsw_document_template_tool.translation_tree import export_translation_tree, sync_translation_tree
from dsw_document_template_tool._translation_tree.manifest import load_tree_manifest


def run(english, output, storage='jinja'):
    assert not output.exists(); source = output / 'source'; (source / 'src/word').mkdir(parents=True)
    shutil.copy2(english / 'template.json', source / 'template.json')
    assert storage in ['jinja', 'asset']
    files = {LUA: LUA, XML: XML if storage == 'jinja' else XML.removesuffix('.j2')}
    for original, relative in files.items(): shutil.copy2(HERE / Path(original).name, source / relative)
    expanded = output / 'expanded'; tree = output / 'tree'; translated = output / 'translated'
    expand_template_dir(source_dir=source, output_dir=expanded, profile='science-europe')
    export_translation_tree(source_dir=expanded, output_dir=tree, source_lang='en', target_lang='zh_Hant')
    units = load_tree_manifest(tree)['units']
    if units:
        result = dict(passed=False, minimal_shared_files_probe=True, full_source_integration=False,
                      storage=storage, integration_blocked=True, issue='machine-xml-misclassified-as-translatable-prose',
                      translation_units=len(units), source_files=sorted({u['source_file'] for u in units}),
                      source_sha256={r: sha((source / r).read_bytes()) for r in files.values()},
                      expanded_sha256={r: sha((expanded / r).read_bytes()) for r in files.values()},
                      checker_sha256=sha(Path(__file__).read_bytes()))
        (output / 'report.json').write_text(json.dumps(result, indent=2) + '\n')
        return result
    sync_translation_tree(tree_dir=tree, source_dir=expanded, output_dir=translated, source_lang='en', target_lang='zh_Hant')
    hashes = {}
    for relative in files.values():
        raw = (source / relative).read_bytes()
        assert raw == (expanded / relative).read_bytes() == (translated / relative).read_bytes(), relative
        hashes[relative] = sha(raw)
    result = dict(passed=True, minimal_shared_files_probe=True, full_source_integration=False, storage=storage,
                  native_asset_pipeline_checked=False,
                  translation_units=0, unchanged_file_sha256=hashes, checker_sha256=sha(Path(__file__).read_bytes()))
    (output / 'report.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--english', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    p.add_argument('--storage', choices=['jinja', 'asset'], default='jinja')
    a = p.parse_args(); result = run(a.english, a.output, a.storage); print(json.dumps(result))
    raise SystemExit(0 if result['passed'] else 1)
