# 0.3.24：空白 Q15 缺答資訊框與整份 PDF

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

| 案例 | EN PDF 前 → 後 | ZH PDF 前 → 後 | EN / ZH Word 頁數（不變） |
|---|---:|---:|---:|
| empty | 4 → 4 | 4 → 3 | 3 / 3 |
| negative | 4 → 4 | 3 → 3 | 3 / 3 |
| personal-transfer-complete | 9 → 9 | 8 → 8 | 7 / 8 |
| partial | 5 → 5 | 5 → 5 | 4 / 4 |
| budget-long-no-currency | 10 → 10 | 9 → 9 | 9 / 10 |

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
