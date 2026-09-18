# 0.3.37 整份文件稽核

本輪只做閱讀稽核，不改模板／翻譯／lock／版號。完整證據見
[稽核報告](../reviews/2026-09-18-whole-document/README.md) 與
[83 頁逐頁概覽紀錄](../reviews/2026-09-18-whole-document/page-ledger.md)。

先看實際漏填案例：

- [中文 PDF](../reviews/2026-09-18-whole-document/native/metadata-partial-chinese.pdf)／[DOCX](../reviews/2026-09-18-whole-document/native/metadata-partial-chinese.docx)。
- [英文 PDF](../reviews/2026-09-18-whole-document/native/metadata-partial-english.pdf)／[DOCX](../reviews/2026-09-18-whole-document/native/metadata-partial-english.docx)。
- [英文 Word 孤立章節標題](../reviews/2026-09-18-whole-document/visual/metadata-complete-english-word-orphan-p3.png)。
- [中文 PDF 預算尾頁](../reviews/2026-09-18-whole-document/visual/metadata-complete-chinese-budget-tail-p6.png)。

優先順序：Q6 已啟用的存取控制追問漏填提示 → Q8 權利歸屬缺答提示 → Word
章節標題連頁／中文 PDF 短預算分頁 → 中英模板敘事與中文語氣。
不要把全部問題塞進同一版，也不因要潤飾中文而另養一套 Jinja。

`metadata-complete` 只表示特定後設資料追問有答，不是完整合格 DMP；
`narrative-long` 的 80 段重複來自 fixture，不是模板自行重複。
前兩案例重用同一組 0.3.37 ZIP 的成品；本輪另產生長文案例的六個原生輸出。
Word 僅驗 LibreOffice 預覽；真正 Microsoft Word、部署 worker、自然完整研究案例及
領域審查仍是發布門檻。

分支：`review/whole-document-0.3.37` 從中文 `fix/metadata-gap-prose` 分出，
英文來源仍鎖定 `0730b11c4027fcc020c441a3c36264d85649321c`。
這是短期證據分支，不另定模板版本，也不建立新的永久支援線。
目前 workflow 的 push filter 不含 `review/**`，此分支推送不會觸發完整候選建置；
其本機單元測試與原實作分支的 CI 狀態分開記錄，不冒稱本分支 CI 已通過。
