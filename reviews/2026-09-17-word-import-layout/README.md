# 0.3.34 Word 匯入診斷（未修好、不是新版模板）

中文 Q5 原生 DOCX 的政策與限制仍分在第 3／4 頁。本輪不修改模板或譯文，
不發布版本，只保存可重跑的診斷及未採用方案。
完整解釋與重跑命令見 [診斷說明](../../docs/word-import-layout.md)。

## 最有用的對照

- 原生來源：[中文 DOCX](../2026-09-17-storage-context-pagination/after/native/metadata-partial-chinese.docx)、
  [英文 DOCX](../2026-09-17-storage-context-pagination/after/native/metadata-partial-english.docx)。
- 原生中文 Word 預覽：[第 3 頁](visual/native-chinese-page3.png)、[第 4 頁](visual/native-chinese-page4.png)。
- 記憶體內重新指定政策段原有連頁值：[PDF](memory-and-reopen/chinese/same-policy.pdf)、
  [第 4 頁](visual/memory-chinese-page4.png)；Q5 暫時同頁，**不是原生／可交付修正版**。
- 另存重開：[PDF](memory-and-reopen/chinese/same-policy-reopened.pdf)、
  [第 3 頁](visual/reopened-chinese-page3.png)；Q5 再次跨頁。
- 第二引擎：[中文 PDF](engine-comparison/metadata-partial-chinese.pdf)、
  [第 2 頁](visual/engine26-chinese-page2.png)、[第 4 頁](visual/engine26-chinese-page4.png)；
  Q5 同頁但全篇多一頁，前文亦變動，未採用。
- 英文：[原生第 3 頁](visual/native-english-page3.png)、
  [第二引擎第 3 頁](visual/engine26-english-page3.png)；這份案例的 Q5 均同頁。

## 證據範圍

`memory-and-reopen/` 各語言含 11 個 PDF、2 個另存的診斷 DOCX 及 report。
九種操作使用原生來源另開唯讀 Writer session；另兩次明確改用衍生 DOCX 重開。
18 個直接／記憶體 PDF 的全文擷取相同，四個另存重開 PDF 則各增加 13 個
U+F020 擷取字元；報告保留嚴格全文比較不相同，沒有刪除這些字元掩蓋差異。

`engine-comparison/` 含 20 個未修改原生 DOCX 的第二引擎預覽及 report。
原引擎樣張仍在上一輪 `after/word-preview/`，每份輸入／輸出以 SHA256 綁定。
英中各十個案例，包含空白、漏填、明確否定、冷儲存及長預算：英文頁數不變；
中文各增加一頁。20 份正文段落保留；19 份嚴格全文擷取相同，中文長預算的
重複表頭位置變動保留為全文比較 false。此項不是新 DSW PDF 測試。

所有實驗均為公開合成案例，未用正式站憑證或修改正式 project。模板、翻譯、
ZIP 與原生 DOCX 不變。沒有測試 Microsoft Word；仍不得正式發布。

`reproduce/` 保留實際工具原碼，需搭配 repo 現有 helper 與診斷說明中的環境；
不是獨立可執行套件。`checksums.json` 記錄本目錄其他全部檔案。
