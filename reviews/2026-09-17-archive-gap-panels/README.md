# 0.3.30：Q11 相鄰缺答提示共用外框

本輪只調整 PDF／列印版三種固定配對：冷儲存費用與最低期限、延長保存
決策者與依據、過時格式與媒體移轉。每組兩個原有段落共用外框；不合併
句子、不縮字，不動中文翻譯、已填回答或作者自由段落。

## 看成品

- 保存細節漏填，中文第 6 頁：[前版](../2026-09-16-archive-basis-reading/after/native/preservation-partial-chinese.pdf) → [新版](after/native/preservation-partial-chinese.pdf)。五個獨立缺答框變成三組，五項提示及中間已填政策都在；另有「保存選擇仍需核對」框，不與缺答混在一起。
- 同一案例：[英文 PDF 第 6 頁](after/native/preservation-partial-english.pdf)、[中文 Word](after/native/preservation-partial-chinese.docx)、[Word 預覽](after/word-preview/preservation-partial-chinese.pdf)。Word 原本沒有這種外框，正文與版面完全不改。
- 過時格式／媒體都漏填：[中文 PDF 第 6 頁](after/native/archive-migration-gaps-chinese.pdf)、[英文 PDF 第 7 頁](after/native/archive-migration-gaps-english.pdf)。兩項仍為各自完整提示。
- 英文長篇：[前版第 6／7 頁](before-extra/native/budget-long-archive-gaps-english.pdf) → [新版第 6 頁](after/native/budget-long-archive-gaps-english.pdf)。「誰決定延長」與「決策依據」原跨兩頁，新版在同頁；後面的格式缺答仍獨立，不強迫整段同頁。
- 完全空白：[中文 PDF](after/native/empty-chinese.pdf)、[英文 PDF](after/native/empty-english.pdf)。十五題及缺答提示保留。這輪沒改空白文件，英文尾頁仍有大片留白。

## 核對結果

八組案例 × 中英 × HTML／PDF／DOCX = 48 個原生輸出，另有 16 份
LibreOffice Word 預覽，全部通過所選檢查。新加三組相同輸入的 0.3.29
基準，共 18 個原生輸出、6 份預覽；其餘基準在
[0.3.29 紀錄](../2026-09-16-archive-basis-reading/README.md)。

| 案例 | EN PDF 前→後 | ZH PDF 前→後 | EN／ZH Word 頁數（不變） |
|---|---:|---:|---:|
| 保存細節漏填 | 8→8 | 7→7 | 7／7 |
| 過時格式／媒體漏填 | 9→9 | 8→8 | 7／8 |
| 只有費用負擔漏填 | 9→9 | 8→8 | 7／8 |
| 長預算＋保存細節漏填 | 10→10 | 9→9 | 9／10 |
| 完整回答 | 9→9 | 8→8 | 7／8 |
| 自訂期限、不可延長 | 8→8 | 7→7 | 7／8 |
| 完全空白 | 4→4 | 3→3 | 3／3 |
| 明確否定 | 4→4 | 3→3 | 3／3 |

十組未受影響的語言／案例，PDF 正文頁的文字座標完全相同。受影響的
六組只改預定配對：九組原本同頁的提示減少 12 pt 的內部距離；另一組
原本跨頁，改為同頁。所有提示的文字行、寬度與字型 metrics 相同。
固定引擎另驗證外框連續、字級／行高不變、螢幕版不變，以及頁尾配對不拆開。

全部十五題 HTML 內容逐字／結構相同；所有 Word 正文 XML、表格、連結、
樣式、字型與編號不變，2386 個預覽正文段落核對保留。Word 正文頁座標
完全相同。封面日期／版本可能不同，排除封面頁，不刪除正文裡的日期文字。
PDF 正文比較允許折行空白；只處理有幾何證明的生成條列符號，與經完整
內容驗證的長預算續頁表頭。中英文長篇各 60 段用途及續頁身分全保留。

## 原文、翻譯與版本

唯一模板來源差異為英文 `src/layout.css` 的標記區塊。所有 Jinja、Lua、
字型、Word reference 與 732 個翻譯檔都與 0.3.29 相同。548 組既有 Q11
分支測試保留，新增 128 組中英缺答組合、80 個固定引擎檢查。
不是讓 LLM 重寫答案，也沒有第二套中文 Jinja。

兩 repo 使用短期分支 `fix/archive-gap-panels`；中文鎖英文完整 commit
`acf13bae71d1fda3c69a95759a2b513bd465bdd4`。模板版號 0.3.30，
upstream 基底仍為 1.30.1；沒有 merge main、tag 或正式發布。
原生候選來自 `692a1005582b69098e1fa6dc1c70b8f6640f2050`，
後續 commit 僅修測試。最終鎖定來源的乾淨重建與原生候選兩個 ZIP 完全
同 hash；候選／重建／原生 manifest 分別保存，不偽稱原生輸出重新產過。

未來升版先核對這三組 fact ID、標記結構與提示長度；有變動就重跑分支、
引擎及原生分頁測試。只在已證明相鄰、純文字、missing 的兩項之間分組；
遇到作者區塊、已填答案、其他期限、未知欄位、需核對或否定狀態不套用。
不以長期語言分支各維護一套樣式，也不為了保持版面而盲目合併 upstream。

## CI、失敗紀錄與本機環境

初輪中文 [CI 失敗](https://github.com/ThreeMonth03/science-europe-template-zhtw/actions/runs/35158377481)
發生於舊 Q13 探針的整份 CSS hash：新 Q11 區塊未被隔離。現在先驗證
該區塊完整 hash，再剝除它做原本 Q13 hash／行為檢查。舊 hash 未變，
也沒有移除測試；新增測試會拒絕未審閱區塊、重複標記或改過的留白。
`probes/identifier-spacing-engine.json` 是修正後 13 組 PDF／Word 探針結果。

引擎初版把頁碼當正文比對；原生初版則對條列抽字位置、舊版提示必須同頁
作了錯誤假設。失敗報告及當時的 checker 保留在 `diagnostics/`，修正時
沒有改模板／ZIP。最終 16 組報告為 `after/archive-gap-report.json`。

本輪使用本機 tables-only worker，沒有加入字型修補實驗。48 個新版與
18 個補充基準輸出期間，worker 啟動時間及 restart count 不變；不能據此
宣稱歷史 exit 139 已解決。已核對零 project／document 引用及 ZIP 備份，
清除本輪前版與新版共四個暫存模板，備份與樣張可恢復。已還原 stock
worker 並停止四個 pilot 服務，volumes 與其他服務保留；未讀 production
問卷、未取用 keyring。

## 可重現與驗收界線

重建命令與檢查器保存在 repo 的 `scripts/`，本次執行使用：

```bash
python scripts/build.py --english ../science-europe-template --tooling ../dsw-document-template-tool
python scripts/check_archive_gap_outputs.py \
  --build outputs/runtime-tables-hmb9qsrm \
  --prior outputs/runtime-tables-nuk4ctky \
  --prior-extra outputs/runtime-tables-am3ic1dw \
  --english ../science-europe-template \
  --output outputs/runtime-tables-hmb9qsrm/archive-gap-recheck.json
```

原生 rerun 需重新建立隔離的本機 runtime、使用新輸出路徑；完成紀錄不覆寫。
完整嵌字型 HTML 留本機，這裡存十五題摘錄、原檔 hash 和輸入 sidecar。
`checksums.json` 涵蓋本目錄其他全部檔案。

已目視中英文 Q11 PDF／Word、英文跨頁反例與中英空白尾頁。這是相鄰提示
的小範圍改善，不等於整份可讀性已理想，也不證明使用者已填得充分。
固定敘述仍有重複與生硬措辭、某些短段落及尾頁仍稀疏。下一步應從完整
中英文件逐段檢查敘述密度與提示語氣，保留來源資訊，再決定要改哪些固定句；
Science Europe 全面覆蓋、所有問卷組合及 Microsoft Word 實機仍待驗收。
