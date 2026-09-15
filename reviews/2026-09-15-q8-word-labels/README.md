# 0.3.22：Q8 Word 資料集名稱與授權說明連頁

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

| 案例 | EN PDF / Word 預覽 | ZH PDF / Word 預覽 |
|---|---:|---:|
| personal-transfer-complete | 9 / 7 | 8 / 8 |
| empty | 4 / 3 | 4 / 3 |
| negative | 4 / 3 | 3 / 3 |
| preservation-complete | 8 / 7 | 7 / 8 |
| q8-long-permissions | 11 / 9 | 9 / 10 |
| q8-many-references | 10 / 9 | 9 / 10 |

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
