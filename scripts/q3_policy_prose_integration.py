"""Exact paired 0.3.51 Q3 packages before reversible historical projections."""
import argparse
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import sys
import zipfile
from artifact_utils import sha
from check_budget_grouping_integration import asset_uuid

ROOT=Path(__file__).resolve().parents[1]
CONTRACT=json.loads((ROOT/'docs/q3-policy-prose-delta.json').read_text())
QUESTION=CONTRACT['question'];HELPER=CONTRACT['helper']

@lru_cache(maxsize=2)
def archive(phase):
    root=ROOT/CONTRACT[phase+'_archive']
    assert sha(root/'checksums.json')==CONTRACT[phase+'_seal']
    rows=json.loads((root/'checksums.json').read_text())['files']
    assert all(sha(root/r['path'])==r['sha256'] for r in rows)
    return root

def fixtures(language):
    archive('baseline');archive('prototype')
    result={}
    for name,item in CONTRACT['languages'][language]['fixtures'].items():
        path=ROOT/item['path'];assert sha(path)==item['sha256']==CONTRACT['languages'][language]['after'][name]
        result[name]=path.read_bytes()
    assert set(result)=={QUESTION,HELPER}
    return result

def current_q3_sources(current,language):
    record=CONTRACT['languages'][language]
    hashes=lambda data:{n:hashlib.sha256(v).hexdigest() for n,v in data.items()}
    if hashes(current)!=record['after'] and CONTRACT.get('version')=='0.3.51':
        from current_source_repairs import project_sources as project_current
        historical=integrated_package(language,'2000-01-01T00:00:00Z')['files']
        current,_=project_current(current,language,historical)
    assert hashes(current)==record['after'],'Unreviewed 0.3.51 prepared source, helper or asset'
    return current

def project_sources(current,language):
    current=current_q3_sources(current,language)
    record=CONTRACT['languages'][language]
    hashes=lambda data:{n:hashlib.sha256(v).hexdigest() for n,v in data.items()}
    assert all(current[n]==v for n,v in fixtures(language).items())
    from word_empty_section_integration import integrated_package as old, project_sources as verify_old
    before={n:v for n,v in current.items() if n!=HELPER}
    before[QUESTION]=next(f['content'].encode() for f in old(language,'2000-01-01T00:00:00Z')['files'] if f['fileName']==QUESTION)
    assert hashes(before)==record['before'],'Every 0.3.50 byte must be restored'
    assert set(current)-set(before)=={HELPER} and {n for n in before if current[n]!=before[n]}=={QUESTION}
    verify_old(before,language)
    return before

def integrated_package(language,timestamp):
    from word_empty_section_integration import integrated_package as old
    result=old(language,timestamp);changed=fixtures(language)
    result['version']='0.3.51';result['id']=result['id'].removesuffix('0.3.50')+'0.3.51'
    for item in result['files']:
        if item['fileName']==QUESTION:item['content']=changed[QUESTION].decode()
    result['files'].append(dict(fileName=HELPER,content=changed[HELPER].decode(),uuid=''))
    for kind in ['files','assets']:
        for item in result[kind]:item['uuid']=asset_uuid(result['id'],kind,item['fileName'])
        result[kind].sort(key=lambda item:item['fileName'])
    return result

def project_package(candidate,language,timestamp):
    from word_empty_section_integration import integrated_package as old
    expected=integrated_package(language,timestamp)
    if candidate!=expected:
        from current_source_repairs import project_package as project_current
        candidate,_=project_current(candidate,language,timestamp,expected)
    assert candidate==expected,'Unreviewed identity, format, source, asset metadata, UUID or timestamp'
    return old(language,timestamp)

def check_package(path,prepared,language,timestamp):
    from submission_flow_integration import sources
    current=sources(prepared);project_sources(current,language)
    expected=integrated_package(language,timestamp)
    with zipfile.ZipFile(path) as z:
        members={'template/template.json'}|{'template/assets/'+a['fileName'] for a in expected['assets']}
        assert len(z.namelist())==len(members) and set(z.namelist())==members
        metadata=json.loads(z.read('template/template.json'));project_package(metadata,language,timestamp)
        for item in metadata['assets']:assert z.read('template/assets/'+item['fileName'])==current[item['fileName']]
        for item in metadata['files']:assert item['content'].encode()==current[item['fileName']]
    return dict(package_sha256=sha(path),prepared_source_verified=True,deterministic_identity_verified=True,
        historical_projection_verified=True,
        historical_q3_delta=dict(added_source_files=[HELPER],changed_source_files=[QUESTION]))

def check(build,english,preview=False):
    from build import git,package_timestamp
    from submission_flow_integration import sources
    sys.path.insert(0,str(english/'scripts'))
    from q3_policy_prose_contract import project_source,load
    project_source()
    manifest=json.loads((build/'manifest.json').read_text())
    assert manifest['status']==('preview' if preview else 'candidate')
    assert manifest['source']['version']==manifest['translation']['version']=='0.3.51'
    if not preview:
        assert all(not c['dirty'] for c in manifest['checkouts'].values())
        assert manifest['source']['commit']==manifest['checkouts']['english']['commit']==git(english,'rev-parse','HEAD')
    assert manifest['package_timestamp']==package_timestamp(english)
    prior=json.loads((archive('baseline')/'build-manifest.json').read_text())
    files=list((ROOT/'translation').rglob('translation.md'))
    tree={str(p.relative_to(ROOT/'translation')):sha(p) for p in files}
    from probe_pdf_budget_translation import pair
    from probe_personal_data_translation import project_current_language_polish_translations
    historical_pairs,translation_delta=project_current_language_polish_translations([pair(p.read_text()) for p in files])
    assert len(tree)==manifest['translation_units']==translation_delta['current_units'] and not manifest['untranslated_units']
    assert tree==manifest['translation_tree_sha256']
    assert len(historical_pairs)==translation_delta['baseline_units']==len(prior['translation_tree_sha256'])
    packages={};comparisons={}
    for language,folder in [('english','en'),('chinese','translated')]:
        path=build/(language+'.zip');assert sha(path)==manifest['sha256'][path.name]
        packages[language]=check_package(path,build/folder,language,manifest['package_timestamp'])
        current=sources(build/folder);after=current_q3_sources(current,language);before=project_sources(after,language)
        rows=load('probe').check(english,before,after,language)
        with (build/('q3-policy-prose-'+language+'-cases.json')).open('x') as f:json.dump(rows,f,indent=2);f.write('\n')
        comparisons[language]=dict(total=len(rows),full_document=sum(r['case'].startswith('fixture-') for r in rows),
            joined=sum(r['joined_policies'] for r in rows),removed_inserted_spaces=sum(r['removed_owned_separators'] for r in rows))
        assert comparisons[language]==dict(total=7932,full_document=396,joined=1090 if language=='chinese' else 0,
            removed_inserted_spaces=1258 if language=='chinese' else 0)
    return dict(passed=True,source_integrated=True,version='0.3.51',baseline_version='0.3.50',
        translation_units=len(tree),historical_translation_units=len(historical_pairs),
        translation_delta=translation_delta,packages=packages,comparisons=comparisons,
        native_integrated_render_checked=False,release_acceptance=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build',type=Path,required=True);parser.add_argument('--english',type=Path,required=True)
    parser.add_argument('--preview',action='store_true');args=parser.parse_args()
    result=check(args.build.resolve(),args.english.resolve(),args.preview)
    with (args.build/'q3-policy-prose-integration.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result))
