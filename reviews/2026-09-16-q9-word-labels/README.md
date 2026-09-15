# 0.3.23：Q9 Word 資料集名稱與倫理說明連頁

本輪只改共用 Word Lua，不改 Jinja、PDF CSS、字型、reference 樣式或任何
一個翻譯檔。731 個翻譯檔完全保留；沒有新增中文專用分支邏輯。

先比較 [原本英文 Word 預覽](before/word-preview/personal-transfer-complete-english.pdf)
與 [修正後英文 Word 預覽](after/word-preview/personal-transfer-complete-english.pdf)，
以及 [修正後中文 Word 預覽](after/word-preview/personal-transfer-complete-chinese.pdf)。
原生 DOCX：[英文](after/native/personal-transfer-complete-english.docx)／
[中文](after/native/personal-transfer-complete-chinese.docx)。
原生 PDF：[英文](after/native/personal-transfer-complete-english.pdf)／
[中文](after/native/personal-transfer-complete-chinese.pdf)。

## 本輪驗證

原本英文 Q9 名稱在第 4 頁、第一項倫理說明在第 5 頁；修正後名稱與最後一項
說明同在第 5 頁。不是刪字、合併作者段落或強制整份清單同頁。


- 六組中英文，12 份 PDF、12 份 DOCX、12 份 HTML 與 12 份 Word 預覽。
  全空、否定、部分漏填、8 筆資料集及 30 段作者回答都有實際輸出。
- 新增案例先用真正的 0.3.22 套件輸出，不以新版模擬舊版；其餘案例使用
  保存的上一輪成品。原本失敗紀錄保留於 `before/original-q9-failure.json`。
- 15 題 HTML 完全相同；原生 PDF 正文與頁數不變。Word 只允許 Q9 合格名稱
  從 Compact 改成既有連頁樣式，並把兩句固定倫理說明合為一段，保留兩句完整
  文字、順序、標點。單項說明和自由回答不合併；所有其他段落 XML、連結及 styles.xml 不變。
- 短名稱與各自倫理說明在實際 Word／PDF 同頁；Q8 的原生連頁檢查也通過。
  一項漏填不會被補成「不包含」，兩項都漏填的既有提示仍保留。
- 29 組固定 Pandoc AST／實際 DOCX 探針，含邊界、混合、長篇與複雜拒絕形狀。
  乾淨候選與重建 ZIP hash 相同，來源範圍和翻譯不變證據在 `probes/`。
- 第一版只加連頁，英文完整 Word 卻從 7 頁增為 8 頁、把整組預算推到稀疏
  新頁。保留於 `rejected-style-only/`，沒有覆寫為成功樣張。最後版採兩句
  固定說明緊湊成段；全部案例均檢查整份 Word 沒有比 0.3.22 增頁。

| 案例 | EN PDF / Word 預覽 | ZH PDF / Word 預覽 |
|---|---:|---:|
| personal-transfer-complete | 9 / 7 | 8 / 8 |
| empty | 4 / 3 | 4 / 3 |
| negative | 4 / 3 | 3 / 3 |
| q9-partial-flags | 9 / 8 | 8 / 8 |
| q9-many-datasets | 11 / 9 | 10 / 10 |
| q9-long-purpose | 10 / 8 | 9 / 9 |

## 尚未驗收的範圍

這不是整份 DMP 的理想版面認證。短預算提示折行、空白中文 PDF 尾頁留白、
長／複雜名稱、其他種類標籤與語氣仍需逐一檢視。部分漏填本輪保留既有表達，
不代表已為每個缺項增加新提示。Word 預覽使用 LibreOffice，尚未完成 Microsoft
Word 實機驗收。stock worker 的 Markdown 表格仍是正式發布門檻。

本機隔離測試使用合成資料，沒有讀取 keyring 或操作線上 DSW。前版對照與新版
及未採用版各自建立的暫存模板已清理，ZIP 備份保留可重建；原版 worker 已恢復，
四個 pilot 服務已停止，沒有刪除 volumes，也沒有合併 main、tag 或 release。
`question-content/` 僅擷取原生 HTML 題目，完整 HTML 留在本機 runtime 目錄，
其 hash 可供核對；不是另外渲染的理想樣張。
