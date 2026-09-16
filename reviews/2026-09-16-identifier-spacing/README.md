# 0.3.28：中文識別碼固定句的空格

第 13 題原本的「持續識別碼將由資料儲存庫指派。 資料儲存庫將確保……」
改為「持續識別碼將由資料儲存庫指派。資料儲存庫將確保……」。
只移除輸出層額外插入的西文空格，句號、字型本身的標點寬度與全部文字保留。
這是局部排字修正，頁數沒有減少，也不是全篇中文空白已修好。

## 看成品

- 中文 PDF 第 6 頁：[前版](../2026-09-16-identifier-concise/after/native/budget-mixed-gaps-chinese.pdf) → [新版](after/native/budget-mixed-gaps-chinese.pdf)。
- 中文 Word 預覽第 7 頁：[前版](../2026-09-16-identifier-concise/after/word-preview/budget-mixed-gaps-chinese.pdf) → [新版](after/word-preview/budget-mixed-gaps-chinese.pdf)，[DOCX](after/native/budget-mixed-gaps-chinese.docx)。
- 漏填追問：[中文 PDF](after/native/identifier-followups-chinese.pdf)、[中文 Word 預覽](after/word-preview/identifier-followups-chinese.pdf)。四個管道的已知回答、否定與待補提示仍分別呈現。
- 英文對照：[PDF](after/native/budget-mixed-gaps-english.pdf)、[Word 預覽](after/word-preview/budget-mixed-gaps-english.pdf)、[DOCX](after/native/budget-mixed-gaps-english.docx)。
- 空白問卷：[中文 PDF](after/native/empty-chinese.pdf)、[英文 PDF](after/native/empty-english.pdf)。15 題與待補提示保留。

## 原因與範圍

PDF 的共用 CSS 用 `p::after` 插入空格；Word 的 Lua 在合併固定句時另外
插入 Pandoc Space。第 13 題可移除這兩種「新增的分隔符」，因為相鄰段落
只有固定政策敘述、中文句號已分隔完整句子，而且中間沒有模板字面空白。
後一項由 1136 組中英分支核對，不能只憑樣張推測。

CSS 只對 `zh-Hant` 的 `identifier-arrangement.dataset-policy` 生效。
Word 只在同一種區塊、左側為中文句號且右側為漢字時不再插入空格；不刪
已有 inline，不全域改「。 空格」。管道編號／儲存庫種類之間的空格保留。
所有 Jinja、731 個翻譯檔、字型、Word reference、字級、行距與段落間距
都與 0.3.27 相同。中文仍走既有翻譯流程，沒有第二套中文 Jinja。

Q1／Q2／Q5／Q10／Q11 的部分固定句另有模板字面換行空白；不能假設移除
CSS 產生的空格就會全部改善。它們未套用這次規則，後續需連同語意段落
邊界、自由回答與漏填提示逐組處理。

## 驗證

八組中英共 48 個原生 HTML／PDF／DOCX 及 16 份 LibreOffice 預覽通過。
五組中文案例合計在 PDF、DOCX 各移除 10 個指定接點空格；其他字元不變。
11 組不受影響的對照（8 組英文，以及中文 partial／empty／negative）
連 PDF 與 Word 預覽的文字座標都完全相同。

| 案例 | EN PDF／Word 頁數 | ZH PDF／Word 頁數 |
|---|---:|---:|
| budget-mixed-gaps | 8／7 | 7／8 |
| identifier-followups | 9／8 | 8／8 |
| partial | 5／4 | 4／4 |
| empty | 4／3 | 3／3 |
| negative | 4／3 | 3／3 |
| personal-transfer-complete | 9／7 | 8／8 |
| budget-long-no-currency | 10／9 | 9／10 |
| budget-many | 9／8 | 8／8 |

頁數前後全部相同。HTML 正文完全相同；Word 其餘正文 XML、保留字元格式、
段落樣式、表格、連結、字型及編號不變；另檢查 2288 個預覽正文段落。
PDF 正文比對保留水平空格及標點，只容許指定接點差異和折行／頁面分隔；
未用全域去空白掩蓋錯誤。混合缺答與追問的中文 PDF／Word 頁面另行目視。

13 組固定引擎探針涵蓋指派者、肯定／否定解析與英文、標題、其他政策及
自由回答對照；來源檢查可精確還原 0.3.27 CSS／Lua，候選與乾淨重建 ZIP
相同。這些測試不代表所有可能問卷或 Microsoft Word 實機都完成驗收。

最初原生檢查程式誤將 Path 傳給需要文字的 helper，因此中止；失敗工具、
未完成報告與錯誤原因保存在 `diagnostics/`，修正後用同一批成品重驗。
原始 HTML 較大，留本機並記錄 hash；本目錄保存全部題目摘錄與 sidecar。
完整前版文件沿用 [0.3.27 審閱](../2026-09-16-identifier-concise/README.md)，不重複複製。

## 版本與環境

兩個 repo 在短期 `fix/identifier-cjk-spacing`，中文鎖英文完整 commit
`b7b80d9db3a47685223aa2aabb273e37d81d4c39`。仍為實驗版，未 merge main、
未 tag、未正式 release。worker 沿用 tables-only，沒有加入字型修補實驗。
48 份輸出期間沒有 container restart；不因此宣稱歷史 exit 139 已解決。
確認零引用與 ZIP 備份後，已清理本輪兩個本機暫存模板，恢復 stock worker
並停止四個服務，volumes 保留；未使用線上 DSW、keyring 或真實問卷。

稀疏尾頁、整篇閱讀密度、其他固定句的空白與中文措辭仍需改善。
`checksums.json` 覆蓋本目錄其他檔案；`after/identifier-spacing-report.json`
列出完整檢查範圍與來源 hash。不要把 CI 通過當成全篇視覺驗收。
