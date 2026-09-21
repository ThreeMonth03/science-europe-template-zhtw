# 0.3.43：混合預算與大量資源分組整合

英文來源鎖定 `5a0c4545fc5f0d9dac09c2c92831d002b65e8f27`，中英文配對版本為
`0.3.43`，仍在 `fix/profile-pagination` 實驗分支。沒有另寫中文 Jinja；
748 組翻譯與翻譯工具版本不變，也沒有部署到正式 DSW。

本次只整合前輪已實測的三個來源檔：PDF 長表續頁名稱、混合表中的短列連頁，
以及大量資源以至多 32 筆普通列分組，避免第 33 筆起整表退回窄欄。
Word 保留原本逐格安全檢查；不符合條件的內容仍不轉換。

版本管理有兩道檢查：

- 精確撤回這三個差異後，全部來源與中英文 prepared source 都必須還原成
  0.3.42 的封存值，再繼續執行更早版本的檢查；不改寫舊測試封存。
- 新套件與[前輪原生試作](../reviews/2026-09-21-large-resource-groups/README.md)
  的全部模板內容、字型及 Word 資產相同。只允許版號、套件 ID、依公式生成的
  檔案 UUID 與來源提交時間戳記改變；輸出格式 UUID 不可變。

`scripts/check_budget_grouping_integration.py` 只驗套件，不冒充原生排版驗收。
整合後原生 PDF／Word 與 LibreOffice 預覽另由
`scripts/check_budget_grouping_native.py` 比較，結果完成後獨立封存。

尚未完成：英文 Word 大量資源的三筆短列仍會拆段跨頁；提交預覽尚未全域移除
系統漏填提示，不能當作國科會繳交版；尾頁留白、真實專案與 Microsoft Word
仍需人工驗收。這次沒有改中文語氣或刪除使用者回答。
