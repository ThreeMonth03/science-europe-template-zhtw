"""Archive 0.3.22 Q8 Word continuity against actual 0.3.21 native baselines."""
import argparse
import json
from pathlib import Path
import shutil
from bs4 import BeautifulSoup
from artifact_utils import sha
from check_q8_word_outputs import CASES

ROOT=Path(__file__).resolve().parents[1]


def read(root,name):return json.loads((root/name).read_text())


def verify(root,hashes):
    for name,digest in hashes.items():assert sha(root/name)==digest,('Evidence drift',root,name)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['build','candidate','rebuild','prior','new-case-prior','failed-attempt','english','destination']:
        p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();assert not a.destination.exists()
    report=read(a.build,'q8-word-report.json');assert report['selected_checks_passed'] and len(report['rows'])==12
    expected={(c,l) for c in CASES for l in ['english','chinese']}
    assert {(r['case'],r['language']) for r in report['rows']}==expected
    assert all(not r['errors'] and not r['reading_issues'] for r in report['rows'])
    for root in [a.build,a.candidate,a.rebuild]:verify(root,report['package_sha256'])
    render=read(a.build,'missing-info-render-report.json')
    assert render['all_renders_succeeded'] and len(render['renders'])==36
    assert all(r['rendered'] for r in render['renders'])
    assert {(r['case'],r['language'],r['format']) for r in render['renders']}=={(c,l,f) for c,l in expected for f in ['html','pdf','docx']}
    restoration=read(a.build,'runtime-restoration.json')
    assert restoration['stock_worker_restored'] and len(restoration['services'])==4
    assert all(not row['running'] for row in restoration['services'])
    cleanup=read(a.build,'owned-test-template-cleanup.json')
    assert len(cleanup['deleted'])==2 and cleanup['project_references']==cleanup['document_references']==0
    baseline=read(a.new_case_prior,'missing-info-render-report.json')
    assert baseline['all_renders_succeeded'] and len(baseline['renders'])==12 and all(r['rendered'] for r in baseline['renders'])
    assert baseline['package_sha256']==read(a.prior,'missing-info-render-report.json')['package_sha256']
    verify(a.new_case_prior,baseline['package_sha256']);verify(a.prior,baseline['package_sha256'])
    current=read(a.build,'q8-list-continuity.json');old=read(a.prior,'q8-list-continuity.json')
    assert current['passed'] and len(current['rows'])==24 and not current['failures']
    assert not old['passed'] and old['failures']==[{'case':'personal-transfer-complete','language':'chinese','format':'word-preview',
        'label':'開放海岸觀測資料——測站1','label_page':4,'permission_page':5,'label_end_page':4,'permission_end_page':5,'together':False}]
    failed=read(a.failed_attempt,'q8-list-continuity.json')
    assert not failed['passed'] and old['failures'][0] in failed['failures']
    assert not read(a.failed_attempt,'q8-word-first-pair.json')['selected_checks_passed']
    verify(a.failed_attempt,failed['package_sha256'])
    copies=[];excerpts={}
    def keep(source,name):copies.append((source,Path(name)))
    for row in report['rows']:
        verify(a.build,row['artifact_sha256']);stem=row['case']+'-'+row['language']
        prior=a.new_case_prior if row['case'].startswith('q8-') else a.prior
        for label,root in [('before',prior),('after',a.build)]:
            for fmt in ['pdf','docx']:
                for suffix in ['', '.fixture.json']:
                    name=stem+'.'+fmt+suffix;keep(root/'renders'/name,label+'/native/'+name)
            keep(root/'word-preview'/(stem+'.pdf'),label+'/word-preview/'+stem+'.pdf')
            keep(root/'renders'/(stem+'.html.fixture.json'),label+'/native/'+stem+'.html.fixture.json')
        html=a.build/'renders'/(stem+'.html');soup=BeautifulSoup(html.read_text(),'html.parser')
        excerpts['question-content/'+stem+'.html']='<!-- Native HTML excerpt; full HTML SHA256: '+sha(html)+' -->\n'+str(soup.select_one('#dmp-content'))+'\n'
        locale='en' if row['language']=='english' else 'zh-Hant'
        for suffix in ['.json','.events.json']:
            name=row['case']+suffix;keep(a.english/'fixtures/pilot'/locale/name,'fixtures/'+locale+'/'+name)
    for name in ['q8-word-report.json','q8-list-continuity.json','remaining-q9-word-reading.json','missing-info-render-report.json','manifest.json','owned-test-template-cleanup.json','runtime-restoration.json']:
        keep(a.build/name,'after/'+name)
    for name in ['missing-info-render-report.json','manifest.json','owned-test-template-cleanup.json']:
        keep(a.new_case_prior/name,'before/new-cases-'+name)
    keep(a.prior/'q8-list-continuity.json','before/original-q8-list-failure.json')
    for name in ['q8-list-continuity.json','q8-word-first-pair.json','missing-info-render-report.json','manifest.json','owned-test-template-cleanup.json']:
        keep(a.failed_attempt/name,'failed-first-attempt/'+name)
    for case,language in [('personal-transfer-complete','chinese'),('personal-transfer-complete','english'),
                          ('q8-long-permissions','chinese'),('q8-many-references','english')]:
        stem=case+'-'+language
        for fmt in ['docx','pdf']:
            for suffix in ['', '.fixture.json']:
                keep(a.failed_attempt/'renders'/(stem+'.'+fmt+suffix),'failed-first-attempt/native/'+stem+'.'+fmt+suffix)
        keep(a.failed_attempt/'word-preview'/(stem+'.pdf'),'failed-first-attempt/word-preview/'+stem+'.pdf')
    for name in ['q8-word-scope.json','q8-word-probe.json']:
        assert read(a.candidate,name)['passed'];keep(a.candidate/name,'probes/'+name)
    for label,root in [('candidate',a.candidate),('rebuild',a.rebuild)]:
        m=read(root,'manifest.json');assert m['status']=='candidate' and all(not v['dirty'] for v in m['checkouts'].values())
        keep(root/'manifest.json',label+'-manifest.json')
    for file in sorted(a.build.glob('*.png')):keep(file,'page-samples/'+file.name)
    for name in ['check_q8_word_outputs.py','probe_q8_word_scope.py','probe_q8_list_continuity.py','cleanup_owned_runtime_templates.py','collect_q8_word_review.py']:
        keep(ROOT/'scripts'/name,'reproduce/'+name)
    for name in ['probe_q8_word.py','generate_q8_word_fixtures.py']:
        keep(a.english/'scripts'/name,'reproduce/'+name)
    keep(ROOT/'pipeline.yml','reproduce/pipeline.yml')
    for source,_ in copies:assert source.is_file(),source
    a.destination.mkdir(parents=True)
    for source,name in copies:
        path=a.destination/name;path.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,path)
    for name,value in excerpts.items():
        path=a.destination/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(value)
    rows={(r['case'],r['language']):r for r in report['rows']}
    table=['| 案例 | EN PDF / Word 預覽 | ZH PDF / Word 預覽 |','|---|---:|---:|']
    for case in CASES:
        en,zh=[rows[case,l] for l in ['english','chinese']]
        table.append(f"| {case} | {en['pages']} / {en['word_pages']} | {zh['pages']} / {zh['word_pages']} |")
    document='''# 0.3.22：Q8 Word 資料集名稱與授權說明連頁

本輪修正上一版中文 Word 第 8 題資料集名稱與授權說明跨頁分離的反例。
只改英文共用 Word Lua；全部 731 個翻譯檔、Jinja、PDF CSS、Word reference
樣式與字型都不變。不是重新翻譯或把原回答併成一段。

先看 [修正前中文 Word 預覽](before/word-preview/personal-transfer-complete-chinese.pdf)
與 [修正後中文 Word 預覽](after/word-preview/personal-transfer-complete-chinese.pdf)，
以及 [修正後英文 Word 預覽](after/word-preview/personal-transfer-complete-english.pdf)。
原生 [中文 DOCX](after/native/personal-transfer-complete-chinese.docx)／
[英文 DOCX](after/native/personal-transfer-complete-english.docx) 可下載；
PDF 對照：[中文](after/native/personal-transfer-complete-chinese.pdf)／
[英文](after/native/personal-transfer-complete-english.pdf)。

## 驗證

- 六組案例 × 中英文：原本反例、空白、否定、完整控制、30 段自訂限制、8 筆
  資料集。新版有 12 份原生 PDF、12 份 DOCX、12 份 HTML 和 12 份 Word 預覽。
- 每組均與實際 0.3.21 輸出比對；新增長／多筆案例另用上一版套件產生原生
  對照。不是用新版模擬舊版，也沒有覆蓋上一輪失敗證據。
- 原生 HTML 的 15 題及 PDF 正文／頁數不變。Word XML 只允許 Q8 合格名稱
  改為既有連頁樣式，其他文字、段落、條列、連結和樣式定義必須保留。
- 短名稱與授權說明的實際頁碼檢查通過；原始失敗與新版結果分別保存在
  `before/original-q8-list-failure.json` 與 `after/q8-list-continuity.json`。
- 初輪 AST 測試通過，實際 DOCX 卻忽略 Plain 名稱上的樣式，跨頁反例仍在。
  修正為保留所有 inline 的單一 Para 後，另建乾淨套件、重產全部 36 個輸出。
  `failed-first-attempt/` 保存失敗報告及中英文反例，不以最後成功樣張覆蓋。
- 26 組固定 Pandoc AST **及實際 DOCX** 探針涵蓋中英文邊界、單筆／多筆與拒絕案例。套件
  重建 checksum 相同，英中來源與翻譯範圍證據在 `probes/` 與 manifest。

'''+ '\n'.join(table)+'''

## 範圍限制

僅處理 Q8 直接清單中有界限的純文字名稱與短授權說明；長、複雜或含屬性的
區塊保留原樣，不強制整份問題或長回答同頁。Word 預覽使用 LibreOffice，
尚未在 Microsoft Word 環境完成驗收。短預算缺答提示折行、全篇留白與其他
閱讀問題仍待處理；CI／本輪檢查通過不等於整份 DMP 已可正式發布。

逐頁抽查另確認英文完整 Word 的 Q9 `Quality-checked coastal observations`
名稱仍在第 4 頁、第一個倫理旗標在第 5 頁；與上一版相同，沒有因 Q8 修正
而新增，但也未修好。失敗診斷保存在 `after/remaining-q9-word-reading.json`。
空白中文 PDF 的 Q15 與四個缺答提示雖同頁，尾頁仍偏空；`page-samples/`
保留這些頁面，不把機器檢查的無越界等同於理想閱讀品質。

全部測試在隔離本機使用合成資料。已清理本輪建立的暫存模板，原 ZIP 保留可
重新匯入；stock worker 已恢復，四個 pilot 服務停止，未操作線上 DSW 或 keyring。
沒有合併 main、建立 tag／release 或部署。stock worker 的 Markdown 表格仍是
發布門檻。`question-content/` 是原生 HTML 題目擷取，非另一種渲染結果；大型
完整 HTML 保存在本機 runtime 目錄，檔案 hash 可由報告核對。
'''
    (a.destination/'README.md').write_text(document)
    hashes={str(f.relative_to(a.destination)):sha(f) for f in sorted(a.destination.rglob('*')) if f.is_file()}
    (a.destination/'checksums.json').write_text(json.dumps(hashes,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'archive':str(a.destination),'verified_files':len(hashes)}))


if __name__=='__main__':main()
