# 混合長／短預算：0.3.42 原生基準與離線排版試驗

**本輪沒有修改模板、翻譯、版號或 Word。** 這裡區分 0.3.42 的 DSW 原生輸出
與另外產生的 PDF 排版試驗；後者不是已發布或已原生驗收的新版本。

## 結果與成品

確認 0.3.42 的一個缺口：預算有長回答時，短列不會套用上一輪的連頁規則。
原生英文第 7 列又拆在第 8／9 頁；中文檢核版第 6 列拆在第 7／8 頁，
中文提交預覽第 7 列也拆在第 7／8 頁。

試驗只替已分組的普通表格中、符合原有上限的短列加連頁屬性。
長列的完整原始 HTML、續頁識別、CSS、字型與所有文字都不修改。
八組 A/B 的短列全部保持同頁、頁數不增加；長列仍能跨頁並重複識別。

- 英文：[原生基準 PDF](native/mixed-long-last-review-english.pdf)、[試驗 PDF](trials/mixed-long-last-review-english-keep-short-rows.pdf)。
- 中文提交：[原生基準 PDF](native/mixed-long-last-submission-chinese.pdf)、[試驗 PDF](trials/mixed-long-last-submission-chinese-keep-short-rows.pdf)。
- 中文提交第 8 頁：[修改前](visual/mixed-long-last-submission-chinese-baseline-p8.png)／[試驗後](visual/mixed-long-last-submission-chinese-trial-p8.png)。
- 中文漏填：[原生 PDF](native/mixed-gaps-submission-chinese.pdf)、[試驗 PDF](trials/mixed-gaps-submission-chinese-keep-short-rows.pdf)。
- 中文漏填 Word：[可編輯原生檔](native/mixed-gaps-submission-chinese.docx)、[LibreOffice 預覽](word-preview/mixed-gaps-submission-chinese.pdf)。

英文、中文提交的六組離線基準，其全部文字座標與字型清單都重現原生 PDF。
**另外兩組中文檢核版未重現原生基準，不能列為原生改善驗收。**

| 情境／模式 | 原生 PDF 頁數 | 離線基準 → 試驗 | 原生基準重現 |
| --- | --- | --- | --- |
| 長列在最後，英文兩模式 | 11 | 11 → 11 | 是 |
| 長列在最後，中文提交 | 9 | 9 → 9 | 是 |
| 長列在最後，中文檢核 | 9 | 10 → 10 | **否** |
| 混合漏填，英文兩模式 | 11 | 11 → 11 | 是 |
| 混合漏填，中文提交 | 10 | 10 → 10 | 是 |
| 混合漏填，中文檢核 | 10 | 10 → 10 | **否** |

中文檢核版的原生 PDF 有 `Pilot-CJK-Semi-Bold`，離線基準沒有；
除了字型清單不同，文字座標也不同。這是延續先前離線重播的基準差異，
不是本輪已修復的項目。`provenance/font-baseline-diagnostics.json` 保留實測清單。
八組 A/B 各自的前後字型相同；不把「A/B 相同」寫成「一定與原生相同」。

## 檢查涵蓋什麼

兩組公開合成案例 × 中英文 × 檢核／提交，共 24 份原生 HTML／PDF／DOCX，
另產生八份 Word 預覽及 16 份離線 PDF。每筆長回答有 60 個唯一段落標记，
可檢查遺失、重複或順序錯誤；這些標記只在測試資料，不會加入使用者的回答。

- 逐列核對 PDF 的完整段落、金額及經費來源，不能用其他列的內容補足；
  刪字、重複、錯列及長用途改字都有拒絕測試。
- 長列各續頁保留完整的名稱／金額／經費來源；短列有界連頁，整張表不綁定。
- 漏填保留原提示；金額 0、900 即使缺幣別也不消失、不推定幣別。
- 八份 Word 的 60 個長段落各出現一次且順序正確，續頁資源名稱仍在；
  每個正文段落也與 LibreOffice 擷取結果核對。Word 沒有另做試驗改版。
- A/B 的 Q15 以前正文座標相同，沒有增加既有字型度量框重疊記錄。
  兩組本來就沒有短列跨頁的英文漏填案例，整份 PDF 座標都不變。
- 長列放前／中／後、兩邊各三筆短列、32／33 列上限有八組結構測試；
  這些額外排列不是本輪的原生匯出範圍。

`native/` 和 `word-preview/` 是原生基準及其預覽；`trials/` 是另存的 PDF 試验。
HTML 只封存題目內容與完整原檔雜湊，避免重複存入字型。
`fixtures/` 保留本輪實際匯出的四組題目資料與來源雜湊；
`reproduce/`、`provenance/` 分別保存檢查程式與建置／清理收據。

## 下一步與邊界

建議下一版只在英文共用 `budgetReading.ordinary()` 的普通表格分組中，
接上現有短列 helper；保留原本長列分支、三列以下及超限回退規則。
中文仍由既有流程產生，不另維護一套排版來源。

接回後應直接比較「0.3.42 原生」與「新候選原生」，特別驗證兩組中文檢核版；
目前不能用離線 PDF 代替這一步。還要加入既有全空／部分填答／純長列／純多列
控制組，避免為了混合情境影響原來的成品。

提交預覽的提示關閉範圍不變。Microsoft Word 實機、ODT／LaTeX、任意真實專案、
超過 32 列及複雜巢狀內容，都不是本輪全面驗收項目。

本輪使用乾淨 0.3.42 套件，英文來源 `200fac5239051e1a877493c7d52c3a199964c718`，
中文候選建置來源 `f06df3b58cd7b5346b049644d540a70eb5ea86b5`；工具仍鎖定
`25e339fbdfb1d20796471055790aad6a4226b6ed`。未呼叫正式站或取用正式憑證。
兩個本輪本機測試模板已清除、ZIP 備份保留；stock worker 已還原，四個 pilot
服務已停止，其他 stacks 與 volumes 未刪除。
