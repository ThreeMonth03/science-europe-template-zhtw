# Q2 中英文格式與資料量閱讀對照（0.3.31）

本輪通過限定案例的產檔與內容比較，**不是整份 DMP 或 Microsoft Word 正式驗收**。
英文來源 `1ba2d826927e9b35f0dec1e6f83700aed758d603`，中英文工作分支皆為
`fix/format-reading`。中文仍由英文及翻譯樹產生，不另養一份 Jinja 邏輯。

## 先看第 3 頁

- 四筆格式：[中文 PDF](after/native/format-reading-chinese.pdf)、[英文 PDF](after/native/format-reading-english.pdf)。
- 部分漏填：[中文 PDF](after/native/format-partial-chinese.pdf)、[英文 PDF](after/native/format-partial-english.pdf)。
- 自填原因：[中文 PDF](after/native/format-rich-chinese.pdf)、[英文 PDF](after/native/format-rich-english.pdf)。
- 可編輯 Word：[中文](after/native/format-reading-chinese.docx)、[英文](after/native/format-reading-english.docx)。
- Word 排版預覽：[中文](after/word-preview/format-reading-chinese.pdf)、[英文](after/word-preview/format-reading-english.pdf)。
- [修改前中文 PDF](before/native/format-reading-chinese.pdf) 可對照同一批回答。

## 有效改善與保留界線

例如「此格式為標準化格式。此格式適合長期封存。」合成
「採用標準化格式，適合長期封存。」；檔案數和平均大小皆有值時合成一句，
並縮短總量／少量的固定說明。減少重複主詞和句號，不變更使用者寫的段落。

部分缺答仍逐筆顯示已填項目與待補項目。只有「檔案數」不會被當成同時
知道「平均大小」；0 與 0.0001 原樣保留，不用乘法補寫總量。
不適合封存、未規劃轉換及非標準化原因仍有獨立意義，不合併成推測答案。

## 實際檢查

五組案例 × 中英文 × HTML/PDF/DOCX，前後各 30 個原生輸出；前後各
10 份 LibreOffice Word 預覽。全部使用同輸入、同知識模型及同一個
tables-only worker；其映像、啟動時間與 restart count 前後一致。

| 案例 | PDF 英／中頁數（前＝後） | Word 預覽英／中頁數（前＝後） |
| --- | --- | --- |
| 非標準格式＋自填原因 | 6／6 | 6／6 |
| 四筆部分缺答 | 7／6 | 6／6 |
| 四筆完整格式 | 6／6 | 6／6 |
| 空白 | 4／3 | 3／3 |
| 明確否定 | 4／3 | 3／3 |

- [完整產檔比較](after/format-reading-report.json)：15 題 HTML 只准 Q2 指定固定句變更；全部自填區塊與缺答標記保留。
- Word 摘要仍一筆一段，修改範圍以完整句對限制；保留字元的樣式逐字核對，其餘正文 XML、編號與外部連結不變。
- PDF 全文按指定句對比較，保留標點與順序；只在核對實際清單文字／縮排後排除頁尾繪製的清單符號。
- 空白與否定控制組的 PDF／Word 正文幾何位置不變。所有案例頁數不增加、回答未截斷。
- [來源與翻譯界線](probes/format-reading-scope.json)：中英 528 組 Q2 DOM 比較；Q11 的 548 組分支與 128 組缺答組合繼續檢查。
- 734 個翻譯單位中，原 732 組保留 729 組、替換 3 組、另增 2 組；Q2 以外翻譯檔逐位元不變。樣式、Lua、字型與 Word 參考文件不變。

## 視覺觀察與尚未解決

已查看中英文原生 Q2 三類樣張及 Word 完整／部分缺答第 3 頁，並保存頁面圖。
多筆格式摘要更精簡，未看到 Q2 壓字或遺失；部分缺答仍較長，不能為了短而刪提示。
這一輪沒有全文件每頁逐字人工驗收：全篇採自動內容、頁界、Word 段落檢查，
視覺聚焦 Q2。Word 缺答仍是普通段落，而非 PDF 色框；這是既有差異，不是已修好。
中文全篇標點間距、Q3／Q5 的其他固定句與跨題閱讀節奏仍待獨立改善。
英文既有字型度量框交疊的診斷數量未增加，不能把度量框當成實際字形重疊。

## 可追溯與清理

`candidate-manifest.json`、`rebuild-manifest.json`、前後產檔回條及
`checksums.json` 綁定來源、套件、測例與樣張。兩次乾淨打包與新版產檔用 ZIP 一致：

- EN：`c1f98ff6df8590a1be5e3822eddafa48284b5a4a2e3b1eb73888d99b9a182d77`
- ZH：`eebb3d757b52cda3fcf15e7f7d67c5836917bcfcb93004620f90c405b7c19ea0`

開發中檢查器遇到的混合清單符號／CJK 字型提示，以及基線預覽啟動過早的
中止紀錄，見 [診斷記錄](diagnostics/checker-development.md)，沒有混稱初輪全通過。
四個本輪本機暫存模板已在確認無引用、ZIP 備份後刪除；原生 worker 已復原，
四個 pilot 容器已停止，資料卷及備份保留。未存取正式 DSW 站台。

CI 是另外一層測試，不取代原生樣張；最後執行狀態見
[英文分支 CI](https://github.com/ThreeMonth03/science-europe-template/actions?query=branch%3Afix%2Fformat-reading)、
[中文分支 CI](https://github.com/ThreeMonth03/science-europe-template-zhtw/actions?query=branch%3Afix%2Fformat-reading)。
