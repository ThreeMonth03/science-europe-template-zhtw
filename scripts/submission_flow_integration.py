"""Exact 0.3.47 packages and actual branches, then test-only 0.3.46 views."""
import argparse
from functools import lru_cache
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import zipfile
from artifact_utils import sha
from check_budget_grouping_integration import asset_uuid
from current_source_repairs import is_q3_version

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads((ROOT/'docs/submission-flow-prepared-delta.json').read_text())
ADDED = {'src/reuse-summary.html.j2','src/question-spacing.html.j2',
         'src/word/question-spacing.lua','src/word/question-spacing.xml'}

@lru_cache(maxsize=2)
def sealed(name):
    directory=ROOT/name;assert sha(directory/'checksums.json')==CONTRACT['seals'][name]
    inventory=json.loads((directory/'checksums.json').read_text())
    rows=inventory['files'] if 'files' in inventory else [dict(path=n,sha256=v) for n,v in inventory.items()]
    assert all(sha(directory/r['path'])==r['sha256'] for r in rows)
    return directory

def package(language,prototype=False):
    phase='prototype' if prototype else 'baseline';sealed(CONTRACT[phase+'_archive'])
    spec=CONTRACT['languages'][language][phase];path=ROOT/spec['fixture']
    assert sha(path)==spec['fixture_sha256']
    return json.loads(path.read_text())

def sources(root):return {str(p.relative_to(root)):p.read_bytes() for p in (root/'src').rglob('*') if p.is_file()}

def project_sources(current,language):
    from empty_section_spacing_integration import MARKER,project_sources as before_sections
    if MARKER in current.get('src/layout.css',b''):current=before_sections(current,language)
    expected=CONTRACT['languages'][language]
    hashes=lambda data:{n:hashlib.sha256(v).hexdigest() for n,v in data.items()}
    assert hashes(current)==expected['prototype']['sources'],'Unreviewed 0.3.47 prepared source or asset'
    assert set(expected['added'])==ADDED
    previous={n:v for n,v in current.items() if n not in ADDED}
    for item in package(language)['files']:previous[item['fileName']]=item['content'].encode()
    assert hashes(previous)==expected['baseline']['sources'],'Every 0.3.46 byte must be restored'
    return previous

def integrated_package(language,timestamp):
    result=package(language,True);old=package(language)
    for key in ['name','templateId']:result[key]=old[key]
    result['id']=old['id'].removesuffix('0.3.46')+'0.3.47';result['version']='0.3.47'
    result['createdAt']=result['updatedAt']=timestamp
    for kind in ['files','assets']:
        for item in result[kind]:item['uuid']=asset_uuid(result['id'],kind,item['fileName'])
    return result

def project_package(candidate,language,timestamp):
    if candidate['version'] in ['0.3.48','0.3.49', '0.3.50'] or is_q3_version(candidate['version']):
        from empty_section_spacing_integration import project_package as before_sections
        candidate=before_sections(candidate,language,timestamp)
    assert candidate==integrated_package(language,timestamp),'Unreviewed content, identity, UUID or conversion step'
    return package(language)

def check_package(path,prepared,language,timestamp):
    with zipfile.ZipFile(path) as z:
        version=json.loads(z.read('template/template.json'))['version']
    if version == '0.3.50' or is_q3_version(version):
        from word_empty_section_integration import check_package as check_current
        return check_current(path,prepared,language,timestamp)
    current=sources(prepared);project_sources(current,language)
    members=CONTRACT['languages'][language]['prototype']['assets']
    with zipfile.ZipFile(path) as z:
        assert len(z.namelist())==len(members)+1 and set(z.namelist())==set(members)|{'template/template.json'}
        for name,digest in members.items():
            assert hashlib.sha256(z.read(name)).hexdigest()==digest
            assert z.read(name)==current[name.removeprefix('template/assets/')]
        spec=json.loads(z.read('template/template.json'))
    project_package(spec,language,timestamp)
    for item in spec['files']:assert item['content'].encode()==current[item['fileName']]
    return dict(package_sha256=sha(path),prototype_content_and_assets_identical=True,
        deterministic_identity_verified=True,prepared_source_verified=True)

def historical_zip(build,destination,language):
    """Only validated current packages may become exact old ZIPs for legacy tests."""
    manifest=json.loads((build/'manifest.json').read_text())
    folder='en' if language=='english' else 'translated'
    check_package(build/(language+'.zip'),build/folder,language,manifest['package_timestamp'])
    previous=package(language);members=CONTRACT['languages'][language]['baseline']['assets']
    with zipfile.ZipFile(build/(language+'.zip')) as current,zipfile.ZipFile(destination,'x') as old:
        old.writestr('template/template.json',json.dumps(previous,ensure_ascii=False).encode())
        for name,digest in members.items():
            data=current.read(name);assert hashlib.sha256(data).hexdigest()==digest
            old.writestr(name,data)

def check(build,english,preview=False):
    from build import package_timestamp
    from probe_personal_data_translation import verify_submission_translation_chain
    from probe_pdf_budget_translation import pair
    sys.path.insert(0,str(english/'scripts'))
    from submission_flow_contract import project_source
    project_source()
    manifest=json.loads((build/'manifest.json').read_text())
    assert manifest['status']==('preview' if preview else 'candidate')
    version=manifest['source']['version']
    assert version==manifest['translation']['version'] and (version in ['0.3.47','0.3.48','0.3.49', '0.3.50'] or is_q3_version(version))
    if not preview:
        assert all(not v['dirty'] for v in manifest['checkouts'].values())
        head=subprocess.check_output(['git','-C',str(english),'rev-parse','HEAD'],text=True).strip()
        assert manifest['source']['commit']==manifest['checkouts']['english']['commit']==head
    assert manifest['package_timestamp']==package_timestamp(english)
    files=list((ROOT/'translation/tree').rglob('translation.md'));pairs=[pair(p.read_text()) for p in files]
    _,chain=verify_submission_translation_chain(pairs)
    assert manifest['translation_units']==len(files)==chain['current_language_polish']['current_units'] and not manifest['untranslated_units']
    assert manifest['translation_tree_sha256']=={str(p.relative_to(ROOT/'translation')):sha(p) for p in files}
    def load(name,path):
        spec=importlib.util.spec_from_file_location(name,english/path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
    q1=load('integrated_q1','experiments/reuse-summary/probe.py')
    spacing=load('integrated_spacing','experiments/empty-question-spacing/probe.py')
    results={};branches={}
    for language,folder in [('english','en'),('chinese','translated')]:
        path=build/(language+'.zip');assert sha(path)==manifest['sha256'][path.name]
        results[language]=check_package(path,build/folder,language,manifest['package_timestamp'])
        current=sources(build/folder)
        # Reproduce the Q1-only parent of the empty-question experiment.
        before=dict(current);before['src/content.html.j2']=next(f['content'].encode() for f in package(language)['files'] if f['fileName']=='src/content.html.j2')
        branches[language]=dict(q1=len(q1.check(english,current,dict(pairs) if language=='chinese' else None)),
            empty_questions=len(spacing.check(english,before,current)))
        assert branches[language]==dict(q1=1844,empty_questions=480)
    return dict(passed=True,source_integrated=True,release_acceptance=False,native_integrated_render_checked=False,
        historical_scope=version in ['0.3.48','0.3.49', '0.3.50'] or is_q3_version(version),comparison_version='0.3.47',
        translation_delta=chain['submission_flow'],packages=results,branch_checks=branches)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build',type=Path,required=True);p.add_argument('--english',type=Path,required=True);p.add_argument('--preview',action='store_true')
    a=p.parse_args();result=check(a.build.resolve(),a.english.resolve(),a.preview)
    with (a.build/'submission-flow-integration.json').open('x') as f:f.write(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False))
