# Word 空節整合（0.3.50）

將已通過的 [Word 原型](../reviews/2026-09-23-word-empty-section-spacing/README.md)
接回共用英文來源，中文沿原有工具產生，不另維護中文 Jinja。
`pipeline.yml` 鎖定完整英文 commit，中英配對升至 0.3.50；775 組翻譯檔案逐位元不變。

只改 `question-spacing.lua`、`question-spacing.xml` 兩個 Word 資產。完全沒有答案的
提交節，其節標題採 3 pt／2 pt 上下間距，節內非末題與下一題連頁，保留全部原題。
不改 PDF 輸入、字型、參考 DOCX、格式 UUID、轉換步驟或使用者答案。

`scripts/word_empty_section_integration.py` 先驗證新版套件、全部來源／資產、版本與
UUID，再以實際建置的中英文資產各跑 121 個 Pandoc 邊界案例。只有驗證完成的新版
才能還原為精確舊版測試視圖，舊版所有回歸檢查保留。新資產與舊版測試分開驗證，
不是略過資產比對或更換舊版預期結果。

配對建置、完整本機 workflow 及新版原生對照須另留證據；source integration 本身
不等於發布或繳交驗收。Word 預覽使用 LibreOffice，不宣稱 Microsoft Word 已驗收。
保留原型的歷史 commit、失敗紀錄及封存雜湊，不改寫舊證據。原型重播使用其鎖定
checkout，正式新版使用目前 build 與 integration 腳本。

已完成[本輪驗證與封存](../reviews/2026-09-23-word-empty-section-integration/README.md)：
兩次乾淨建置一致，英文 265／中文 472 項測試、全部 54 個本機 workflow 指令通過。
28 組原生對照的 130 頁 PDF／131 頁 Word 預覽重現原型，另抽看八頁；775 組翻譯不變。
這份記錄不等同 GitHub Actions 或 Microsoft Word 驗收，未推送或部署。
