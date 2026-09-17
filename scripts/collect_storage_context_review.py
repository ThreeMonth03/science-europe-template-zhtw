"""Archive verified 0.3.33 → 0.3.34 source, fixtures and native evidence."""
import argparse
import json
from pathlib import Path
import shutil
from bs4 import BeautifulSoup
from artifact_utils import sha
from check_storage_context_outputs import CASES,EXTRA
ROOT=Path(__file__).resolve().parents[1]


def verify_previews(root,stems):
    rows={}
    for path in root.glob('word-preview-*.json'):
        report=json.loads(path.read_text());assert report['completed']
        for row in report['rows']:
            name=row['name'];assert name not in rows
            assert sha(root/'renders'/(name+'.docx'))==row['docx_sha256']
            assert sha(root/'word-preview'/(name+'.pdf'))==row['preview_sha256']
            rows[name]=row
    assert set(rows)==set(stems), 'Preview receipts do not match the expected native documents'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['build','prior','prior-extra','candidate','rebuild','english','diagnostic','readme','output']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.output.exists()
    report=json.loads((a.build/'storage-context-report.json').read_text());assert report['content_and_scope_checks_passed'] and len(report['rows'])==20
    unresolved=[dict(case=r['case'],language=r['language'],**issue) for r in report['rows'] for issue in r['pagination_issues']]
    assert unresolved==[dict(case='metadata-partial',language='chinese',format='word',locations=[3,3,4,4,4])]
    assert not report['selected_checks_passed'] and not report['pagination_checks_passed'] and not report['release_acceptance']
    assert {(r['case'],r['language']) for r in report['rows']}=={(c,l) for c in CASES for l in ['english','chinese']}
    assert sha(ROOT/'scripts/check_storage_context_outputs.py')==report['checker_sha256']
    for name,digest in report['package_sha256'].items():assert sha(a.build/name)==sha(a.candidate/name)==sha(a.rebuild/name)==digest
    for root,count,cases in [(a.prior,48,[c for c in CASES if c not in EXTRA]),(a.prior_extra,12,EXTRA),(a.build,60,CASES)]:
        renders=json.loads((root/'missing-info-render-report.json').read_text());assert renders['all_renders_succeeded'] and len(renders['renders'])==count
        verify_previews(root,[c+'-'+l for c in cases for l in ['english','chinese']])
        cleanup=json.loads((root/'owned-test-template-cleanup.json').read_text());assert len(cleanup['deleted'])==2 and cleanup['project_references']==cleanup['document_references']==0
        for backup in cleanup['backups'].values():assert sha(Path(backup['path']))==backup['sha256']
    lifecycle=json.loads((a.build/'worker-lifecycle.json').read_text())
    assert lifecycle['same_worker_before_and_after'] and lifecycle['before']==lifecycle['after']==json.loads((a.build/'worker-start.json').read_text())
    assert json.loads((a.build/'runtime-restoration.json').read_text())['restored_stock_and_stopped']
    assert json.loads((a.build/'unchanged-control-pixels.json').read_text())['passed']
    for name in ['storage-context-scope.json','storage-context-engine-en.json','storage-context-engine-zh.json','identifier-spacing-engine.json']:
        assert json.loads((a.candidate/name).read_text())['passed']
    diagnostic=json.loads((a.diagnostic/'report.json').read_text());assert diagnostic['diagnostic_not_native']
    assert diagnostic['source_sha256']==sha(a.build/'renders/metadata-partial-chinese.docx')
    assert len(diagnostic['rows'])==4
    for row in diagnostic['rows']:
        assert row['q5_locations']==[3,3,4,4,4]
        for suffix,key in [('.docx','docx_sha256'),('.pdf','preview_sha256')]:
            assert sha(a.diagnostic/(row['mode']+suffix))==row[key]
    def copy(source,name):
        target=a.output/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    for row in report['rows']:
        assert row['content_and_scope_checks_passed'] and not row['errors'] and not row['reading_issues']
        case,language=row['case'],row['language'];stem=case+'-'+language
        prior=a.prior_extra if case in EXTRA else a.prior
        for label,root,key in [('before',prior,'before_sha256'),('after',a.build,'after_sha256')]:
            for name,digest in row[key].items():assert sha(root/name)==digest
            for fmt in ['pdf','docx']:copy(root/'renders'/(stem+'.'+fmt),label+'/native/'+stem+'.'+fmt)
            for fmt in ['html','pdf','docx']:copy(root/'renders'/(stem+'.'+fmt+'.fixture.json'),label+'/native/'+stem+'.'+fmt+'.fixture.json')
            copy(root/'word-preview'/(stem+'.pdf'),label+'/word-preview/'+stem+'.pdf')
            html=root/'renders'/(stem+'.html');soup=BeautifulSoup(html.read_text(),'html.parser')
            target=a.output/label/'question-content'/(stem+'.html');target.parent.mkdir(exist_ok=True,parents=True)
            target.write_text('<!-- Native HTML SHA256: '+sha(html)+' -->\n'+str(soup.select_one('#dmp-content'))+'\n')
    for label,root in [('before',a.prior),('before-extra',a.prior_extra),('after',a.build)]:
        for name in ['manifest.json','missing-info-render-report.json','owned-test-template-cleanup.json']:copy(root/name,label+'/'+name)
        for path in root.glob('word-preview-*.json'):copy(path,label+'/'+path.name)
    for locale in ['en','zh-Hant']:
        for case in CASES:
            for suffix in ['.json','.events.json']:copy(a.english/'fixtures/pilot'/locale/(case+suffix),'fixtures/'+locale+'/'+case+suffix)
    for name in ['storage-context-report.json','worker-start.json','worker-lifecycle.json','runtime-restoration.json','unchanged-control-pixels.json']:copy(a.build/name,'after/'+name)
    for path in (a.build/'visual').iterdir():copy(path,'visual/'+path.name)
    for path in a.diagnostic.iterdir():copy(path,'diagnostic-not-native/'+path.name)
    for name in ['storage-context-scope.json','storage-context-engine-en.json','storage-context-engine-zh.json','identifier-spacing-engine.json']:copy(a.candidate/name,'probes/'+name)
    for label,root in [('candidate',a.candidate),('rebuild',a.rebuild)]:copy(root/'manifest.json',label+'-manifest.json')
    for folder in ['en','translated']:
        for name in ['src/questions/05-store-backup.html.j2','src/storage-reading.html.j2','src/layout.css','src/word/pilot.lua']:copy(a.candidate/folder/name,'source/'+folder+'/'+name)
    for name in ['check_storage_context_outputs.py','capture_storage_context_pages.py','collect_storage_context_review.py','probe_storage_context_scope.py','check_unchanged_control_pixels.py','diagnose_q5_word_keep.py']:
        copy(ROOT/'scripts'/name,'reproduce/'+name)
    for name in ['probe_storage_context.py','storage_context_contract.py','probe_identifier_spacing.py']:copy(a.english/'scripts'/name,'reproduce/'+name)
    copy(a.english/'docs/storage-context-style-delta.json','reproduce/storage-context-style-delta.json')
    copy(a.english/'tests/fixtures/storage-context-0.3.33.en.html.j2','reproduce/storage-context-0.3.33.en.html.j2')
    copy(ROOT/'tests/fixtures/storage-context-0.3.33.zh-Hant.html.j2','reproduce/storage-context-0.3.33.zh-Hant.html.j2')
    copy(ROOT/'pipeline.yml','reproduce/pipeline.yml');copy(a.readme,'README.md')
    hashes={str(f.relative_to(a.output)):sha(f) for f in sorted(a.output.rglob('*')) if f.is_file()}
    (a.output/'checksums.json').write_text(json.dumps(hashes,indent=2)+'\n')
    print(json.dumps(dict(archived=str(a.output),files=len(hashes),native_outputs=120,word_previews=40)))


if __name__=='__main__':main()
