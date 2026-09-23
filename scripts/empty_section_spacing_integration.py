"""Exact 0.3.48 paired packages, unchanged translation tree, and scoped branches."""
import argparse
from functools import lru_cache
import hashlib,json,sys
from pathlib import Path
from artifact_utils import sha
from check_budget_grouping_integration import asset_uuid

ROOT=Path(__file__).resolve().parents[1]
CONTRACT=json.loads((ROOT/'docs/empty-section-spacing-delta.json').read_text())
MARKER=b'/* BEGIN empty section spacing v1:'

@lru_cache(maxsize=2)
def receipt(phase):
    root=ROOT/CONTRACT[phase+'_archive']
    assert sha(root/'checksums.json')==CONTRACT[phase+'_seal']
    assert all(sha(root/r['path'])==r['sha256'] for r in json.loads((root/'checksums.json').read_text())['files'])
    return json.loads((root/'build/manifest.json').read_text())

def css():
    value=CONTRACT['css'].encode()
    assert hashlib.sha256(value).hexdigest()==receipt('prototype')['css_sha256']
    return value

def project_sources(current,language):
    from reuse_preparation_integration import needs_projection,project_sources as before_preparation
    if needs_projection(current,language):current=before_preparation(current,language)
    from submission_flow_integration import CONTRACT as old
    delta=css();before=dict(current);value=before['src/layout.css']
    assert value.count(MARKER)==value.count(delta)==1 and value.endswith(delta),'Changed or missing section CSS'
    before['src/layout.css']=value[:-len(delta)]
    assert {n:hashlib.sha256(v).hexdigest() for n,v in before.items()}==old['languages'][language]['prototype']['sources'],'Unreviewed prepared source or asset'
    return before

def integrated_package(language,timestamp):
    from submission_flow_integration import integrated_package as old
    result=old(language,timestamp);result['version']='0.3.48'
    result['id']=result['id'].removesuffix('0.3.47')+'0.3.48'
    for kind in ['files','assets']:
        for item in result[kind]:
            item['uuid']=asset_uuid(result['id'],kind,item['fileName'])
            if kind=='files' and item['fileName']=='src/layout.css':item['content']+=css().decode()
    return result

def project_package(candidate,language,timestamp):
    if candidate['version'] in ['0.3.49', '0.3.50']:
        from reuse_preparation_integration import project_package as before_preparation
        candidate=before_preparation(candidate,language,timestamp)
    from submission_flow_integration import integrated_package as old
    assert candidate==integrated_package(language,timestamp),'Unreviewed identity, source, asset, timestamp, UUID or step'
    return old(language,timestamp)

def check(build,english,preview=False):
    from build import package_timestamp,git
    from submission_flow_integration import sources,check_package
    sys.path.insert(0,str(english/'scripts'))
    from empty_section_spacing_contract import project_source,load,css as english_css
    project_source();assert english_css()==css()
    manifest=json.loads((build/'manifest.json').read_text())
    assert manifest['status']==('preview' if preview else 'candidate')
    version=manifest['source']['version']
    assert version==manifest['translation']['version'] and version in ['0.3.48','0.3.49', '0.3.50']
    if not preview:
        assert all(not state['dirty'] for state in manifest['checkouts'].values())
        assert manifest['source']['commit']==manifest['checkouts']['english']['commit']==git(english,'rev-parse','HEAD')
    assert manifest['package_timestamp']==package_timestamp(english)
    files=list((ROOT/'translation/tree').rglob('translation.md'))
    assert len(files)==manifest['translation_units']==775 and not manifest['untranslated_units']
    assert manifest['translation_tree_sha256']=={str(p.relative_to(ROOT/'translation')):sha(p) for p in files}
    if version in ['0.3.49', '0.3.50']:
        from reuse_preparation_integration import project_translations
        from probe_pdf_budget_translation import pair
        project_translations([pair(p.read_text()) for p in files])
    else:assert manifest['translation_tree_sha256']==receipt('baseline')['translation_tree_sha256']
    packages={};branches={}
    for language,folder in [('english','en'),('chinese','translated')]:
        path=build/(language+'.zip');assert sha(path)==manifest['sha256'][path.name]
        packages[language]=check_package(path,build/folder,language,manifest['package_timestamp'])
        after=sources(build/folder)
        if version=='0.3.50':
            from word_empty_section_integration import project_sources as before_word
            after=before_word(after,language)
        if version in ['0.3.49', '0.3.50']:
            from reuse_preparation_integration import project_sources as before_preparation
            after=before_preparation(after,language)
        before=project_sources(after,language)
        branches[language]=len(load('probe').check(english,before,after));assert branches[language]==396
    return dict(passed=True,source_integrated=True,release_acceptance=False,native_integrated_render_checked=False,
        baseline_version='0.3.47',version=version,comparison_version='0.3.48',historical_scope=version in ['0.3.49', '0.3.50'],
        translation_units=775,translation_files_unchanged=version=='0.3.48',
        css_sha256=hashlib.sha256(css()).hexdigest(),packages=packages,branch_checks=branches)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,required=True);p.add_argument('--english',type=Path,required=True);p.add_argument('--preview',action='store_true')
    a=p.parse_args();result=check(a.build.resolve(),a.english.resolve(),a.preview)
    with (a.build/'empty-section-integration.json').open('x') as f:f.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
