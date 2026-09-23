"""Build a Word-only prototype through the existing locked EN -> ZH pipeline."""
import argparse, copy, importlib.util, json, shutil, subprocess, sys, uuid, zipfile
from collections import Counter
from dataclasses import asdict
from pathlib import Path
import yaml
import dsw_document_template_tool
from dsw_document_template_tool.template_transform import expand_template_dir
from dsw_document_template_tool.translation_tree import (export_translation_tree,merge_translation_tree,
    sync_translation_tree,audit_translation_tree,audit_translated_template_structure)

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from artifact_utils import sha,canonicalize_zip
from build import git,localize_format_names
from probe_pdf_budget_translation import pair
from submission_flow_integration import check_package

BASELINE_HASHES={'english.zip':'9912fb9454190970614c4b260a305695dfe9bcb60c85480c4e9ed03fff863103',
    'chinese.zip':'1896530e3d340f1b0894ddedab90fc6d8697def24a68f9be9264bd468ffafec5'}
IDENTITY='science-europe-word-empty-sections-prototype'
VERSION='0.3.49'
NAMES={'english':'Science Europe — Word empty sections prototype (not for submission)',
    'chinese':'Science Europe Word 空節間距原型（非提交版）'}
CHANGED={'src/word/question-spacing.lua','src/word/question-spacing.xml'}

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def write(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def sources(root):return {str(p.relative_to(root)):p.read_bytes() for p in (root/'src').rglob('*') if p.is_file()}
def compare_package(before,after,language):
    restored=copy.deepcopy(after)
    identity=IDENTITY+('-zhtw' if language=='chinese' else '')
    assert after['templateId']==identity and after['version']==VERSION and after['name']==NAMES[language]
    assert after['id']==before['organizationId']+':'+identity+':'+VERSION
    for key in ['id','templateId','version','name']:restored[key]=before[key]
    for kind in ['files','assets']:
        old={v['fileName']:v for v in before[kind]}
        assert len(old)==len(restored[kind]) and set(old)=={v['fileName'] for v in restored[kind]}
        for item in restored[kind]:
            assert item['uuid']==str(uuid.uuid5(uuid.NAMESPACE_URL,f"dsw-template/{after['id']}/{kind}/{item['fileName']}"))
            item['uuid']=old[item['fileName']]['uuid']
    assert restored==before,'Unreviewed source, asset metadata, format identity, timestamp or conversion-step change'

def run(english,tooling,baseline,output):
    assert not output.exists(),'Never overwrite earlier evidence'
    config=yaml.safe_load((ROOT/'pipeline.yml').read_text());lock=json.loads((HERE/'lock.json').read_text())
    assert config['source']['commit']==lock['production_source_commit']
    assert config['source']['version']==config['translation']['version']==VERSION
    for name,root in [('english',english),('chinese',ROOT),('tooling',tooling)]:
        assert not git(root,'status','--porcelain'),(name,'dirty checkout')
    assert git(english,'rev-parse','HEAD')==lock['english_recipe_commit']
    assert git(tooling,'rev-parse','HEAD')==lock['tooling_commit']==config['tooling']['commit']
    assert Path(dsw_document_template_tool.__file__).resolve().is_relative_to(tooling/'src')
    archive=ROOT/lock['baseline_review']
    assert sha(archive/'checksums.json')==lock['baseline_review_seal']
    assert all(sha(archive/r['path'])==r['sha256'] for r in json.loads((archive/'checksums.json').read_text())['files'])
    prior=json.loads((baseline/'manifest.json').read_text())
    assert prior['status']=='candidate' and prior['source']==config['source'] and prior['translation']==config['translation']
    assert all(not v['dirty'] for v in prior['checkouts'].values()) and not prior['untranslated_units']
    original_tree={str(p.relative_to(ROOT/'translation')):sha(p) for p in (ROOT/'translation').rglob('translation.md')}
    assert original_tree==prior['translation_tree_sha256'] and len(original_tree)==775
    for language,folder in [('english','en'),('chinese','translated')]:
        path=baseline/(language+'.zip');assert sha(path)==BASELINE_HASHES[path.name]==prior['sha256'][path.name]
        check_package(path,baseline/folder,language,prior['package_timestamp'])
    recipe=load(english/'experiments/word-empty-section-spacing/recipe.py','word_section_recipe')
    assert recipe.BASELINE==lock['production_source_commit'] and recipe.CHANGED==CHANGED
    changed=recipe.overlay(sources(english),english)
    output.mkdir(parents=True)
    for folder in ['en','zh-Hant']:
        shutil.copytree(baseline/folder,output/folder)
        for name in CHANGED:
            assert (output/folder/name).read_bytes()==recipe.baseline_sources(english)[name]
            (output/folder/name).write_bytes(changed[name])
        path=output/folder/'template.json';metadata=json.loads(path.read_text())
        metadata.update(templateId=IDENTITY,version=VERSION,name=NAMES['english']);write(path,metadata)
    expanded=output/'expanded'
    expand_template_dir(source_dir=output/'zh-Hant',output_dir=expanded,profile=config['tooling']['profile'],
        exclude_profile_paths=tuple(config['tooling']['exclude_profile_paths']))
    export_translation_tree(source_dir=expanded,output_dir=output/'fresh',source_lang='en',target_lang='zh_Hant')
    tree=output/'translation'
    migrated=merge_translation_tree(old_tree_dir=ROOT/'translation',new_tree_dir=output/'fresh',
        output_dir=tree,source_lang='en',target_lang='zh_Hant');write(output/'migration.json',asdict(migrated))
    old_pairs=Counter(pair(p.read_text()) for p in (ROOT/'translation').rglob('translation.md'))
    new_pairs=Counter(pair(p.read_text()) for p in tree.rglob('translation.md'))
    assert old_pairs==new_pairs and new_pairs.total()==775,'Any wording change is out of scope'
    assert original_tree=={str(p.relative_to(tree)):sha(p) for p in tree.rglob('translation.md')},'Translation file bytes changed'
    assert not audit_translation_tree(tree_dir=tree,source_dir=expanded)
    sync_translation_tree(tree_dir=tree,source_dir=expanded,output_dir=output/'translated',source_lang='en',target_lang='zh_Hant',
        template_organization_id=config['translation']['organization_id'],template_id=IDENTITY+'-zhtw',
        template_name=NAMES['chinese'],template_version=VERSION,public_readme_path=ROOT/'PACKAGE_README.md')
    path=output/'translated/template.json';metadata=json.loads(path.read_text())
    localize_format_names(metadata,config['translation']['format_names']);write(path,metadata)
    assert not audit_translated_template_structure(source_dir=expanded,output_dir=output/'translated')
    result=dict(status='prototype',prototype_only=True,source_integrated=False,release_acceptance=False,
        experiment_lock=lock,baseline_packages=BASELINE_HASHES,changed_assets=sorted(CHANGED),
        translation_units=775,translation_pairs_and_file_bytes_unchanged=True,sha256={},
        checkouts={n:dict(commit=git(r,'rev-parse','HEAD'),dirty=False) for n,r in [('english',english),('chinese',ROOT),('tooling',tooling)]})
    tdk=tooling/'.venv/bin/dsw-tdk'
    for language,folder in [('english','en'),('chinese','translated')]:
        actual=sources(output/folder);before=sources(baseline/folder)
        assert actual=={n:changed[n] if n in CHANGED else v for n,v in before.items()}
        path=output/(language+'.zip')
        for command in [[str(tdk),'--no-config','verify',str(output/folder)],
                        [str(tdk),'--no-config','package',str(output/folder),'--output',str(path)]]:
            subprocess.run(command,check=True,capture_output=True)
        canonicalize_zip(path,prior['package_timestamp'])
        with zipfile.ZipFile(path) as current,zipfile.ZipFile(baseline/path.name) as previous:
            assert set(current.namelist())==set(previous.namelist())
            for name in previous.namelist():
                if name=='template/template.json':continue
                relative=name.removeprefix('template/assets/')
                assert current.read(name)==(changed[relative] if relative in CHANGED else previous.read(name)),name
            compare_package(json.loads(previous.read('template/template.json')),json.loads(current.read('template/template.json')),language)
        result['sha256'][path.name]=sha(path)
    write(output/'manifest.json',result);return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['english','tooling','baseline','output']:parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();report=run(**{k:v.resolve() for k,v in vars(args).items()})
    print(json.dumps(dict(passed=True,prototype_only=True,translations_unchanged=775,sha256=report['sha256'])))
