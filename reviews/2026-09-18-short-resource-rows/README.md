# 0.3.42：多筆預算短列連頁的原生驗證

這輪修正「名稱在前頁、用途在後頁」的短預算列。英文共用模板實作，
中文沿用既有轉換；不是手改成品 PDF。仍是局部實驗，未部署正式站，
不等於整份 DMP、Microsoft Word 或國科會正式繳交驗收。

## 先看成品

- 中文提交預覽：[PDF](after/native/budget-many-submission-chinese.pdf)、[可編輯 Word](after/native/budget-many-submission-chinese.docx)、[Word 預覽](after/word-preview/budget-many-submission-chinese.pdf)。
- 中文檢核版：[PDF](after/native/budget-many-review-chinese.pdf)。
- 英文檢核版：[PDF](after/native/budget-many-review-english.pdf)、[Word](after/native/budget-many-review-english.docx)。
- 中文全空提交：[PDF](after/native/empty-submission-chinese.pdf)、[Word](after/native/empty-submission-chinese.docx)。
- 英文第 9 頁：[修改前](visual/before-english-p9.png)／[修改後](visual/after-english-p9.png)。
- 中文第 8 頁：[修改前](visual/before-chinese-p8.png)／[修改後](visual/after-chinese-p8.png)。

| 八筆預算案例 | 原本跨頁的列 | 現在完整所在頁 |
| --- | --- | --- |
| 英文檢核／提交 | 第 7 列：第 8／9 頁 | 第 9 頁 |
| 中文檢核 | 第 6 列：第 7／8 頁 | 第 8 頁 |
| 中文提交 | 第 7 列：第 7／8 頁 | 第 8 頁 |

四種輸出中的八列都已逐列核對，名称、用途、金額與經費來源完整同頁。
英文全文仍 9 頁、中文仍 8 頁；表頭在續頁照常重複。已視覺檢查中英文
檢核版表格前後頁，沒有用缩字或刪內容來達成連頁。

## 限定檢查結果

四種公開合成案例：部分填答、全空、長篇且未填幣別、八筆預算；
兩語言 × 檢核／提交預覽，共 16 組前後对照，全部通過本輪限定檢查。
候選實際新增 48 份原生 HTML／PDF／DOCX、16 份 LibreOffice 預覽。
此處保存前後 64 份 PDF／DOCX、32 份 Word 預覽，以及 fixture 收據。
原生 HTML 只封存 15 題與原檔雜湊，避免重複嵌入字型。

- 15 題 HTML 內容完全相同；Word 正文 XML、樣式、字型表、編號與外部連結相同。
- 全部原生 PDF 及 Word 預覽的頁數、字型清單不變。
- 全部 Word 正文座標不變；非八筆預算案例的 PDF 正文座標也完全不變。
- 八筆預算的 PDF 只動 Q15 內部；Q15 以前的正文位置不變。
- 每列以唯一名稱界定範圍，再逐一消耗完整段落，拒絕刪字、重複、錯列或用途倒序。
  不靠字數相同來宣稱保留內容。既有字型度量框重疊記錄沒有增加。

中英 prepared 套件各 120 組結構／escaping 檢查及 28 組 print／screen
排版對照，涵蓋缺用途、缺金額、0 金額但缺幣別、缺經費來源及缺補助編號。
長／複雜控制組維持原行為。這些小型排版案例不是額外的原生 DSW 專案驗收。

## 範圍、限制與後續

只在 4–32 列、沒有既有長列展開的普通預算表，替通過文字／段落／標記上限
的短列加連頁設定；不是把整張表鎖在同頁。三列以下、超過上限與複雜內容
仍走原規則。沒有改問句、自由回答、748 組譯文、CSS、字型或 Word 來源。
完整來源雜湊先逆向還原 0.3.41，再跑所有既有歷史 gates，沒有重設基準。

同表混合超長用途與短列、33 列以上，以及真實代表性專案，仍需下一輪壓力測試。
本輪不擴大提交預覽的提示關閉範圍；不能據此聲稱任意缺答專案可直接繳交。
LibreOffice 預覽不是 Microsoft Word 實機驗收；ODT／LaTeX 也不在本輪範圍。

## 版本、重建與清理

- 英文：`200fac5239051e1a877493c7d52c3a199964c718`，0.3.42。
- 中文候選來源鎖：`3551f091fd7916a58dca34235b9cc65771154984`，0.3.42。
- 工具：`25e339fbdfb1d20796471055790aad6a4226b6ed`。
- 英文 ZIP SHA256：`8e8d036c2623fed7a58035112a6d59d20f3a86ee32fcd36af55a14f32ac43387`。
- 中文 ZIP SHA256：`14aa9f648afb1e295d4066b2eb41db0ccb1db1f26d8c067169d6d8262d4db26d`。

`provenance/` 保存乾淨候選建置、來源／翻譯檢查、排版探針、原生比對與清理收據。
`reproduce/` 保存檢查器、來源片段及 pipeline 鎖；`checksums.json` 封存全部檔案。
只有本機 tables-only 測試 worker 執行公開合成案例，沒有讀取正式 DSW 憑證。
兩個本輪測試模板已刪除，經驗證的 ZIP 備份保留；stock worker 已還原，
四個本機 pilot 服務已停止，其他 stacks 與 volumes 未刪除。
