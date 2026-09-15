"""Preserve exact native before/after evidence for the bounded empty-Q15 panel."""
import argparse
import json
from pathlib import Path
import shutil
from bs4 import BeautifulSoup
from artifact_utils import sha
from check_empty_pdf_outputs import CASES,NEW_BASELINES

ROOT=Path(__file__).resolve().parents[1]


def read(root,name):return json.loads((root/name).read_text())


def verify(root,hashes):
    for name,digest in hashes.items():assert sha(root/name)==digest,(root,name)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['build','candidate','rebuild','prior','extra-prior','preflight','english','destination']:p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();assert not a.destination.exists()
    report=read(a.build,'empty-pdf-report.json');assert report['selected_checks_passed']
    expected={(c,l) for c in CASES for l in ['english','chinese']}
    assert len(report['rows'])==10 and {(r['case'],r['language']) for r in report['rows']}==expected
    assert all(not r['errors'] and not r['reading_issues'] for r in report['rows'])
    for root in [a.build,a.candidate,a.rebuild]:verify(root,report['package_sha256'])
    for root,count in [(a.build,30),(a.extra_prior,12)]:
        render=read(root,'missing-info-render-report.json')
        assert render['all_renders_succeeded'] and len(render['renders'])==count and all(r['rendered'] for r in render['renders'])
        cleanup=read(root,'owned-test-template-cleanup.json')
        assert len(cleanup['deleted'])==2 and cleanup['project_references']==cleanup['document_references']==0
    before_hashes=read(a.prior,'missing-info-render-report.json')['package_sha256']
    assert before_hashes==read(a.extra_prior,'missing-info-render-report.json')['package_sha256']
    for root in [a.prior,a.extra_prior]:verify(root,before_hashes)
    state=read(a.build,'runtime-restoration.json')
    assert state['stock_worker_restored'] and len(state['services'])==4 and all(not s['running'] for s in state['services'])
    copies=[];excerpts={}
    def keep(source,target):copies.append((source,Path(target)))
    for row in report['rows']:
        verify(a.build,row['artifact_sha256'])
        for name,digest in row['prior_artifact_sha256'].items():assert sha(Path(name))==digest
        stem=row['case']+'-'+row['language'];prior=a.extra_prior if row['case'] in NEW_BASELINES else a.prior
        for side,root in [('before',prior),('after',a.build)]:
            for fmt in ['pdf','docx']:
                for extra in ['', '.fixture.json']:
                    name=stem+'.'+fmt+extra;keep(root/'renders'/name,side+'/native/'+name)
            keep(root/'renders'/(stem+'.html.fixture.json'),side+'/native/'+stem+'.html.fixture.json')
            keep(root/'word-preview'/(stem+'.pdf'),side+'/word-preview/'+stem+'.pdf')
        source=a.build/'renders'/(stem+'.html');soup=BeautifulSoup(source.read_text(),'html.parser')
        excerpts['question-content/'+stem+'.html']='<!-- Exact native question excerpt; full HTML SHA256: '+sha(source)+' -->\n'+str(soup.select_one('#dmp-content'))+'\n'
        locale='en' if row['language']=='english' else 'zh-Hant'
        for suffix in ['.json','.events.json']:keep(a.english/'fixtures/pilot'/locale/(row['case']+suffix),'fixtures/'+locale+'/'+row['case']+suffix)
    for name in ['empty-pdf-report.json','manifest.json','missing-info-render-report.json','owned-test-template-cleanup.json','runtime-restoration.json']:keep(a.build/name,'after/'+name)
    for label,root in [('candidate',a.candidate),('rebuild',a.rebuild)]:
        m=read(root,'manifest.json');assert m['status']=='candidate' and all(not c['dirty'] for c in m['checkouts'].values())
        keep(root/'manifest.json',label+'-manifest.json')
    for name in ['empty-pdf-scope.json','empty-pdf-probe-english.json','empty-pdf-probe-chinese.json','missing-info-group-probe.json']:
        assert read(a.candidate,name)['passed'];keep(a.candidate/name,'probes/'+name)
    for name in ['manifest.json','missing-info-render-report.json','owned-test-template-cleanup.json']:keep(a.extra_prior/name,'before/extra-cases-'+name)
    for name in ['report.json','probe-lifetime-diagnostic.json','initial-ci-failure.json']:keep(a.preflight/name,'diagnostics/'+name)
    assert read(a.preflight,'initial-ci-failure.json')['accepted'] is False
    for root,folder in [(a.build,'page-samples'),(a.preflight,'diagnostics/page-samples')]:
        for f in sorted(root.glob('*.png')):keep(f,folder+'/'+f.name)
    for name in ['collect_empty_pdf_review.py','check_empty_pdf_outputs.py','probe_empty_pdf_scope.py','rehearse_empty_pdf.py','cleanup_owned_runtime_templates.py']:keep(ROOT/'scripts'/name,'reproduce/'+name)
    keep(a.english/'scripts/probe_empty_pdf.py','reproduce/probe_empty_pdf.py')
    keep(ROOT/'pipeline.yml','reproduce/pipeline.yml')
    for source,_ in copies:assert source.is_file(),source
    a.destination.mkdir(parents=True)
    for source,name in copies:
        target=a.destination/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    for name,content in excerpts.items():
        target=a.destination/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(content)
    rows={(r['case'],r['language']):r for r in report['rows']}
    table=['| 案例 | EN PDF 前 → 後 | ZH PDF 前 → 後 | EN / ZH Word 頁數（不變） |','|---|---:|---:|---:|']
    for case in CASES:
        en,zh=[rows[case,l] for l in ['english','chinese']]
        table.append(f"| {case} | {en['prior_pages']} → {en['pages']} | {zh['prior_pages']} → {zh['pages']} | {en['word_pages']} / {zh['word_pages']} |")
    doc='''# 0.3.24：空白 Q15 缺答資訊框與整份 PDF

空白中文原生 PDF 從 4 頁減為 3 頁：四項缺答保留原段落、原字級與文字，
只共用一個框，減少重複內距。英文空白仍為 4 頁，沒有宣稱英文尾頁留白已解決。
部分填答、否定、完整與長預算控制組不套用此規則。

先看 [原中文空白 PDF](before/native/empty-chinese.pdf) →
[新版中文空白 PDF](after/native/empty-chinese.pdf)，以及
[新版英文空白 PDF](after/native/empty-english.pdf)。
完整案例：[中文 PDF](after/native/personal-transfer-complete-chinese.pdf)、
[英文 PDF](after/native/personal-transfer-complete-english.pdf)、
[中文 Word](after/native/personal-transfer-complete-chinese.docx)、
[英文 Word](after/native/personal-transfer-complete-english.docx)。

## 同一批回答的實際比較

五組中英文，30 個原生輸出（10 HTML、10 PDF、10 DOCX），另有 10 份
LibreOffice Word 預覽。新增比較用的短預算部分漏答／長預算漏幣別，先以
真正的 0.3.23 補產 12 個前版輸出；其餘前版取自保存的 0.3.23 原生結果。

十五題 HTML 完全相同；全部 PDF 題目正文、已輸出缺答提示和自填段落保留。
除空白中文少一頁，其他 PDF 頁數不變；非空白控制的題目正文分頁完全相同。
Word 本文 XML、樣式、外部連結與預覽頁數全不變。長篇漏幣別的兩語言各
60 段用途、5000 金額及第二筆 0 TWD 保留，續頁仍有同筆資源與缺答資訊。

'''+ '\n'.join(table)+'''

## 檢查與可追溯性

- 新版只新增英文共用 CSS 區段；移除該區段後，CSS 與前版逐位元相同。
  其他 prepared src（含 Word Lua／reference、字型、Jinja）與 731 個翻譯檔相同。
- 英中各 13 組固定引擎探針，涵蓋精確四項、順序／狀態錯誤、缺項、額外與
  長自由回答；原有 8 組缺答群組連頁探針也通過。
- 初版中文探針／CI exit 139 保留於 `diagnostics/initial-ci-failure.json`。
  探針未展開 prepared CSS 的字型資產；載入同一份實際中文字型後通過。
  修正測試程式而非略過中文，並加入字型缺失不得靜默降級的單元測試。
- 原生輸出的來源 manifest 與最後測試程式修正後的候選 manifest 分開保存；
  各自 commit 如實記錄，英文與中文 ZIP 均核對逐位元相同，沒有混用不同套件。

## 邊界與下一步

短預算缺答提示折行、短表格移到稀疏尾頁仍待處理；[中文部分填答](after/native/partial-chinese.pdf)
是未修正的控制組，不是理想版面樣張。英文空白尾頁仍有留白。這不是整份
DMP 語氣、所有問卷分支或 Science Europe 實質內容驗收；Word 預覽不等於
Microsoft Word 實機驗收，stock worker 的 Markdown 表格仍是發布門檻。

本輪只用本機合成資料，不存取 keyring 或操作線上 DSW。前版補測與新版各自
建立的兩個暫存模板已核對無專案／文件引用後清理，ZIP 備份可重建；原版 worker
已恢復，四個 pilot 服務停止，沒有刪除 volumes、合併 main、建立 tag 或發布。
HTML 只擷取題目至 `question-content/`，完整原生 HTML 留在本機，hash 已保存。
'''
    (a.destination/'README.md').write_text(doc)
    hashes={str(f.relative_to(a.destination)):sha(f) for f in sorted(a.destination.rglob('*')) if f.is_file()}
    (a.destination/'checksums.json').write_text(json.dumps(hashes,indent=2)+'\n')
    print(json.dumps({'archive':str(a.destination),'verified_files':len(hashes)}))


if __name__=='__main__':main()
