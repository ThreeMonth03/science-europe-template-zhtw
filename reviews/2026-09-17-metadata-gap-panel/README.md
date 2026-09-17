# 0.3.36：Q3 兩項漏填提示共用外框

這是局部排版改善：當後設資料公開政策的「取用說明」與「擷取／索引」皆未填時，
兩個相接的提示框改為一個。原句、標點、每項事實標記與 `missing` 狀態保留。
沒有改寫已填內容，也沒有把「選項無法轉換」當成漏填一起合併。

## 先看前後樣張

- 中文：[原版 PDF](before/metadata-partial-chinese.pdf) →
  [新版原生 PDF](native/metadata-partial-chinese.pdf)，改動在第 3 頁。
  [前](visual/before-chinese-page3.png)／[後](visual/after-chinese-page3.png)。
- 英文：[原版 PDF](before/metadata-partial-english.pdf) →
  [新版原生 PDF](native/metadata-partial-english.pdf)。
  [前](visual/before-english-page3.png)／[後](visual/after-english-page3.png)。
- 未改的可編輯 Word：[中文 DOCX](native/metadata-partial-chinese.docx)、
  [英文 DOCX](native/metadata-partial-english.docx)；
  [中文 Word 預覽](word-preview/metadata-partial-chinese.pdf)、
  [英文 Word 預覽](word-preview/metadata-partial-english.pdf)。
- 全空白仍完整呈現：[中文 PDF](native/empty-chinese.pdf)、[英文 PDF](native/empty-english.pdf)。
  自訂說明控制組：[中文](native/metadata-private-text-chinese.pdf)、[英文](native/metadata-private-text-english.pdf)。

## 實際結果

兩項提示的文字垂直跨度：中文約 41.4 → 33.1 pt，英文約 57.7 → 49.3 pt。
兩者都減少約 8.3 pt，字級、字框、換行及內容未改；不是靠縮字達成。
部分漏填的中英文原生 PDF 都維持 6 頁。這只是降低局部切割感，不等於整篇已好讀。

重新產出五組案例（部分漏填、完整、含自訂原因、空白、明確否定）× 中英 ×
HTML／PDF／DOCX，共 30 份原生輸出，再重新開啟 10 份 LibreOffice Word 預覽。

- [原生比對](metadata-gap-panel-report.json)：十五題 HTML 內容不變；全文文字、
  標點、連結保留，未新增字框重疊。十份 PDF／Word 的頁數各自與 0.3.35 相同。
- 所有 DOCX 正文 XML、樣式、字型與編號保留，十份 Word 預覽正文座標不變。
  上輪修好的中文 Q5 仍完整在第 4 頁，沒有退步。
- [空白／否定控制組影像](unchanged-control-pixels.json)：中英文 PDF 與 Word 預覽
  共八份的正文影像逐位元相同（100 dpi）。封面按實際第一題位置排除，不能把
  版號不同的封面冒充完全相同。
- [來源與翻譯範圍](probes/storage-context-scope.json)：744 個譯文檔不變、無未翻譯單位，
  保留既有 Q2／Q3／Q11 與 Q5 契約；只允許移除精確的新 CSS 規則後再套舊版檢查。
- [英文](probes/metadata-gap-panel-engine-en.json)／
  [中文](probes/metadata-gap-panel-engine-zh.json)各 30 組 Jinja 分支及 47 組引擎正反例，
  包含只缺一項、未知／否定狀態、富文字、額外子節點、螢幕與近頁底控制。
- 兩次乾淨建置與實際輸入 ZIP 相同：英文
  `2ab39706eb601960d56b22e6043ef8d939cd8bb3906e5fba7d69addbfdd52814`，中文
  `52889c5e4675d2a5ae95cd19686d721ccf73652c1e428019fc78c0e8388aa1e7`。

## 第一批失敗沒有被覆寫

[第一次批次](failed-attempt/missing-info-render-report.json)是 17 次成功、第 18 次失敗，
並非全部通過。[診斷摘錄](failed-attempt/runtime-failure.json)記錄 worker 取件延遲到
180 秒後，測試端同時逾時清除臨時專案，導致 `UPDATE document` 與 `DELETE project`
互鎖，worker 以 exit 2 結束。通知後為何先取不到工作仍未查明。

本機測試等待上限改為 600 秒後，使用相同 ZIP、新目錄重新跑完整 30 次；本目錄
的成功檔案全部來自第二批，沒有挪用第一批成功檔案。第二批使用同一 worker，
期間未再重啟。這不是已修復 DSW 佇列／交易問題的證明。

最後比對的初版檢查器將英文換行題目誤當成單行標題，因而中止；現已改成完整
多行標題定位，並新增保留字框與拒絕錯字的測試。`checker-correction/` 保留原始
比對程式與失敗報告。這是檢查器修正，沒有因此修改或重產 PDF。

第一批另有一次提早開啟 Word 預覽、中文 DOCX 尚未齊備的中斷，保存於
`failed-attempt/early-preview/`，不計入成功預覽。兩批各自只清除兩筆無引用臨時模板；
ZIP、原始輸出與資料卷保留。結束後還原 stock worker，停止四個隔離服務。
沒有使用正式站、使用者 keyring，也沒有修改其他本機服務。

## 維護與驗收邊界

英文 `e44157ba91ad9f8f2285a2e97e462364d278df47`，工具
`25e339fbdfb1d20796471055790aad6a4226b6ed`；中英文同在短期
`fix/metadata-gap-panel` 分支，中文鎖定英文，不另維護中文 CSS。
只改共用排版層；Jinja、問卷對應、翻譯及 Word 產生規則不變。

`native/` 是原生 PDF／DOCX 與三格式收據；`question-content/` 明示截取 HTML 問題區，
附原始完整 HTML 的 SHA256；`word-preview/` 是 LibreOffice 預覽，不是 DSW 原生 PDF
或 Microsoft Word 實機驗收。`checksums.json` 覆蓋其餘所有檔案。
重跑需固定工具與隔離 DSW，應使用新目錄，不覆寫證據。

仍是實驗版，未正式發布。重複的「尚待補充」、英文冗句與整篇閱讀密度仍須繼續改善；
這次沒有宣稱所有 Science Europe 分支、完整中文語氣或 Microsoft Word 已驗收。
下一步及測試端調整細節見[說明](../../docs/metadata-gap-panel.md)。
