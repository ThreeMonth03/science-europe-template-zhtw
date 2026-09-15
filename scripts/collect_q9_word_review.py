"""Archive exact bilingual Q9 comparisons, retaining the original failed example."""
import argparse
import json
from pathlib import Path
import shutil
from bs4 import BeautifulSoup
from artifact_utils import sha
from check_q9_word_outputs import CASES

ROOT=Path(__file__).resolve().parents[1]


def read(root,name):return json.loads((root/name).read_text())


def verify(root,hashes):
    for name,digest in hashes.items():assert sha(root/name)==digest,(root,name)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['build','candidate','rebuild','prior','new-case-prior','rejected','english','destination']:p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();assert not a.destination.exists()
    report=read(a.build,'q9-word-report.json');assert report['selected_checks_passed'] and len(report['rows'])==12
    expected={(c,l) for c in CASES for l in ['english','chinese']}
    assert {(r['case'],r['language']) for r in report['rows']}==expected
    assert all(not r['errors'] and not r['reading_issues'] for r in report['rows'])
    for root in [a.build,a.candidate,a.rebuild]:verify(root,report['package_sha256'])
    render=read(a.build,'missing-info-render-report.json')
    assert render['all_renders_succeeded'] and len(render['renders'])==36 and all(r['rendered'] for r in render['renders'])
    assert {(r['case'],r['language'],r['format']) for r in render['renders']}=={(c,l,f) for c,l in expected for f in ['html','pdf','docx']}
    baseline=read(a.new_case_prior,'missing-info-render-report.json')
    assert baseline['all_renders_succeeded'] and len(baseline['renders'])==18 and all(r['rendered'] for r in baseline['renders'])
    assert baseline['package_sha256']==read(a.prior,'missing-info-render-report.json')['package_sha256']
    for root in [a.prior,a.new_case_prior]:verify(root,baseline['package_sha256'])
    continuity=read(a.build,'q8-list-continuity.json');assert continuity['passed'] and len(continuity['rows'])==24
    old=read(a.prior,'remaining-q9-word-reading.json');assert not old['passed']
    original=old['rows'][-1]['entries'][0];assert original['label_page']==4 and original['permission_page']==5 and not original['together']
    fixed=next(r for r in report['rows'] if r['case']=='personal-transfer-complete' and r['language']=='english')['q9_word_pairs'][0]
    assert fixed['label']==original['label'] and fixed['together']
    rejected=read(a.rejected,'layout-tradeoff.json');assert not rejected['accepted'] and rejected['prior_word_pages']==7 and rejected['attempt_word_pages']==8
    assert all(r['word_pages']<=r['prior_word_pages'] for r in report['rows'])
    state=read(a.build,'runtime-restoration.json');assert state['stock_worker_restored'] and len(state['services'])==4 and all(not s['running'] for s in state['services'])
    for root in [a.build,a.new_case_prior]:
        cleanup=read(root,'owned-test-template-cleanup.json');assert len(cleanup['deleted'])==2 and cleanup['project_references']==cleanup['document_references']==0
    copies=[];excerpts={}
    def keep(source,name):copies.append((source,Path(name)))
    for row in report['rows']:
        verify(a.build,row['artifact_sha256']);stem=row['case']+'-'+row['language']
        for path,digest in row['prior_artifact_sha256'].items():assert sha(Path(path))==digest
        prior=a.new_case_prior if row['case'].startswith('q9-') else a.prior
        for side,root in [('before',prior),('after',a.build)]:
            for fmt in ['pdf','docx']:
                for extra in ['','.fixture.json']:
                    name=stem+'.'+fmt+extra;keep(root/'renders'/name,side+'/native/'+name)
            keep(root/'renders'/(stem+'.html.fixture.json'),side+'/native/'+stem+'.html.fixture.json')
            keep(root/'word-preview'/(stem+'.pdf'),side+'/word-preview/'+stem+'.pdf')
        source=a.build/'renders'/(stem+'.html');soup=BeautifulSoup(source.read_text(),'html.parser')
        excerpts['question-content/'+stem+'.html']='<!-- Native HTML excerpt; full SHA256: '+sha(source)+' -->\n'+str(soup.select_one('#dmp-content'))+'\n'
        locale='en' if row['language']=='english' else 'zh-Hant'
        for suffix in ['.json','.events.json']:keep(a.english/'fixtures/pilot'/locale/(row['case']+suffix),'fixtures/'+locale+'/'+row['case']+suffix)
    for name in ['q9-word-report.json','q8-list-continuity.json','missing-info-render-report.json','manifest.json','runtime-restoration.json','owned-test-template-cleanup.json']:
        keep(a.build/name,'after/'+name)
    keep(a.prior/'remaining-q9-word-reading.json','before/original-q9-failure.json')
    for name in ['layout-tradeoff.json','q9-first-pair-report.json','manifest.json','missing-info-render-report.json','owned-test-template-cleanup.json']:
        keep(a.rejected/name,'rejected-style-only/'+name)
    stem='personal-transfer-complete-english'
    for fmt in ['pdf','docx']:
        for extra in ['','.fixture.json']:keep(a.rejected/'renders'/(stem+'.'+fmt+extra),'rejected-style-only/native/'+stem+'.'+fmt+extra)
    keep(a.rejected/'word-preview'/(stem+'.pdf'),'rejected-style-only/word-preview/'+stem+'.pdf')
    for file in sorted(a.rejected.glob('after-complete-en*.png')):keep(file,'rejected-style-only/page-samples/'+file.name)
    for name in ['missing-info-render-report.json','manifest.json','owned-test-template-cleanup.json']:keep(a.new_case_prior/name,'before/new-cases-'+name)
    for name in ['q9-word-probe.json','q9-word-scope.json']:
        assert read(a.candidate,name)['passed'];keep(a.candidate/name,'probes/'+name)
    for label,root in [('candidate',a.candidate),('rebuild',a.rebuild)]:
        m=read(root,'manifest.json');assert m['status']=='candidate' and all(not v['dirty'] for v in m['checkouts'].values());keep(root/'manifest.json',label+'-manifest.json')
    for file in sorted(a.build.glob('*.png')):keep(file,'page-samples/'+file.name)
    for name in ['check_q9_word_outputs.py','check_q8_word_outputs.py','probe_q9_word_scope.py','probe_q8_list_continuity.py','collect_q9_word_review.py','cleanup_owned_runtime_templates.py']:keep(ROOT/'scripts'/name,'reproduce/'+name)
    for name in ['probe_q9_word.py','probe_q8_word.py','q9_word_contract.py','generate_q9_word_fixtures.py']:keep(a.english/'scripts'/name,'reproduce/'+name)
    keep(ROOT/'pipeline.yml','reproduce/pipeline.yml')
    for source,_ in copies:assert source.is_file(),source
    a.destination.mkdir(parents=True)
    for source,name in copies:
        target=a.destination/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    for name,value in excerpts.items():
        target=a.destination/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(value)
    rows={(r['case'],r['language']):r for r in report['rows']}
    table=['| 案例 | EN PDF / Word 預覽 | ZH PDF / Word 預覽 |','|---|---:|---:|']
    for case in CASES:
        en,zh=[rows[case,l] for l in ['english','chinese']]
        table.append(f"| {case} | {en['pages']} / {en['word_pages']} | {zh['pages']} / {zh['word_pages']} |")
    doc='''# 0.3.23：Q9 Word 資料集名稱與倫理說明連頁

本輪只改共用 Word Lua，不改 Jinja、PDF CSS、字型、reference 樣式或任何
一個翻譯檔。731 個翻譯檔完全保留；沒有新增中文專用分支邏輯。

先比較 [原本英文 Word 預覽](before/word-preview/personal-transfer-complete-english.pdf)
與 [修正後英文 Word 預覽](after/word-preview/personal-transfer-complete-english.pdf)，
以及 [修正後中文 Word 預覽](after/word-preview/personal-transfer-complete-chinese.pdf)。
原生 DOCX：[英文](after/native/personal-transfer-complete-english.docx)／
[中文](after/native/personal-transfer-complete-chinese.docx)。
原生 PDF：[英文](after/native/personal-transfer-complete-english.pdf)／
[中文](after/native/personal-transfer-complete-chinese.pdf)。

## 本輪驗證

'''+f"原本英文 Q9 名稱在第 4 頁、第一項倫理說明在第 5 頁；修正後名稱與最後一項\n說明同在第 {fixed['label_page']} 頁。不是刪字、合併作者段落或強制整份清單同頁。\n\n"+'''
- 六組中英文，12 份 PDF、12 份 DOCX、12 份 HTML 與 12 份 Word 預覽。
  全空、否定、部分漏填、8 筆資料集及 30 段作者回答都有實際輸出。
- 新增案例先用真正的 0.3.22 套件輸出，不以新版模擬舊版；其餘案例使用
  保存的上一輪成品。原本失敗紀錄保留於 `before/original-q9-failure.json`。
- 15 題 HTML 完全相同；原生 PDF 正文與頁數不變。Word 只允許 Q9 合格名稱
  從 Compact 改成既有連頁樣式，並把兩句固定倫理說明合為一段，保留兩句完整
  文字、順序、標點。單項說明和自由回答不合併；所有其他段落 XML、連結及 styles.xml 不變。
- 短名稱與各自倫理說明在實際 Word／PDF 同頁；Q8 的原生連頁檢查也通過。
  一項漏填不會被補成「不包含」，兩項都漏填的既有提示仍保留。
- 29 組固定 Pandoc AST／實際 DOCX 探針，含邊界、混合、長篇與複雜拒絕形狀。
  乾淨候選與重建 ZIP hash 相同，來源範圍和翻譯不變證據在 `probes/`。
- 第一版只加連頁，英文完整 Word 卻從 7 頁增為 8 頁、把整組預算推到稀疏
  新頁。保留於 `rejected-style-only/`，沒有覆寫為成功樣張。最後版採兩句
  固定說明緊湊成段；全部案例均檢查整份 Word 沒有比 0.3.22 增頁。

'''+ '\n'.join(table)+'''

## 尚未驗收的範圍

這不是整份 DMP 的理想版面認證。短預算提示折行、空白中文 PDF 尾頁留白、
長／複雜名稱、其他種類標籤與語氣仍需逐一檢視。部分漏填本輪保留既有表達，
不代表已為每個缺項增加新提示。Word 預覽使用 LibreOffice，尚未完成 Microsoft
Word 實機驗收。stock worker 的 Markdown 表格仍是正式發布門檻。

本機隔離測試使用合成資料，沒有讀取 keyring 或操作線上 DSW。前版對照與新版
及未採用版各自建立的暫存模板已清理，ZIP 備份保留可重建；原版 worker 已恢復，
四個 pilot 服務已停止，沒有刪除 volumes，也沒有合併 main、tag 或 release。
`question-content/` 僅擷取原生 HTML 題目，完整 HTML 留在本機 runtime 目錄，
其 hash 可供核對；不是另外渲染的理想樣張。
'''
    (a.destination/'README.md').write_text(doc)
    checks={str(f.relative_to(a.destination)):sha(f) for f in sorted(a.destination.rglob('*')) if f.is_file()}
    (a.destination/'checksums.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'archive':str(a.destination),'verified_files':len(checks)}))


if __name__=='__main__':main()
