"""Bind native output to final packages after the complete final-lock workflow.

The original clean package was rendered natively. A tests-only correction and
lock update must leave both final rebuilt packages bitwise identical to it.
"""
import hashlib,json,subprocess
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parent
EN=Path('/home/trc/Downloads/science-europe-template')
ZH=Path('/home/trc/Downloads/science-europe-template-zhtw')
PY='/home/trc/Downloads/dsw-document-template-tool/.venv/bin/python'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(repo,*args):return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
def write(p,value):
    with p.open('x') as f:json.dump(value,f,indent=2);f.write('\n')
def main():
    ci=read(ROOT/'ci.json');assert not ci['passed'] and len(ci['rows'])==55
    assert read(ROOT/'ci-verify-exit.json')['child_exit_code']==0
    assert read(ROOT/'ci-result-verification.json')['effective_workflow_checks_passed']==55
    assert read(ROOT/'english-exit.json')['child_exit_code']==0
    builds=[Path(Path('/tmp/se-q3-integration-build-'+n+'.log').read_text().strip()) for n in ['01','02','03','04','05','06']]
    manifests=[read(b/'manifest.json') for b in builds]
    for m in manifests:
        assert m['status']=='candidate' and all(not x['dirty'] for x in m['checkouts'].values())
        assert m['source']['version']==m['translation']['version']=='0.3.51'
        assert m['translation_tree_sha256']==manifests[0]['translation_tree_sha256']
        assert m['translation_units']==775 and not m['untranslated_units']
    assert manifests[0]['checkouts']==manifests[1]['checkouts']
    assert manifests[2]['checkouts']==manifests[3]['checkouts']
    assert manifests[4]['checkouts']==manifests[5]['checkouts']
    old,middle,new=[manifests[i]['checkouts'] for i in [0,2,4]]
    assert middle['english']==new['english'] and middle['tooling']==new['tooling']
    assert git(ZH,'diff','--name-only',middle['translation']['commit'],new['translation']['commit']).splitlines()==['tests/test_word_empty_section_prototype.py']
    assert old['tooling']==new['tooling']
    differences={}
    for key,repo,expected in [('english',EN,['tests/test_word_empty_section_spacing.py']),('translation',ZH,['pipeline.yml','tests/test_word_empty_section_prototype.py'])]:
        assert git(repo,'rev-parse','HEAD')==new[key]['commit'] and not git(repo,'status','--porcelain')
        paths=git(repo,'diff','--name-only',old[key]['commit'],new[key]['commit']).splitlines()
        assert paths==expected,(key,paths)
        differences[key]=paths
    before=yaml.safe_load(git(ZH,'show',old['translation']['commit']+':pipeline.yml'))
    after=yaml.safe_load((ZH/'pipeline.yml').read_text())
    assert before['source']['commit']==old['english']['commit']
    before['source']['commit']=new['english']['commit'];assert before==after
    assert sha(ZH/'.github/workflows/pilot-checks.yml')==ci['workflow_sha256']
    packages={}
    for name in ['english.zip','chinese.zip']:
        hashes=[sha(b/name) for b in builds]
        assert len(set(hashes))==1 and all(h==m['sha256'][name] for h,m in zip(hashes,manifests))
        packages[name]=hashes[0]
    assert all(m['package_timestamp']==manifests[0]['package_timestamp'] for m in manifests)
    assert ci['clean_candidate_manifest_sha256']==sha(builds[2]/'manifest.json')
    assert read(ROOT/'manifest.json')['build_manifest_sha256']==sha(builds[0]/'manifest.json')
    assert read(ROOT/'compare-exit.json')['child_exit_code']==0
    assert read(ROOT/'final-gate-exit.json')['child_exit_code']==0
    assert read(builds[4]/'q3-policy-prose-integration.json')['passed']
    report=dict(passed=True,full_workflow_rerun_after_chinese_test_fix=False,effective_workflow_checks_passed=55,
        final_unit_suite_rerun=True,final_identity_and_content_gate_rerun=True,
        prior_manifest_sha256=sha(builds[0]/'manifest.json'),workflow_manifest_sha256=sha(builds[2]/'manifest.json'),
        final_manifest_sha256=sha(builds[4]/'manifest.json'),final_rebuild_manifest_sha256=sha(builds[5]/'manifest.json'),
        prior_checkouts=old,workflow_checkouts=middle,final_checkouts=new,
        commit_differences=differences,packages_bitwise_identical_across_six_builds=True,package_sha256=packages,
        final_ci_sha256=sha(ROOT/'ci.json'),english_full_check_exit_sha256=sha(ROOT/'english-exit.json'),
        native_comparison_sha256=sha(ROOT/'checks.json'))
    write(ROOT/'final-lock-equivalence.json',report)
    raise SystemExit(0 if report['passed'] else 1)
if __name__=='__main__':main()
