# 0.3.26：Word 短預算缺答欄寬

只調符合條件的 Word 表格欄寬，從用途／預算／經費來源 57/17/26 改為
49/25/26。字級、行距、段落、表格內距、提示與作者回答都保留；不把缺答
改寫為否定，也不縮短提示以塞進窄欄。

Word 入口啟用專用標記，Q15 呼叫英文共用的短預算判斷：1–3 列、短文字、
有限段落與已知標籤，而且至少一筆金額／幣別缺答。未知、長篇、多筆和完整
填答表格維持原排版。Pandoc 會丟掉段落 fact attributes，因此不在 Lua
搜尋中英文提示文字；Lua 只在 Q15 接收這個標記並調整合規三欄表格。

英文四個 prepared src 有界限變更：共用 helper、Q15 分支、Word 入口及
Word Lua。逐項移除新增內容後，必須與封存的 0.3.25 source hash 相同；
所有其他來源、731 個翻譯檔、字型、CSS 與 Word reference 不變。
中文由原翻譯樹產生，不新增或手改中文 Jinja，也不用 LLM 改寫答案。

先以凍結的原生 DOCX 複本試 49/25/26 和 46/28/26，保留未採用方案。
49/25/26 已使 partial 中文缺幣別提示 2 → 1 行、英文 3 → 2 行，仍是
四頁；採用較小的欄寬調整。試算不是原生 DSW 驗收。

接著用固定 Pandoc 跑 46 組中英文 Jinja／AST／DOCX 探針，核對只改
column grid，原有 PDF、長表格與 Q8／Q9 探針繼續執行。原生前後對照
另行保存；LibreOffice 預覽不能代替 Microsoft Word 實機驗收。

兩個 repo 工作分支皆為 `fix/word-short-budget-widths`，英文與中文版本
為實驗性 0.3.26，中文鎖定英文完整 commit。這不是新的永久相容線。
worker 延用 tables-only 映像，沒有採用上一輪的字型修補實驗；本機診斷
override 僅開啟 `PYTHONFAULTHANDLER`，若再當機先保存 stack trace。
不動線上 DSW、不合併 main、不建立正式 tag 或 release。
