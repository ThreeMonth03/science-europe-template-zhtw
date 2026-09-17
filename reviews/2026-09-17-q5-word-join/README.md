# 0.3.35 Q5 Word 固定說明合段：原生反例修正

原本 `metadata-partial` 中文 Word 的政策與限制說明跨頁，現在由已寫入
英文共用 Lua 的規則產出後、重新開啟 DOCX，即可完整同頁。沒有在開檔後
重設屬性、另存補救、換引擎、改字型或加入固定頁碼換頁。

| 原生 DOCX 的 LibreOffice 預覽 | 0.3.34 | 0.3.35 | 全文頁數 |
| --- | --- | --- | --- |
| 部分漏填，中文 | Q5 題目／政策／引言／兩項限制在 3,3,4,4,4 頁 | 全部第 4 頁 | 6 → 6 |
| 部分漏填，英文 | 全部第 3 頁 | 全部第 3 頁 | 6 → 6 |
| 明確否定，中英 | 全部第 2 頁 | 全部第 2 頁 | 都是 3 → 3 |

Word 只將兩個短篇、模板擁有的固定說明段合成一段，以換行分隔；上述頁碼
仍分別追蹤原有五項內容。語意資格、長度限制及長／複雜回答的原流程不變。
HTML、原生 PDF、問卷對應、744 個譯文、字型、字級和樣式均保留。

## 先看成品

- 部分漏填中文：[可編輯 DOCX](native/metadata-partial-chinese.docx)、
  [Word 預覽 PDF](word-preview/metadata-partial-chinese.pdf)、
  [原生 PDF](native/metadata-partial-chinese.pdf)。
- 中文前後頁面：[舊第 3 頁](visual/before-chinese-page3.png)、
  [舊第 4 頁](visual/before-chinese-page4.png)、
  [新第 3 頁](visual/after-chinese-page3.png)、[新第 4 頁](visual/after-chinese-page4.png)。
- 英文：[DOCX](native/metadata-partial-english.docx)、[Word 預覽](word-preview/metadata-partial-english.pdf)、
  [前](visual/before-english-page3.png)／[後](visual/after-english-page3.png)。
- 漏填與長篇：[空白中文 PDF](native/empty-chinese.pdf)、[空白英文 PDF](native/empty-english.pdf)、
  [長預算中文 PDF](native/budget-long-chinese.pdf)、[長預算英文 PDF](native/budget-long-english.pdf)。

## 驗證結果與範圍

十組合成案例 × 中英，各重產 HTML／PDF／DOCX，共 60 份原生輸出，再產
20 份使用私人 LibreOffice profile 重新開啟的預覽。案例為資料字典是／否、
部分漏填、不公開原因漏填、已填不公開原因、後設資料完整、全空白、明確否定、
儲存共享及長預算。全部頁數與 0.3.34 相同。

- [原生比較](q5-word-join-report.json)：十五題 HTML 不變；PDF 正文及座標不變；
  Word 僅 10 份合格案例有精確的兩段→一段改動，原 runs、標點、連結、編號、
  其他題目與樣式保留。所有合格 Q5 同頁，之前的正文位置不變。
- [影像對照](q5-word-join-pixels.json)：20 份 PDF 加 10 份未合段 Word，
  共 128 個正文頁在 100 dpi 影像逐位元相同。以第一題位置確認封面範圍；
  套件版號改變的封面不拿來冒充完全相同。否定案例有合段，不是假裝不變的控制組。
- [來源／翻譯範圍](probes/storage-context-scope.json)：744 個翻譯檔不變，無未翻譯單位；
  原有 Q2／Q3／Q11 與分支契約保留。
- [英文](probes/q5-word-join-engine-en.json)／[中文](probes/q5-word-join-engine-zh.json)
  各 31 組固定 Pandoc 正反例通過，涵蓋長度邊界、複雜內容與既有多項固定政策。
- 兩次乾淨建置 ZIP 相同：英文
  `2bab8d81c77a077f6cda34ad2cc59a588e6ba57c04395f114a85ed319189a059`；中文
  `3668e9621e9f833db3b1dd0f4e1923707647937e059982241eefaaa2117c0ac6`。

來源鎖定英文 `fc2d4196eeeb3716696c31f64cdd4d69eb47b681`、工具
`25e339fbdfb1d20796471055790aad6a4226b6ed`；使用 LibreOffice 25.2.3.2。
前次原生檔案及失敗檢查仍在 [0.3.34 after](../2026-09-17-storage-context-pagination/after/)，
本輪沒有覆寫舊結果。新報告以 SHA256 綁定所有前後輸入與輸出。

## 不是正式發布

只證明上述案例中的指定修正，**不是所有問卷分支、整份 Science Europe DMP、
中文語氣或 Microsoft Word 的全面驗收**。Microsoft Word 尚未實機測試。
原生產檔仍使用隔離本機的 tables-only worker 實驗，不把它當已部署的正式依賴。
60 次產檔使用同一 worker、沒有重啟；結束後還原 stock worker 並停止本機服務。
只刪本輪兩筆無引用臨時模板，ZIP 備份與本機資料卷保留；正式站、keyring 未使用。

`native/` 保存原生 PDF／DOCX 與三格式來源收據；`question-content/` 是明示截取的
原生 HTML 問題區，不冒充完整 HTML。`word-preview/` 不是 DSW 原生 PDF。
`reproduce/` 保存檢查原碼與版本鎖定，仍需 repo helpers、固定工具及本機 DSW 環境，
不是獨立安裝包；重跑必須用新目錄，不能覆寫既有證據。
`checksums.json` 覆蓋本目錄其他全部檔案。原理與維護邊界見[說明](../../docs/q5-word-join.md)。
