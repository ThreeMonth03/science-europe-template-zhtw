# 0.3.44 中英文提交預覽：原生整合對照

實際使用已整合、乾淨建置的 0.3.44 中英套件，完成 **16 組原生比較**：四種公開合成案例、
兩種語言、檢核／提交兩種模式。保留 48 份原生 HTML／PDF／DOCX 與 16 份 LibreOffice
Word 預覽。本輪沒有修改模板、翻譯或版號，也沒有接觸正式 DSW。

英文來源為 `41bb0ac59e86f5591b641a001a04240375426545`；實測中文候選建置為
`d17911ff57d29ede821193a0f03da1827f70e8de`。原生執行使用相同 ZIP，不在套件上重新套原型補丁。

## 結果

| 案例 | 語言 | 原生 PDF：檢核 → 提交 | Word 預覽：檢核 → 提交 |
| --- | --- | --- | --- |
| 全空 | 英文 | 4 → 3 | 3 → 2 |
| 全空 | 中文 | 3 → 2 | 3 → 2 |
| 部分漏填／自填提示字樣 | 英文 | 7 → 6 | 6 → 5 |
| 部分漏填／自填提示字樣 | 中文 | 6 → 6 | 6 → 6 |
| 概要／品管 | 英文 | 8 → 6 | 6 → 6 |
| 概要／品管 | 中文 | 7 → 6 | 7 → 6 |
| 資料集名稱漏填 | 英文 | 8 → 7 | 7 → 6 |
| 資料集名稱漏填 | 中文 | 7 → 6 | 7 → 6 |

此表比較同版的兩個輸出模式，不是宣稱升版另有減頁效果。16 組新版輸出皆與相應已驗證
原型逐頁一致：前三種案例對照 `2026-09-21-submission-polish`，名稱漏填案例對照
`2026-09-21-dataset-labels`。舊證據與舊檢查結果沒有回填或重封。

- 原生 HTML 全部逐位元組相同；封存只把內嵌字型換成可核對雜湊，保留原始 HTML 雜湊。
- Word 的每個 ZIP 組件完全相同，僅容許經解析驗證的建立／修改時間不同；正文、樣式、
  連結、字型、編號與標點不准不同。
- 原生 PDF 與 Word 預覽的文字座標、逐頁像素皆相同；沒有文字超出頁面。
- 另檢查 HTML → DOCX → 預覽的完整字元數量與段落，以及六節十五題、已填內容、
  否定答案、自填提示文字與資料集原始清單編號。Q8 篩選後仍顯示「參考資料集 2」。
- 英文原生 PDF 仍有一至兩筆字型度量框重疊篩查結果，與原型相同；這不是新增撞字，
  也不能把度量框直接當成墨跡碰撞。完整座標警示保留在 `provenance/native.json`。

## 可直接閱讀的範例

- [中文概要／品管提交 PDF](native/renders/submission-metadata-submission-chinese.pdf)
- [相同內容的可編輯 Word](native/renders/submission-metadata-submission-chinese.docx)
- [Word 的 LibreOffice 預覽](native/word-preview/submission-metadata-submission-chinese.pdf)
- [英文概要／品管提交 PDF](native/renders/submission-metadata-submission-english.pdf)
- [中文未命名資料集提交 PDF](native/renders/dataset-labels-submission-chinese.pdf)
- [中文未命名資料集檢核 PDF](native/renders/dataset-labels-review-chinese.pdf)
- [中文全空提交 PDF](native/renders/empty-submission-chinese.pdf)

注意：`AUTHORED-NOTICE` 黃框、使用者填寫的「尚待補充」及 `N/A` 是刻意設計的原文保留
測試，並非提交模式漏掉的系統提示。不能以全文搜尋這些字串後刪除來實作開關。
全空案例仍顯示本機測試專案的實際建立者，不代表模板虛構人員。

## 目視紀錄與仍需改善之處

本輪查看 `visual/` 七張頁面圖，包括中英品管、中文 Word 品管、名稱漏填、Q8 編號與全空
封面。固定品管已合成完整句子，中文「校正量測結果、資料輸入檢核及其他品質管控方法」
沒有再拆成零碎項目，沒有觀察到這些頁面的新增截字或撞字。

一致性通過不等於整體閱讀品質已完成：名稱漏填案例的非參考資料集小區塊仍分在第 2／3 頁；
第 9 題仍有重複、偏生硬的個人資料敘述；中性數字標籤與後接中文字的間距也可再檢視。
這些保留為下一輪改善候選，不能在本輪比對中偷偷修字後稱為相同。

尚未完成所有未標記佔位文字的處理、空經費來源項目、ORCID 解析、任意真實專案、
Microsoft Word 原生目視驗收，亦不宣稱符合所有 Science Europe 或臺灣正式繳交要求。
`release_acceptance`、`global_switch_complete`、`microsoft_word_acceptance` 仍為 false。

## 範圍、安全與重現

僅在本機 DSW 4.30、已審核的 tables-only docworker、同一 Poppler／LibreOffice 環境比較。
不將跨平台像素雜湊當成通用黃金值；測試會重新計算前後一致關係。
生成日是 2026-09-21；不同日期重新原生匯出時，必須另行核對實際日期，不可隨意忽略全文差異。

兩個本輪暫存模板已在確認無專案／文件引用後清除，原 ZIP 備份保留；worker 已還原為 stock
映像，四個本輪服務已停止。沒有刪除資料卷或其他本機服務。

`provenance/` 保存乾淨候選建置、544 組實際來源檢查、歷史還原檢核、原生結果、套件成員
雜湊與清理／生命週期收據；候選階段的 `native_integrated_render_checked=false` 保留原樣，
本輪完成狀態另見 `inventory.json` 與 `provenance/native.json`。

重跑使用 `scripts/prepare_submission_preview_native.py`，提供與收據雜湊一致的公開 KM
檔案目錄；再用 `run_missing_info.py` 對四案例與兩模式匯出，以 `preview_word_short_budget.py`
產生獨立 LibreOffice 預覽，最後用 `check_submission_preview_native.py` 核對。
`reproduce/` 保留本輪腳本；它們仍依賴相同 repo 的共用檢查器與未改動的前輪封存。
