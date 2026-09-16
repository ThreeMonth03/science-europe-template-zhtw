# 0.3.27：識別碼說明不再重複宣告

中文混合缺答的兩段識別碼安排，在原生 PDF 和 Word 預覽都各由 **2 行變 1 行**；
英文去除同樣的重複句，仍各為 2 行。字級、行距與欄寬沒有改，整份頁數不變。

先看第 13 題：

- 中文原生 PDF 第 6 頁：[前版](before/native/budget-mixed-gaps-chinese.pdf) → [新版](after/native/budget-mixed-gaps-chinese.pdf)。
- 中文 Word 預覽第 7 頁：[前版](before/word-preview/budget-mixed-gaps-chinese.pdf) → [新版](after/word-preview/budget-mixed-gaps-chinese.pdf)，[可編輯 DOCX](after/native/budget-mixed-gaps-chinese.docx)。
- 英文原生 PDF 第 7 頁：[前版](before/native/budget-mixed-gaps-english.pdf) → [新版](after/native/budget-mixed-gaps-english.pdf)。
- 英文 Word 預覽第 6 頁：[前版](before/word-preview/budget-mixed-gaps-english.pdf) → [新版](after/word-preview/budget-mixed-gaps-english.pdf)，[可編輯 DOCX](after/native/budget-mixed-gaps-english.docx)。
- 漏填追問：[中文 PDF](after/native/identifier-followups-chinese.pdf)、[中文 Word 預覽](after/word-preview/identifier-followups-chinese.pdf)、[英文 PDF](after/native/identifier-followups-english.pdf)、[英文 Word 預覽](after/word-preview/identifier-followups-english.pdf)。

## 改什麼、不改什麼

原本「資料將取得持續識別碼。持續識別碼將由資料儲存庫指派。」在已知
指派者時只保留第二句；後一句本來已經表達會指派。其外層段落標記
`persistent-identifier`，內層 span 標記 `identifier-assigner`，兩項事實沒有
消失。解析保證仍獨立保留，不能因為有人指派就推論「一定可解析」。

指派者漏填或無法辨識時，仍顯示原肯定句及缺答／核對提示。追問案例包括：
兩項皆漏填、機構指派但不保證解析、指派者漏填且不保證解析、已知計畫
指派者但漏解析答案。不同資料集／管道不混用回答，自由回答完全不動。

只改英文 Q13 Jinja 及實驗版 metadata，沒有改 15 題題目、CSS、Word Lua、
reference 樣式或字型。中文仍由既有翻譯樹產生，731 組來源／譯文配對完全
相同；四個單位路徑因結構移動改變，其餘 727 個翻譯檔原位逐位元相同。
工具未自動遷移的三句已補回原譯文，沒有新增獨立中文 Jinja 或 LLM 改寫。

## 原生驗證

八組中英共 48 份原生 HTML／PDF／DOCX，加上 16 份 LibreOffice 預覽。
前版七組沿用已驗證的 0.3.26 原生檔；識別碼追問另以同一版凍結套件補產
六份，獨立 manifest、輸出及清理記錄保留。各案例 before／after 的回答、
事件與 KM hash 一致，不能以不同問卷比較篇幅。

| 案例 | EN PDF / Word 頁數 | ZH PDF / Word 頁數 |
|---|---:|---:|
| 混合預算缺答 | 8 / 7 | 7 / 8 |
| 識別碼追問 | 9 / 8 | 8 / 8 |
| 部分漏填 | 5 / 4 | 4 / 4 |
| 空白 | 4 / 3 | 3 / 3 |
| 明確否定 | 4 / 3 | 3 / 3 |
| 完整填答 | 9 / 7 | 8 / 8 |
| 長預算缺幣別 | 10 / 9 | 9 / 10 |
| 多筆預算 | 9 / 8 | 8 / 8 |

以上頁數前後皆相同。共 20 個 Q13 閱讀單位刪除冗餘肯定前句；其餘
14 題 HTML、缺答、否定與自由回答不變。Word 保留字元的格式、段落樣式、
其他正文 XML、表格、連結、編號及字型核對不變，另核對 2288 個預覽正文
段落。中英 1136 組分支檢查與凍結 Q13 比對通過；候選與乾淨重建 ZIP 相同。

## 失敗證據與限制

初次未 refresh 的預覽因來源位置改變被 translation audit 拒絕；refresh
後三個新標記單位暫時漏譯，已保留遷移報告並補回原譯文，正式候選沒有
未翻譯單位。

第一版 PDF 全文比對遇到清單符號在頁末繪製的抽取差異；第二版試圖處理
全篇又遇到前頁巢狀符號，皆未通過。最終只在 Q13 起的受影響頁處理已
驗證的尾端符號：逐一核對符號所在首行、數量、縮排，禁止含作者字面
項目符號的案例套用。此前頁面及其巢狀符號不正規化，其他字元完整比較。
兩版失敗報告／工具、第三版四份通過及最終十六份通過分開保存。

這不是全篇理想 DMP 或 Microsoft Word 實機驗收。中文混合缺答尾頁仍較空，
英文長固定敘述與中文句間空白仍有改善空間，不能用這次局部改善宣稱全部
閱讀問題已解決。原生 PDF 與 Word 是不同版面，不承諾兩者頁數一致。

本輪 tables-only worker 沒有 container restart，未混入字型修補實驗，亦不
宣稱歷史 exit 139 根因已修復。確認零引用與 ZIP 備份後清理本輪四個暫存
模板，恢復 stock worker 的 immutable image ID 並停止四個服務；volumes
保留，沒有 keyring 或線上 DSW 操作。

兩個 repo 使用短期 `fix/identifier-concise-prose`。中文鎖英文完整 commit
`9a1e76d62384a9e2a2c54553b751ab4d40df8c9f`，版本為實驗性 0.3.27；沒有
upstream 升級、main merge、tag 或正式 release。舊來源快照保留原本縮排
與行尾空白，以維持可驗證的原始 hash，不當作待格式化的工作檔。

`probes/`、`after/identifier-concise-report.json` 及候選／重建 manifest 記錄
檢查範圍與 hash；`checksums.json` 覆蓋本目錄其他檔案。完整原生 HTML
留在本機，這裡保存帶原檔 hash 的完整題目摘錄。
