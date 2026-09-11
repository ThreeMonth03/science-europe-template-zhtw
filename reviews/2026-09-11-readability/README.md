# 中文閱讀品質樣張：實驗版 0.2.0

本輪是閱讀品質改善，不是正式發布或完整 DMP 驗收。所有回答都是合成資料。
前一輪文件保留於 [0.1.0 樣張](../2026-09-11/README.md)，沒有覆寫。

| 案例 | 中文 PDF | 可編輯 Word | Word 預覽（LibreOffice） |
| --- | --- | --- | --- |
| 已填測試案例 | [4 頁 PDF](populated-chinese.pdf) | [DOCX](populated-chinese.docx) | [5 頁 PDF](word-preview/populated-chinese.pdf) |
| 部分缺漏 | [PDF](partial-chinese.pdf) | [DOCX](partial-chinese.docx) | [預覽](word-preview/partial-chinese.pdf) |

英文對照：[已填 PDF](populated-english.pdf)／[Word](populated-english.docx)，
[部分缺漏 PDF](partial-english.pdf)／[Word](partial-english.docx)。

建議先比較中文第 1 頁的資訊順序、第 2 頁的資料集與共同管理方式，以及
第 4 頁的培訓和預算表。Word 的第十五題在第 5 頁；不要求兩種格式頁數相同，
但相關說明、短清單和表格必須保留可理解的關係。

## 檢查結果

- 同一鎖定建置，五種回答 × 英中 × HTML／PDF／DOCX，30 份渲染成功。
- 所選英中事實／狀態一致；10 組閱讀結構回歸檢查通過。639 個翻譯單位無空白，
  翻譯及結構 audit 無問題。這些數字不是中文文體分數或內容完整度認證。
- 長文案例的 80 次測試敘述在兩種語言的 PDF 和 Word 都保留；頁尾計數不算正文。
- **整體驗收仍未通過**：使用者輸入的 Markdown 管線式表格仍以文字顯示。
  原生預算表已顯示並可編輯，不代表自由文字表格的問題已解決。
- 尚未檢查實際 Microsoft Word、全部十五題的所有條件，以及真實專案回答。

詳見 [頁面審閱](visual-review.md)、[內容與版本說明](../../docs/readability-review.md)、
[所選事實檢查](pilot-report.json)、[閱讀結構檢查](readability-checks.json)及
[來源 manifest](manifest.json)。`checksums.json` 記錄封存時的產物雜湊。

官方基底仍為 1.30.1；客製英中套件均為實驗 0.2.0。沒有建立正式 release、
合併主線或修改線上 DSW。需重建時使用 manifest 的三個精確 commit。
