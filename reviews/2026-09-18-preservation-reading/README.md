# 0.3.39：Q11 Word 短摘要接回模板

中文提交預覽的 Q11 題目／短摘要由第 4／5 頁，改為同在第 5 頁。
這次是實際 DSW 原生 DOCX，不是修改成品後的排版示意；Word 頁面仍由
LibreOffice 25.2.3.2 預覽，不代表 Microsoft Word 已驗收。

## 直接看成品

| 語言／模式 | 新版 Word | Word 預覽 PDF | 原生 PDF（未改 PDF 樣式） |
| --- | --- | --- | --- |
| 中文提交預覽 | [DOCX](after/native/profile-partial-submission-chinese.docx) | [PDF](after/word-preview/profile-partial-submission-chinese.pdf) | [PDF](after/native/profile-partial-submission-chinese.pdf) |
| 中文內部檢核 | [DOCX](after/native/profile-partial-review-chinese.docx) | [PDF](after/word-preview/profile-partial-review-chinese.pdf) | [PDF](after/native/profile-partial-review-chinese.pdf) |
| 英文提交預覽 | [DOCX](after/native/profile-partial-submission-english.docx) | [PDF](after/word-preview/profile-partial-submission-english.pdf) | [PDF](after/native/profile-partial-submission-english.pdf) |
| 英文內部檢核 | [DOCX](after/native/profile-partial-review-english.docx) | [PDF](after/word-preview/profile-partial-review-english.pdf) | [PDF](after/native/profile-partial-review-english.pdf) |

[修正前第 4 頁](visual/before-chinese-submission-p4.png)、
[修正後第 5 頁](visual/after-chinese-submission-p5.png)。
完整前版樣張在 `before/`；全空與部分漏填對照也包含兩種模式、兩種語言。

## 改了什麼

英文共用來源新增一個有界的 Word filter，接在既有 filter 後面；中文依原流程轉換。
短而純文字的 Q11 資料集名稱與固定摘要合成一段，名稱加粗，以換行分隔。
新增樣式只讓該段自身不拆頁，不強迫整個 Q11 或後續清單同頁。
名稱上限 80、摘要上限 360 個寬度單位；U+2E80 以上字元各算兩個。

有自由回答、漏填區塊、複雜格式、未知屬性、過長內容時不套用。
合格的資料集名稱不再是 Heading5；原有書籤保留，Q11 Heading3 不變。
這是明列的導覽層級取捨，不是聲稱 Word 結構完全沒改。
全部 Jinja、既有 Lua、PDF CSS、原有字型／樣式和 748 組譯文維持不變。

## 實際驗證結果

- 3 組合成問卷 × 2 種模式 × 2 種語言，共 12 組前後對照。
- 本輪重產 60 份原生 HTML／PDF／DOCX、20 份 Word 預覽；另沿用前輪
  `profile-partial` 的 12 份原生基準與 4 份 Word 預覽。來源收據逐一核對。
- 180 組題目 HTML 比較全部一致。Word 正文 XML 只允許指定的合段、名稱加粗、
  一個換行與該書籤搬移；其餘文字、格式、連結及書籤均保留。
- 4 組 `profile-partial` 各合併一段；中文提交 Q11 `[4,5] → [5,5]`。
  其他三組題目與摘要仍同頁；四份 Word 都維持 6 頁。
- 8 組全空／部分漏填對照不合段，Word 正文 XML 與非封面文字座標一致。
  全空各 3 頁、部分漏填各 7 頁；不強行壓縮或刪掉缺答內容。
- 全部 12 組原生 PDF 正文文字、非封面文字座標及頁數相同。
  1,334 個新版 Word 正文段落在預覽中找到；指定文字框內未偵測到行重疊。
- 中英文準備後來源各跑 41 組實際 Pandoc AST／DOCX 邊界測試。
  名稱、摘要的長度邊界、同名多筆、混合合格／不合格、自由回答及巢狀假結構均納入。

完整數值與雜湊見 [native-comparison.json](provenance/native-comparison.json)。
文字座標相同不等於全部像素相同；人工只檢視四份目標 Word 的 24 頁概覽及
中文目標頁細圖，不宣稱每個對照案例都已逐頁人工驗收。

## 未解項目

中文檢核 Word 的 Q5 引導句仍跨頁；短預算區塊仍可能與前文分離。
本輪不處理 Q15 PDF 修正，也未改中文語氣與標點前空白。
前輪獨立 PDF 重播曾出現字型基準差異；本輪原生 PDF 比較相同，不能據此推論
前輪差異的原因已查明。詳見前輪的 [分頁實驗](../2026-09-18-profile-pagination/README.md)。
提交預覽仍只切換已明列的提示，不能直接視為任意國科會計畫的正式繳交模板。

## 版本與環境

兩 repo 工作分支均為 `fix/profile-pagination`。英文來源
`11c05c3b77ec21fc0fa9a9d12c165876e1e78d26`；中文候選來源
`1e86b2eb6b72260c072a60fdc34934b2d47c8e2d`，兩者均為 0.3.39。
後續 QA 文件／測試提交不改套件輸入；未合併 main、未 tag 或正式部署。
review／submission 是同一套件的輸出選項，不是兩條永久分支。

使用本機 DSW 4.30 與已記錄的 tables-only worker；沒有套用實驗字型修補。
第一批候選 HTML 因清理尚未完成、配額不足而失敗，保留在 `diagnostics-quota/`。
待前版兩個自有模板完成零引用檢查及 ZIP 備份驗證後清除，另開資料夾完整重跑。
新版兩個自有模板也已清除，保留全部 ZIP、樣張及 volumes；未調整配額。
worker 已還原原廠映像並停止四個本機測試服務；正式 DSW 未動。

`question-content/` 只存題目 DOM 與原始 HTML 雜湊，不重複提交大份內嵌字型。
完整 HTML 與套件仍留在本機 `outputs/`；`reproduce/` 保存比對程式及來源鎖。
這是限定範圍的修正證據，`release_acceptance` 仍為 false。
