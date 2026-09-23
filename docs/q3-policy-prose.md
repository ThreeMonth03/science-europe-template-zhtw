# 第 3 題固定政策共用接句（0.3.51）

將[已驗證原型](../reviews/2026-09-23-q3-shared-policy-prose/README.md)的最小差異
接回英文：Q3 capture／call 與 `metadata-prose.html.j2`。只有每個邊界都是
中文句號接 BMP 漢字的 2–3 段純文字固定政策才合併；含英文或混合邊界、
原文、缺漏提示、未知結構時，整段原樣回退。沒有全域刪空白或改寫使用者答案。

仍使用鎖定的既有翻譯工具，不另維護中文 Jinja。中英文配對升到 0.3.51；
`pipeline.yml` 鎖定完整英文 commit。775 份翻譯、CSS、字型、Word 樣式、
格式 UUID 和轉換步驟都保留。

新 gate 先驗證實際新版全部來源、資產、套件 metadata 與答案矩陣，再提供
精確 0.3.50 舊版視圖供既有回歸測試使用。舊 fixture、雜湊與封存證據不改。
[本輪整合驗證](../reviews/2026-09-23-q3-policy-prose-integration/README.md)完成：
最終兩次乾淨建置相同，英文 281／中文 481 項完整測試與其餘 54 項本機
workflow 檢查通過。原始測試失敗與完整重跑分別保存；tests-only 修正後未重跑
整套 workflow，而以精確 commit 差異、相同套件及新版 gate 綁定其餘結果。
40 組實際套件重產的 168 頁 PDF／167 頁 Word 預覽逐頁重現已接受原型，另抽看九頁。

這次不改善 Word 既有行距、中文語氣或全形標點字寬。LibreOffice 預覽不代表
Microsoft Word 驗收，本機 workflow 不代表 GitHub Actions 執行或部署。
