"""Rebuild the bounded print-margin prototype through the unchanged translator."""
import argparse,copy,hashlib,importlib.util,json,shutil,subprocess,sys,uuid,zipfile
from collections import Counter
from dataclasses import asdict
from pathlib import Path
import yaml
import dsw_document_template_tool
from dsw_document_template_tool.template_transform import expand_template_dir
from dsw_document_template_tool.translation_tree import (export_translation_tree,merge_translation_tree,
    sync_translation_tree,audit_translation_tree,audit_translated_template_structure)

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from artifact_utils import sha,canonicalize_zip
from build import git,localize_format_names
from probe_pdf_budget_translation import pair
from submission_flow_integration import check_package

BASELINE_HASHES={'english.zip':'f210dcfce3643b83b07ce1bf2b3d9ac5efff11cb7068471e04439c9fe267c39d',
    'chinese.zip':'86a2e6f2ee5f5c1e3abf714f0061eb29f9c460ff3ee55f15dd0ebe849ec33248'}

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module);return module
def write(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def sources(root):return {str(p.relative_to(root)):p.read_bytes() for p in (root/'src').rglob('*') if p.is_file()}
def spec(path):
    with zipfile.ZipFile(path) as z:return json.loads(z.read('template/template.json'))

def compare_package(before,after,css):
    """Only explicit prototype identity and one CSS suffix may differ."""
    restored=copy.deepcopy(after)
    suffix='-zhtw' if before['templateId'].endswith('-zhtw') else ''
    assert after['templateId']=='science-europe-empty-section-prototype'+suffix
    assert after['version']=='0.3.48'
    assert after['id']==before['organizationId']+':'+after['templateId']+':0.3.48'
    assert after['name']==('Science Europe 空節間距原型（非提交版）' if suffix else 'Science Europe — empty section spacing prototype (not for submission)')
    for key in ['name','id','templateId','version']:restored[key]=before[key]
    for kind in ['files','assets']:
        old={v['fileName']:v for v in before[kind]}
        assert {v['fileName'] for v in restored[kind]}==set(old)
        assert len(restored[kind])==len(old)
        for item in restored[kind]:
            assert item['uuid']==str(uuid.uuid5(uuid.NAMESPACE_URL,f"dsw-template/{after['id']}/{kind}/{item['fileName']}"))
            item['uuid']=old[item['fileName']]['uuid']
            if kind=='files' and item['fileName']=='src/layout.css':
                assert item['content']==old[item['fileName']]['content']+css.decode()
                item['content']=old[item['fileName']]['content']
    assert restored==before,'Unreviewed metadata, file, asset, format or timestamp changed'

def run(english,tooling,baseline,output):
    assert not output.exists(),'Never overwrite an earlier trial'
    config=yaml.safe_load((ROOT/'pipeline.yml').read_text())
    lock=json.loads((Path(__file__).parent/'lock.json').read_text())
    assert lock['prototype_only'] and config['source']['commit']==lock['production_source_commit']
    assert git(english,'rev-parse','HEAD')==lock['english_recipe_commit'] and not git(english,'status','--porcelain')
    assert not git(ROOT,'status','--porcelain'),'Commit the experiment before producing frozen artifacts'
    assert lock['tooling_commit']==config['tooling']['commit']
    archive=ROOT/lock['baseline_review'];assert sha(archive/'checksums.json')==lock['baseline_review_seal']
    assert all(sha(archive/r['path'])==r['sha256'] for r in json.loads((archive/'checksums.json').read_text())['files'])
    assert config['source']['version']==config['translation']['version']=='0.3.47'
    assert git(tooling,'rev-parse','HEAD')==config['tooling']['commit'] and not git(tooling,'status','--porcelain')
    assert Path(dsw_document_template_tool.__file__).resolve().is_relative_to(tooling/'src')
    prior=json.loads((baseline/'manifest.json').read_text())
    assert prior['status']=='candidate' and not prior['untranslated_units']
    assert all(not r['dirty'] for r in prior['checkouts'].values())
    old_pairs=Counter(pair(p.read_text()) for p in (ROOT/'translation/tree').rglob('translation.md'))
    assert old_pairs.total()==775
    assert {str(p.relative_to(ROOT/'translation')):sha(p) for p in (ROOT/'translation/tree').rglob('translation.md')}==prior['translation_tree_sha256']
    recipe=load(english/'experiments/empty-section-spacing/recipe.py','section_builder_recipe')
    probe=load(english/'experiments/empty-section-spacing/probe.py','section_builder_probe')
    assert config['source']['commit']==recipe.BASELINE
    raw=sources(english);recipe.overlay(raw,english)
    for language,folder in [('english','en'),('chinese','translated')]:
        path=baseline/(language+'.zip');assert sha(path)==BASELINE_HASHES[path.name]==prior['sha256'][path.name]
        check_package(path,baseline/folder,language,prior['package_timestamp'])
    output.mkdir(parents=True)
    for folder in ['en','zh-Hant']:
        shutil.copytree(baseline/folder,output/folder)
        css=output/folder/'src/layout.css';css.write_bytes(css.read_bytes()+recipe.CSS)
        path=output/folder/'template.json';metadata=json.loads(path.read_text())
        metadata.update(templateId='science-europe-empty-section-prototype',version='0.3.48',
            name='Science Europe — empty section spacing prototype (not for submission)')
        write(path,metadata)
    expanded=output/'expanded'
    expand_template_dir(source_dir=output/'zh-Hant',output_dir=expanded,
        profile=config['tooling']['profile'],exclude_profile_paths=tuple(config['tooling']['exclude_profile_paths']))
    export_translation_tree(source_dir=expanded,output_dir=output/'fresh',source_lang='en',target_lang='zh_Hant')
    migration=merge_translation_tree(old_tree_dir=ROOT/'translation',new_tree_dir=output/'fresh',output_dir=output/'translation',source_lang='en',target_lang='zh_Hant')
    write(output/'migration.json',asdict(migration))
    new_pairs=Counter(pair(p.read_text()) for p in (output/'translation').rglob('translation.md'))
    assert new_pairs==old_pairs,'Translation changes are out of scope'
    assert not audit_translation_tree(tree_dir=output/'translation',source_dir=expanded)
    sync_translation_tree(tree_dir=output/'translation',source_dir=expanded,output_dir=output/'translated',
        source_lang='en',target_lang='zh_Hant',template_organization_id=config['translation']['organization_id'],
        template_id='science-europe-empty-section-prototype-zhtw',template_name='Science Europe 空節間距原型（非提交版）',
        template_version='0.3.48',public_readme_path=ROOT/'PACKAGE_README.md')
    path=output/'translated/template.json';metadata=json.loads(path.read_text())
    localize_format_names(metadata,config['translation']['format_names']);write(path,metadata)
    assert not audit_translated_template_structure(source_dir=expanded,output_dir=output/'translated')
    result=dict(status='prototype',source_integrated=False,release_acceptance=False,baseline_packages=BASELINE_HASHES,
        source_changes=['src/layout.css'],translation_units=775,translation_pairs_unchanged=True,
        format_steps_unchanged=True,checks={},sha256={},css_sha256=hashlib.sha256(recipe.CSS).hexdigest(),
        experiment_lock=lock,
        checkouts={name:dict(commit=git(root,'rev-parse','HEAD'),dirty=bool(git(root,'status','--porcelain'))) for name,root in [('english',english),('chinese',ROOT),('tooling',tooling)]},
        recipes={label:{str(p.relative_to(root)):sha(p) for p in (root/'experiments/empty-section-spacing').rglob('*') if p.is_file() and '__pycache__' not in p.parts} for label,root in [('english',english),('chinese',ROOT)]})
    tdk=tooling/'.venv/bin/dsw-tdk'
    for language,folder in [('english','en'),('chinese','translated')]:
        before,after=sources(baseline/folder),sources(output/folder);recipe.project_prepared(before,after)
        path=output/(language+'.zip')
        for command in [[str(tdk),'--no-config','verify',str(output/folder)],
                        [str(tdk),'--no-config','package',str(output/folder),'--output',str(path)]]:
            subprocess.run(command,check=True,capture_output=True)
        canonicalize_zip(path,prior['package_timestamp'])
        compare_package(spec(baseline/path.name),spec(path),recipe.CSS)
        with zipfile.ZipFile(path) as new,zipfile.ZipFile(baseline/path.name) as old:
            assert set(new.namelist())==set(old.namelist())
            assert all(new.read(n)==old.read(n) for n in old.namelist() if n!='template/template.json')
        rows=probe.check(english,before,after);write(output/(language+'-checks.json'),rows)
        result['checks'][language]=len(rows);result['sha256'][path.name]=sha(path)
    write(output/'manifest.json',result);return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ['english','tooling','baseline','output']:parser.add_argument('--'+key,type=Path,required=True)
    a=parser.parse_args();result=run(a.english.resolve(),a.tooling.resolve(),a.baseline.resolve(),a.output.resolve())
    print(json.dumps(dict(passed=True,checks=result['checks'],translations_unchanged=775)))
