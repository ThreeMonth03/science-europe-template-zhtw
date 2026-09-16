# 0.3.25：部分漏填的短預算表與整份 PDF

中文 partial 原生 PDF 從 5 頁減為 4 頁，短預算表不再單獨留在稀疏尾頁。
缺幣別提示中文 2 → 1 行、英文 4 → 2 行；英文整份仍是 5 頁，未宣稱
其尾頁留白已解決。這次不改中文措辭，不改原始回答或隱藏缺答。

先看 [中文前版](before/native/partial-chinese.pdf) →
[中文新版](after/native/partial-chinese.pdf)，以及
[英文前版](before/native/partial-english.pdf) →
[英文新版](after/native/partial-english.pdf)。
混合漏填：[中文 PDF](after/native/budget-mixed-gaps-chinese.pdf)、
[英文 PDF](after/native/budget-mixed-gaps-english.pdf)。
Word 控制：[中文](after/native/partial-chinese.docx)、
[英文](after/native/partial-english.docx)。

## 原生比較

七組中英共 42 個原生輸出（14 HTML、14 PDF、14 DOCX），另有 14 份
LibreOffice 預覽。混合漏填／八筆預算先以真正 0.3.24 補產 12 個基準
輸出；其他基準取自前輪保留的 0.3.24。輸入配方、事件與 KM hash 相同。

所有十五題 HTML 完全相同；PDF 題目正文、缺答與自填段落保留，沒有新增
頁數，非目標控制組的正文分頁完全相同。所有 Word 本文 XML、樣式、外部
連結與預覽頁數不變。漏幣別的長回答仍保留 60 段、5000、第二筆 0 TWD
及續頁資源資訊。詳見 `after/short-budget-report.json`。
partial 的兩個培訓清單圓點由引擎在每頁最後繪製，raw 抽取順序會隨表格
移頁改變；比對先核對兩個圓點與清單行的座標、數量及內容，再恢復其視覺
順序。沒有刪掉所有圓點或放寬作者原文、標點的相同比對。

| 案例 | EN PDF 前 → 後 | ZH PDF 前 → 後 | EN / ZH Word 頁數（不變） |
|---|---:|---:|---:|
| empty | 4 → 4 | 3 → 3 | 3 / 3 |
| negative | 4 → 4 | 3 → 3 | 3 / 3 |
| personal-transfer-complete | 9 → 9 | 8 → 8 | 7 / 8 |
| partial | 5 → 5 | 5 → 4 | 4 / 4 |
| budget-long-no-currency | 10 → 10 | 9 → 9 | 9 / 10 |
| budget-mixed-gaps | 8 → 8 | 7 → 7 | 7 / 8 |
| budget-many | 9 → 9 | 8 → 8 | 8 / 8 |

## 變更範圍與版本

英文 `src/budget-reading.html.j2` 增加保守判斷：1–3 列、原有預算缺答、
短文字、有限段落與已知 HTML 才加 PDF 專用 class。未知／長／複雜內容
回到原版型；已有長預算排版的表格不改。CSS 只調欄寬與內距，字級、行距
不變。這些條件不是通用 HTML 驗證器，也不能保證所有任意輸入的頁高。

中英各 42 組短表格原樣保留／邊界測試、32 組既有長表格測試、13 組空白
Q15 引擎測試通過。731 個翻譯檔與其餘 prepared src 不變；去掉新增 helper
與 CSS 後，與 0.3.24 逐位元一致。Q15 的問題與回覆邏輯沒有再改。

兩個 repo 同用 `fix/short-budget-reading`；中文仍由既有翻譯樹建置，
`pipeline.yml` 鎖英文 commit 與工具 commit，不另養一套中文 Jinja。
未升級官方 upstream、合併 main、建立 tag 或發布。未來 upstream 若改
Q15 的捕捉結構，需要重跑兩語言與各格式測試，不能只靠 Git 無衝突。

## 保留的未採用方案與限制

第一版原生 partial PDF 印出 `<table ...>` 文字而失去表格，已拒收並保存於
`diagnostics/rejected-native`。原因是 Jinja autoescape 把新增的固定開頭
標籤跳脫；修正版只對該固定字串使用 safe，不將使用者輸入改為安全 HTML。
42 組測試現在同時跑自動跳脫開／關，另測作者標題仍被跳脫。第一版 CI
通過不足以證明成品可用，修正版另以完整七組原生輸出重測。

`diagnostics/width-trials` 保留 40/29/31 欄寬：提示雖變短，英文用途被擠窄，
表格反而更高。49/25/26 加小幅內距調整才進原生驗證。這些試算用凍結
HTML 和固定引擎，不冒充 DSW 原生輸出；原生結果在 `before/after`。

仍是局部實驗，不是所有問卷分支、Science Europe 實質內容、整份中英語氣
或 Microsoft Word 實機驗收。英文稀疏尾頁與 stock worker 的 Markdown
表格問題仍是後續工作／發布門檻。字型替代也可能改變 Word 分頁。
Word 的短預算缺幣別提示仍有窄欄折行（這批預覽中文兩行、英文三行）；
本輪只證明 Word 沒退步，不代表這個閱讀問題已修好，列為下一步。
修正版完成第 41 份輸出後，本機 patched worker 發生一次非 OOM 的 exit 139。
保留狀態後重啟相同映像，原等待中的最後一份 Word 正常完成，未改套件或
略過案例。這是故障復原，不是根因修復；`after/worker-exit-139.json` 與
`after/worker-recovery.json` 保留紀錄，runtime 穩定性仍是發布前待查問題。

僅操作本機合成資料；沒有讀取 keyring 或修改線上 DSW。前版／新版各兩個
暫存模板，以及拒收版的兩個暫存模板，核對無引用後清理，ZIP 備份可重建；原版 worker 已恢復，四個
pilot 服務停止，沒有刪除 volumes。完整 HTML 留在本機並記 hash，repo
保存題目摘錄、原生 PDF/DOCX、預覽、檢查與來源紀錄。
