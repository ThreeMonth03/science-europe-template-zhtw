"""Freeze verified Word-width evidence, including rejected diagnostic checks."""
import argparse
import json
from pathlib import Path
import shutil
from bs4 import BeautifulSoup
from artifact_utils import sha
from check_word_short_budget_outputs import CASES

ROOT=Path(__file__).resolve().parents[1]
def read(root,name):return json.loads((root/name).read_text())
def verify(root,hashes):
    for name,value in hashes.items():assert sha(root/name)==value,(root,name)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['build','candidate','rebuild','prior','preflight','failed-preflight','english','destination']:
        p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();assert not a.destination.exists()
    report=read(a.build,'word-short-budget-report.json')
    assert report['selected_checks_passed'] and len(report['rows'])==14
    expected={(c,l) for c in CASES for l in ['english','chinese']}
    assert {(r['case'],r['language']) for r in report['rows']}==expected
    assert all(not r['errors'] and not r['reading_issues'] for r in report['rows'])
    assert report['checker_sha256']==sha(ROOT/'scripts/check_word_short_budget_outputs.py')
    for root in [a.build,a.candidate,a.rebuild]:verify(root,report['package_sha256'])
    verify(a.prior,report['prior_package_sha256'])
    renders=read(a.build,'missing-info-render-report.json')
    assert renders['all_renders_succeeded'] and len(renders['renders'])==42
    assert all(r['rendered'] for r in renders['renders'])
    assert {(r['case'],r['language'],r['format']) for r in renders['renders']}=={(c,l,f) for c,l in expected for f in ['html','pdf','docx']}
    cleanup=read(a.build,'owned-test-template-cleanup.json')
    assert len(cleanup['deleted'])==2 and cleanup['project_references']==cleanup['document_references']==0
    state=read(a.build,'runtime-restoration.json')
    assert state['stock_worker_restored'] and len(state['services'])==4 and all(not s['running'] for s in state['services'])
    lifecycle=read(a.build,'worker-lifecycle.json')
    assert lifecycle['no_container_restart_during_run'] and lifecycle['all_42_renders_completed'] and not lifecycle['font_patch_applied']
    copies=[];excerpts={}
    def keep(source,name):copies.append((source,Path(name)))
    for row in report['rows']:
        verify(a.build,row['artifact_sha256'])
        for name,value in row['prior_artifact_sha256'].items():assert sha(Path(name))==value
        stem=row['case']+'-'+row['language']
        for side,root in [('before',a.prior),('after',a.build)]:
            for fmt in ['pdf','docx']:
                for extra in ['','.fixture.json']:keep(root/'renders'/(stem+'.'+fmt+extra),side+'/native/'+stem+'.'+fmt+extra)
            keep(root/'renders'/(stem+'.html.fixture.json'),side+'/native/'+stem+'.html.fixture.json')
            keep(root/'word-preview'/(stem+'.pdf'),side+'/word-preview/'+stem+'.pdf')
        source=a.build/'renders'/(stem+'.html');soup=BeautifulSoup(source.read_text(),'html.parser')
        excerpts['question-content/'+stem+'.html']='<!-- Exact native question excerpt; full HTML SHA256: '+sha(source)+' -->\n'+str(soup.select_one('#dmp-content'))+'\n'
        locale='en' if row['language']=='english' else 'zh-Hant'
        for suffix in ['.json','.events.json']:keep(a.english/'fixtures/pilot'/locale/(row['case']+suffix),'fixtures/'+locale+'/'+row['case']+suffix)
    for name in ['word-short-budget-report.json','manifest.json','missing-info-render-report.json','worker-start.json','worker-lifecycle.json','owned-test-template-cleanup.json','runtime-restoration.json']:
        keep(a.build/name,'after/'+name)
    for file in a.build.glob('word-preview-*.json'):keep(file,'after/'+file.name)
    for label,root in [('candidate',a.candidate),('rebuild',a.rebuild)]:
        manifest=read(root,'manifest.json');assert manifest['status']=='candidate' and all(not v['dirty'] for v in manifest['checkouts'].values())
        keep(root/'manifest.json',label+'-manifest.json')
    for name in ['word-short-budget-scope.json','word-short-budget-english.json','word-short-budget-chinese.json','short-budget-english.json','short-budget-chinese.json','long-budget-word-probe.json','q8-word-probe.json','q9-word-probe.json','pdf-budget-english.json','pdf-budget-chinese.json']:
        assert read(a.candidate,name)['passed'];keep(a.candidate/name,'probes/'+name)
    trial=read(a.preflight,'report.json');assert trial['completed'] and trial['checker_sha256']==sha(ROOT/'scripts/rehearse_word_short_budget.py')
    for folder,label in [(a.preflight,'width-trials'),(a.failed_preflight,'failed-first-trial')]:
        for file in folder.iterdir():
            if file.is_file():keep(file,'diagnostics/'+label+'/'+file.name)
    for report_name,script_name in [('word-short-budget-targets.json','check_word_short_budget_outputs-v1.py'),('word-short-budget-targets-v2.json','check_word_short_budget_outputs-v2.py')]:
        failure=read(a.build,report_name);assert not failure['selected_checks_passed']
        assert failure['checker_sha256']==sha(a.build/script_name)
        for name in [report_name,script_name]:keep(a.build/name,'diagnostics/preview-oracles/'+name)
    keep(a.build/'word-short-budget-targets-v3.json','diagnostics/preview-oracles/word-short-budget-targets-v3.json')
    for file in a.build.glob('*.png'):keep(file,'page-samples/'+file.name)
    for name in ['collect_word_short_budget_review.py','check_word_short_budget_outputs.py','probe_word_short_budget_scope.py','preview_word_short_budget.py','rehearse_word_short_budget.py','cleanup_owned_runtime_templates.py']:
        keep(ROOT/'scripts'/name,'reproduce/'+name)
    for name in ['probe_word_short_budget.py','word_short_budget_contract.py']:
        keep(a.english/'scripts'/name,'reproduce/'+name)
    keep(ROOT/'pipeline.yml','reproduce/pipeline.yml')
    keep(ROOT/'experiments/markdown-tables/compose.diagnostics.yml','reproduce/compose.diagnostics.yml')
    for source,_ in copies:assert source.is_file(),source
    a.destination.mkdir(parents=True)
    for source,name in copies:
        target=a.destination/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    for name,value in excerpts.items():
        target=a.destination/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(value)
    rows={(r['case'],r['language']):r for r in report['rows']}
    table=['| 案例 | EN 原生 PDF / Word 頁數 | ZH 原生 PDF / Word 頁數 |','|---|---:|---:|']
    for case in CASES:
        en,zh=[rows[case,l] for l in ['english','chinese']]
        table.append(f"| {case} | {en['pages']} / {en['word_pages']} | {zh['pages']} / {zh['word_pages']} |")
    doc='''# 0.3.26：Word 短預算缺答提示

partial 中文 Word 的缺幣別提示由 2 行變 1 行，英文由 3 行變 2 行；
兩份仍各 4 頁。沒有縮小字級、刪減答案或提示，也沒有改寫中文。

先看 Word 的 LibreOffice 預覽：
[中文前版](before/word-preview/partial-chinese.pdf) → [中文新版](after/word-preview/partial-chinese.pdf)、
[英文前版](before/word-preview/partial-english.pdf) → [英文新版](after/word-preview/partial-english.pdf)。
可編輯 DOCX：[中文](after/native/partial-chinese.docx)、[英文](after/native/partial-english.docx)。
混合缺答：[中文 Word 預覽](after/word-preview/budget-mixed-gaps-chinese.pdf)、
[英文 Word 預覽](after/word-preview/budget-mixed-gaps-english.pdf)。

## 核對結果

七組英中各自輸出 HTML／PDF／DOCX，共 42 個原生檔案；另有 14 份 Word
預覽。15 題 HTML 完全相同，原生 PDF 正文及逐頁分布不變。Word 只有
partial 與 budget-mixed-gaps 的四張表格欄寬改動，其餘本文 XML、styles、
numbering、fontTable、外部連結完全保留；所有案例頁數不變。
Word 預覽另核對正文段落文字，包含缺答、5000、0 TWD 及長回答。

'''+ '\n'.join(table)+'''

## 來源、版本與實驗邊界

共用 Jinja 判斷 1–3 列、短且簡單、至少一筆預算缺答，Word 入口只提供
版型標記；Lua 在 Q15 將欄寬由 57/17/26 改為 49/25/26。完整、長篇、
八筆預算等控制組不套用。不是根據中英文提示字串猜測，也不改回答狀態。
中英各 46 組 autoescape／Jinja／AST／DOCX 探針通過；原有 PDF 短／長
表格及 Q8／Q9 探針保留。四個 prepared src 的新增內容移除後，與 0.3.25
hash 完全相同；其餘來源、字型、Word reference 與 731 個翻譯檔不變。
乾淨候選與重建 ZIP hash 相同，證據在 `probes/` 及兩份 manifest。

英中兩個 repo 使用短期 `fix/word-short-budget-widths`，中文鎖英文 commit，
仍沿用既有翻譯工具，不另養中文 Jinja。沒有 upstream 升級、main merge、
tag 或正式 release。引擎沿用 tables-only，沒有混入字型修補實驗。

## 保留的診斷與未完成事項

- `diagnostics/width-trials` 保留凍結 DOCX 的兩種欄寬試算；46/28/26 未採用，
  49/25/26 已達成目標，故保留較多用途欄寬。這些不是原生輸出。
- 初版試算誤以為每格都有 tcW，在第一份基準後停止。原檔及失敗工具留在
  `failed-first-trial`，修正後用新目錄完整重跑，不覆寫失敗證據。
- Word 預覽的頁尾在 raw 抽取順序可能在正文前；初版檢查被拒絕。現在先核對
  頁尾內容、唯一性與底部座標，才移除已驗證頁尾，不刪除任意數字。
- LibreOffice 把模板 ISO 日期的不換行連字號抽成一般連字號。第二版檢查
  保留，最後只對 HTML 標記、Word 完整文字 run 與數量皆相符的日期建立
  抽取對應；作者檔名、其他標點與正文不做全域正規化。原生 DOCX XML
  已另外證明文字完全保留，不能用抽取差異掩蓋內容損失。
- 中文混合缺答仍有較空的尾頁，英文部分提示仍需兩到三行；這不是整份
  DMP 理想版面、所有問卷分支或 Science Europe 實質內容完成驗收。
- 預覽使用 LibreOffice，不代表 Microsoft Word 實機驗收。真實代表案例、
  整份中英文語氣／閱讀節奏與 stock worker 表格相容性仍待驗證。

本輪 worker 開啟 faulthandler，42 個輸出沒有 container restart；不能因此
宣稱歷史 exit 139 根因已修復。兩個本輪暫存模板確認無引用後清理，ZIP
備份保留；stock worker 恢復，四個 pilot 服務停止，volumes 沒有刪除。
沒有 keyring 或線上 DSW 操作。完整 HTML 留在本機並記錄 hash，這裡保存
原生 PDF／DOCX、Word 預覽、題目摘錄、來源及失敗檢查紀錄。
'''
    (a.destination/'README.md').write_text(doc)
    checks={str(f.relative_to(a.destination)):sha(f) for f in sorted(a.destination.rglob('*')) if f.is_file()}
    (a.destination/'checksums.json').write_text(json.dumps(checks,indent=2)+'\n')
    print(json.dumps({'archive':str(a.destination),'verified_files':len(checks)}))


if __name__=='__main__':main()
