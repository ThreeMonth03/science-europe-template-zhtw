# 0.3.37：中英文 Q3 缺漏提示成段

本輪完成限定實驗，非正式發布。Science Europe 十五題與問卷綁定不變。
兩個 repo 均使用 `fix/metadata-gap-prose`；中文鎖定英文完整 commit
`0730b11c4027fcc020c441a3c36264d85649321c`。

## 直接看樣張

| 成品 | 0.3.36 | 0.3.37 |
|---|---|---|
| 中文 PDF | [修改前](before/metadata-partial-chinese.pdf) | [修改後](native/metadata-partial-chinese.pdf) |
| 英文 PDF | [修改前](before/metadata-partial-english.pdf) | [修改後](native/metadata-partial-english.pdf) |
| 中文 Word 預覽 | [修改前](before/metadata-partial-chinese-word.pdf) | [修改後](word-preview/metadata-partial-chinese.pdf) |
| 英文 Word 預覽 | [修改前](before/metadata-partial-english-word.pdf) | [修改後](word-preview/metadata-partial-english.pdf) |

可編輯原件：[中文 DOCX](native/metadata-partial-chinese.docx)、
[英文 DOCX](native/metadata-partial-english.docx)。四組變更都在第 3 頁。
`visual/` 保存 PDF／Word 前後頁面影像；Word 預覽由 LibreOffice 25.2.3.2 產生。

## 改了什麼

只有在選擇公開後設資料、兩個相關追問都未填時，呈現一段：

> 尚待補充：後設資料是否會包含取用資料的說明；後設資料是否可供自動擷取並建立索引。

「取用說明」與「擷取索引」仍各有獨立的 missing 標記。資料字典、儲存容量、
已填文字、明確選否與未知選項不混在一起，也不補造答案。
英文共用 Jinja 負責條件及標記，中文譯文負責語序與標點；原有 744 組譯文全保留，
新增 3 組。取消上版七行專用 CSS；無新 Lua、字型、Word reference 或翻譯工具修改。

## 限定驗證結果

- 5 案例 × 中英 × HTML/PDF/DOCX：30 份全數完成，另有 10 份 LibreOffice 預覽。
- 部分漏填的中文提示：PDF 與 Word 均由兩行成為一行；英文均由三行成為兩行。
  文字區塊高度分別由 PDF 33.054→15.204 pt（中）、49.329→30.954 pt（英），
  Word 37.404→15.204 pt（中）、44.718→26.218 pt（英）。字級度量與左對齊保留。
- 全部案例 PDF／Word 頁數不變；四個其他案例的全文、Word XML 及正文座標不變。
- 全空與全否定的 8 份 PDF／Word 預覽，共 18 個正文頁，100 dpi 影像逐位元相同。
- 部分漏填 Q5 Word 政策／限制保持同頁：英文第 3 頁、中文第 4 頁。
- 中英各 1,726 個完整 Q3 前後 DOM 比較；另保留 Q2、Q3 容量／追問、Q5、Q11 累積檢查。
- 每語引擎 33 分支、70 個列印／螢幕／頁尾情境，以及實際 DOCX 檢查。
- 本輪 2 個本機暫存模板確認無 project/document 引用後清除，ZIP 備份可還原。
  同一 worker 完成整批；測試服務已還原 stock worker 並停止，其他服務不動。

## 保留失敗證據與重現邊界

`conversion-trial/` 保留直接翻譯 inline span 時丟失標記、被結構稽核擋下的試作。
最後使用兩個捕捉片語及具名 placeholder，不改翻譯工具、不維護第二套中文 Jinja。
`checker-diagnostics/word-hint/` 保留首次中文 Word 檢查器失敗；修正後只允許 Pandoc
在獨立末尾句號省略 eastAsia hint，其他文字的原有 run 屬性必須完全沿用。

`metadata-gap-prose-report.json` 綁定成品、fixture、檢查器與英文比較規則的 SHA256；
`probes/` 保存完整範圍與引擎報告，`checksums.json` 綁定本目錄所有其他檔案。
`candidate-manifest.json` 與 `rebuild-manifest.json` 為乾淨鎖定建置；後者採用 QA 修正後
commit，兩語 ZIP 及全部 43/44 個 source 檔仍逐位元相同。QA 修正沒有偷換已驗證成品。

目前只驗收上述情境。未執行 Microsoft Word，也未宣稱整篇閱讀、所有問卷分支或
Science Europe 合規已全面驗收。本機使用既有 tables-only worker，不能把此結果當作
stock／production worker 已驗收；沒有碰線上 DSW 專案，也沒有發布版本。
