# 0.3.21：中英文個資追問、缺答與原段落

這是同一組已鎖定候選套件的 8 案例 × 2 語言驗證，共 16 份原生 PDF、16 份
DOCX、16 份 HTML；另產生 16 份 LibreOffice Word 預覽。不是 Microsoft Word
或整份 DMP 的正式驗收，也不是法律合規認證。

先看 [中文追問漏填 PDF](native/personal-followups-empty-chinese.pdf)、
[英文追問漏填 PDF](native/personal-followups-empty-english.pdf)、
[中文傳輸措施漏填 PDF](native/personal-transfer-missing-chinese.pdf)、
[英文傳輸措施漏填 PDF](native/personal-transfer-missing-english.pdf)。
有段落和清單的 [中文完整 PDF](native/personal-transfer-complete-chinese.pdf)、
[英文完整 PDF](native/personal-transfer-complete-english.pdf)，及對應
[中文 Word](native/personal-transfer-complete-chinese.docx)／
[英文 Word](native/personal-transfer-complete-english.docx) 可一起比較。

## 本輪修正

- Q7 追問漏填仍保留明確提示；選「其他法律依據」但沒填細項不再產生半句。
- 跨境傳輸「是但措施缺答」保留傳輸意向；明確「否」如實呈現，與漏填分開。
- 自由回答保留原段落、清單、強調與連結；Markdown 區塊不再巢狀放進段落。
- Q9 不把 Explore 當成完成評估，不自行宣稱公共利益高於隱私；其他依據缺答
  使用完整句指向 Q7。這些是忠實呈現填答，不是代替使用者判斷法規適用性。

## 驗證範圍

原有 718 組英中句對完整沿用；5 組移除／替換與 13 組新增均列入精確差異
檢查，共 731 單位。prepared source 的變動僅 Q7、Q9；CSS、Word Lua、reference
字型、其他問題與長／短預算程式未改。英文來源 commit 與候選／重建 ZIP hashes
見 manifest。所有本輪樣張來自同一組 ZIP，沒有跨候選拼接證據。

人工抽看中英文 Q7 缺答、完整 PDF 與 Word 後，額外發現中文完整 Word 的 Q8
第一個資料集名稱在第 4 頁尾端，授權說明在第 5 頁。這個跨頁反例尚未修正，
已有 [失敗報告](known-failures/q8-list-continuity.json) 與頁面樣張；Q7 自動檢查
通過不能覆蓋這項整份文件的閱讀缺陷。不能把這批成品稱為全部驗收通過。

原生檢查涵蓋 6 節／15 題存在、題答銜接、缺答提示、頁面邊界、Q7 原文順序、
中英 fact/status/ownership 對齊，以及 Word 文字與連結保留。empty、negative、
preservation-complete 六份控制組另核對 0.3.20 題目 HTML、Word 正文／樣式／
連結及 PDF 題目頁碼不變；完整閱讀品質不能只以頁數判斷。

| 案例 | EN PDF / Word 預覽 | ZH PDF / Word 預覽 |
|---|---:|---:|
| personal-followups-empty | 8 / 7 | 8 / 8 |
| personal-transfer-missing | 8 / 7 | 8 / 8 |
| personal-transfer-complete | 9 / 7 | 8 / 8 |
| personal-transfer-no | 8 / 7 | 8 / 8 |
| personal-data-partial | 8 / 7 | 7 / 8 |
| empty | 4 / 3 | 4 / 3 |
| negative | 4 / 3 | 3 / 3 |
| preservation-complete | 8 / 7 | 7 / 8 |

## 邊界與後續

短預算窄欄仍會將「幣別尚未提供」折行，整體留白未改。其他同意程序、DPIA
與剩餘追問尚未全部稽核；Q8 清單名稱／授權說明的 Word 連頁規則優先待修。
原生輸出使用隔離本機的 Markdown-tables worker，
stock worker 表格仍是正式發布門檻；沒有讀取線上帳密或修改線上 project。
沒有合併 main、建立 tag／release 或部署。測試用暫存模板在確認無引用並保留
原 ZIP 後清理；回復 stock worker 並停止本輪四個本機 pilot 服務。

`native/` 是原生 PDF／DOCX，`word-preview/` 是 LibreOffice 預覽；
`question-content/` 是從原生 HTML 擷取的題目內容，非另一次渲染、非完整 HTML。
全文 HTML 保留在本機 runtime 目錄，其 hash 記在報告和擷取檔頭；不將嵌入字型
造成的大型 HTML 重複提交。`checksums.json` 覆蓋本審閱目錄的證據與說明。
