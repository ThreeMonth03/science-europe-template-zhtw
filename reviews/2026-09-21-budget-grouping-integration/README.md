# 0.3.43 整合後的中英文原生對照

本輪將前輪套件試作正式接回**實驗分支的英文共用來源**，中文仍循既有轉換流程。
沒有新增中文 Jinja、改寫 748 組譯文或部署正式 DSW。不是新的整篇視覺驗收。

乾淨建置：英文 `5a0c4545fc5f0d9dac09c2c92831d002b65e8f27`；
中文 `30992d8`；翻譯工具 `25e339fbdfb1d20796471055790aad6a4226b6ed`。
中英文配對版本為 0.3.43。全部模板內容、字型及 Word 資產逐位元組等同
[前輪原生試作](../2026-09-21-large-resource-groups/README.md)，
僅版號、套件 ID、依固定公式生成的檔案 UUID 與來源提交時間戳記改變。
輸出格式 UUID 沒有變動。舊封存及當時的失敗紀錄不改寫。

## 實測結果

32 筆／長列在前，以及 33 筆／長列在後，各測中英文及檢核／提交預覽，
共 24 份原生 HTML、PDF、DOCX，另做 8 份 LibreOffice 預覽。
與前輪試作比較：八組 HTML 全文、PDF／Word 文字座標及逐頁影像完全相同。
DOCX 文件元件相同；只允許 core properties 的合法建立／修改時間戳記不同。
另重驗 PDF 的完整原文、短列同頁、長列續頁名稱、用途尾句與經費配置同頁；
Word 原始列／欄位內容核對通過。

| 案例 | 英文 PDF／Word 預覽 | 中文 PDF／Word 預覽 |
| --- | --- | --- |
| 32 筆・檢核 | 14／15 頁 | 12／13 頁 |
| 32 筆・提交預覽 | 14／15 頁 | 12／13 頁 |
| 33 筆・檢核 | 14／16 頁 | 12／14 頁 |
| 33 筆・提交預覽 | 14／15 頁 | 12／14 頁 |

這些頁數與前輪試作相同，**本輪沒有再次減頁**。
可直接看 [中文 PDF](after/renders/mixed-bound-33-last-submission-chinese.pdf)、
[中文 Word](after/renders/mixed-bound-33-last-submission-chinese.docx)、
[英文 PDF](after/renders/mixed-bound-33-last-submission-english.pdf)、
[英文 Word](after/renders/mixed-bound-33-last-submission-english.docx)。
這些是具識別標記的合成壓力案例，不是可直接繳交的計畫書。

## 仍未完成

- 英文 Word 每組仍有三筆短列拆段跨頁：32 筆案例的第 10、19、28 列，
  33 筆案例的第 9、18、27 列；四組中文案例沒有短列拆段。
- [中文 PDF 尾頁](visual/zh-submission-final-page.png) 仍偏空。
  [Word 尾頁](visual/zh-word-final-page.png) 的長用途原文完整，但人工整體閱讀驗收仍未完成。
- 提交預覽尚未全域關閉系統漏填提示。前輪全空提交仍有 20 個提示節點，
  本輪不刪提示、不補造答案，不能因此宣稱可供國科會正式繳交。
- 沒有重新產出所有先前基本案例；來源／套件精確還原與舊封存回歸之外，
  本輪新原生測試範圍限上述八組。真實專案與 Microsoft Word 尚待驗收。

## 版本與驗證證據

`provenance/candidate-budget-grouping-scope.json` 證明精確撤回新差異後，全部
中英文 prepared source 等同 0.3.42 封存，再接受更早版本的既有檢查；
748 個翻譯單位、260 項 Q5 檢查通過。Q13 預檢另外保留。
`structure/` 保存實際 Pandoc 的 37 組結構檢查及 PDF 的 32 組結構／8 組引擎檢查。
這些檢查不取代全篇人工驗收。

`provenance/budget-grouping-native.json` 綁定新套件、各成品及逐列內容；
`package/` 保存完整模板 JSON，`provenance/package-members.json` 保留全部 ZIP 成員雜湊。
HTML 只把內嵌公開字型改存可逆的雜湊引用，保留原始與精簡後雜湊；
不能把 HTML 匯出誤當 PDF 格式專屬入口。

本機原生測試沿用已審核的 tables-only worker（只處理 Markdown 表格），沒有加入
字型實驗或存取 production／keyring。完成後移除兩個本次測試專用模板；
ZIP 備份保留，stock worker 已還原，四個本機服務全部停止。

重播封存檢查：

```bash
../dsw-document-template-tool/.venv/bin/python -m unittest discover -s tests -p 'test_budget_grouping_*.py' -v
```
