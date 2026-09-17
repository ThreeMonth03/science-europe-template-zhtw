"""Archive verified same-fixture 0.3.32 → 0.3.33 bilingual evidence."""
import argparse
import json
from pathlib import Path
import shutil
from bs4 import BeautifulSoup
from artifact_utils import sha
from check_metadata_followup_outputs import CASES
ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['build','prior','candidate','rebuild','english','readme','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();assert not a.output.exists()
    report=json.loads((a.build/'metadata-followup-report.json').read_text())
    assert report['selected_checks_passed'] and len(report['rows'])==16
    assert {(r['case'],r['language']) for r in report['rows']}=={(c,l) for c in CASES for l in ['english','chinese']}
    assert all(r['passed'] and not r['errors'] and not r['reading_issues'] for r in report['rows'])
    assert sha(ROOT/'scripts/check_metadata_followup_outputs.py')==report['checker_sha256']
    assert sha(a.english/'scripts/metadata_followup_contract.py')==report['contract_sha256']
    for name,digest in report['helper_sha256'].items():assert sha(ROOT/'scripts'/name)==digest
    for name,digest in report['package_sha256'].items():assert sha(a.build/name)==sha(a.candidate/name)==sha(a.rebuild/name)==digest
    for root in [a.prior,a.build]:
        renders=json.loads((root/'missing-info-render-report.json').read_text())
        assert renders['all_renders_succeeded'] and len(renders['renders'])==48 and all(r['rendered'] for r in renders['renders'])
        cleanup=json.loads((root/'owned-test-template-cleanup.json').read_text())
        assert len(cleanup['deleted'])==2 and cleanup['project_references']==cleanup['document_references']==0
        for backup in cleanup['backups'].values():assert sha(Path(backup['path']))==backup['sha256']
        preview=json.loads((root/'word-preview-metadata-dictionary-metadata-dictionary-no-metadata-partial-metadata-private-metadata-private-text-metadata-complete-empty-negative.json').read_text())
        assert preview['completed'] and len(preview['rows'])==16
        for row in preview['rows']:
            assert sha(root/'renders'/(row['name']+'.docx'))==row['docx_sha256']
            assert sha(root/'word-preview'/(row['name']+'.pdf'))==row['preview_sha256']
    assert json.loads((a.build/'runtime-restoration.json').read_text())['restored_stock_and_stopped']
    assert json.loads((a.build/'unchanged-control-pixels.json').read_text())['passed']
    assert json.loads((a.build/'diagnostics/q5-context-reflow.json').read_text())['measurement_completed']
    assert json.loads((a.candidate/'metadata-followup-scope.json').read_text())['passed']
    for row in report['rows']:
        for name,digest in row['artifact_sha256'].items():assert sha(a.build/name)==digest
        for name,digest in row['prior_artifact_sha256'].items():assert sha(a.prior/name)==digest

    def copy(source,name):
        target=a.output/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)

    for prefix,root in [('before',a.prior),('after',a.build)]:
        for row in report['rows']:
            stem=row['case']+'-'+row['language']
            for fmt in ['pdf','docx']:copy(root/'renders'/(stem+'.'+fmt),prefix+'/native/'+stem+'.'+fmt)
            for fmt in ['html','pdf','docx']:copy(root/'renders'/(stem+'.'+fmt+'.fixture.json'),prefix+'/native/'+stem+'.'+fmt+'.fixture.json')
            copy(root/'word-preview'/(stem+'.pdf'),prefix+'/word-preview/'+stem+'.pdf')
            html=root/'renders'/(stem+'.html');soup=BeautifulSoup(html.read_text(),'html.parser')
            target=a.output/prefix/'question-content'/(stem+'.html');target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text('<!-- Native HTML SHA256: '+sha(html)+' -->\n'+str(soup.select_one('#dmp-content'))+'\n')
        for name in ['manifest.json','missing-info-render-report.json','owned-test-template-cleanup.json',
                     'word-preview-metadata-dictionary-metadata-dictionary-no-metadata-partial-metadata-private-metadata-private-text-metadata-complete-empty-negative.json']:copy(root/name,prefix+'/'+name)
    for locale in ['en','zh-Hant']:
        for case in CASES:
            for suffix in ['.json','.events.json']:copy(a.english/'fixtures/pilot'/locale/(case+suffix),'fixtures/'+locale+'/'+case+suffix)
    for name in ['metadata-followup-report.json','worker-start.json','worker-lifecycle.json','runtime-restoration.json','unchanged-control-pixels.json']:
        copy(a.build/name,'after/'+name)
    for folder in ['visual','diagnostics']:
        for f in sorted((a.build/folder).glob('*')):
            if f.is_file():copy(f,folder+'/'+f.name)
    for label,root in [('candidate',a.candidate),('rebuild',a.rebuild)]:copy(root/'manifest.json',label+'-manifest.json')
    for name in ['metadata-followup-scope.json','format-translation-probe.json','personal-data-translation-proof.json','missing-info-translation-proof.json']:
        copy(a.candidate/name,'probes/'+name)
    for name in sorted(set(report['helper_sha256'])|{'check_metadata_followup_outputs.py','collect_metadata_followup_review.py','probe_metadata_followup_scope.py','capture_metadata_pages.py','check_unchanged_control_pixels.py','probe_q5_followup_pagination.py'}):
        copy(ROOT/'scripts'/name,'reproduce/'+name)
    for name in ['metadata_followup_contract.py','generate_metadata_fixtures.py']:copy(a.english/'scripts'/name,'reproduce/'+name)
    copy(ROOT/'pipeline.yml','reproduce/pipeline.yml')
    copy(ROOT/'docs/metadata-followup-translation-delta.json','reproduce/metadata-followup-translation-delta.json')
    for folder in ['en','translated']:copy(a.candidate/folder/'src/questions/03-docs-metadata.html.j2','source/'+folder+'/03-docs-metadata.html.j2')
    for folder in ['en','translated']:copy(a.candidate/folder/'src/uuids.j2','source/'+folder+'/uuids.j2')
    copy(a.english/'docs/metadata-followup-bindings.json','reproduce/metadata-followup-bindings.json')
    copy(a.english/'tests/fixtures/metadata-0.3.32.en.html.j2','reproduce/metadata-0.3.32.en.html.j2')
    copy(ROOT/'tests/fixtures/metadata-0.3.32.zh-Hant.html.j2','reproduce/metadata-0.3.32.zh-Hant.html.j2')
    copy(a.readme,'README.md')
    checks={str(f.relative_to(a.output)):sha(f) for f in sorted(a.output.rglob('*')) if f.is_file()}
    (a.output/'checksums.json').write_text(json.dumps(checks,indent=2)+'\n')
    print(json.dumps({'archived':str(a.output),'candidate_native_outputs':48,'baseline_native_outputs':48,'word_previews':32,'files':len(checks)}))


if __name__=='__main__':main()
