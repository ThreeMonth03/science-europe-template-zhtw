# 混合資源排列與 32／33 筆邊界：原生回歸，不是整份成品驗收

五案例 × 中英 × 檢核／提交兩模式，共 20 組前後對照；每側 60 份原生
HTML／PDF／DOCX，另共 40 份 LibreOffice 預覽。使用與前兩輪**完全相同**的
本機表頭試作套件，英文來源、中文譯文與版本仍為 **0.3.42**。
未合併主線、升版、發布或部署正式站。

## 原生 PDF 結果

| 案例 | 英文頁數，前 → 後 | 中文頁數，前 → 後 | 短列結果 |
| --- | --- | --- | --- |
| 長列在前，另有 8 筆短列 | 11 → 11 | 9 → 9 | 原本完整，維持不變 |
| 4 短＋長＋4 短 | 11 → 11 | 檢核 10 → 10；提交 9 → 9 | 英文兩模式第 8 列、中文檢核第 9 列不再拆頁 |
| 3 短＋長＋3 短 | 10 → 10 | 9 → 9 | 小分組不套短列新規則，原本完整且不變 |
| 長列在前，共 32 筆 | 14 → 14 | 12 → 12 | 中文檢核第 21、32 列不再拆頁 |
| 長列最後，共 33 筆 | 15 → 15 | 13 → 13 | 超過原有上限，前後相同但問題未修 |

除特別區分處，表中涵蓋兩種模式。四組、共五筆短列拆頁改善；20 組皆不增頁，
每側共 227 頁。其餘 16 組原生 PDF 的逐頁文字座標與影像完全相同。
全部保留 15 題、原有欄位文字與標點、60 段長用途及順序、金額與經費來源；
依每一筆資源核對內容，不能借用其他列的同文充當保留證據。
Q15 以前的文字座標及全部字型不變；無新增越界／重疊。

前四案例的 16 組中，選定短列完整同頁，長用途每段不拆頁；
長列每張續頁保有名稱／金額／來源，最後用途與支援項目同頁。
機械紀錄：[comparison.json](provenance/comparison.json)。

## 33 筆不是「通過排版」

英文共用 `src/budget-reading.html.j2` 及 `src/word/pilot.lua` 都有 32 筆上限。
33 筆會退回一般三欄表格，不再展開長用途；本試作刻意沒有偷偷擴大適用範圍。
原生 PDF 的長用途仍完整，但中文第 11–13 頁、英文第 13–15 頁沒有資源名稱。
短列跨頁也原樣存在。**前後完全相同只證明未改到上限外行為，不代表它好讀。**

32 筆中文檢核尾頁由「只有上一列兩行殘文」改善為「一整筆完整資源」，
但仍然大幅留白；不是解決全篇閱讀節奏。前輪最後長列中文檢核 9 → 10 頁的
取捨仍存在，本輪不增頁不能抵銷它。

## Word 證據與未完成範圍

全部 Word 正文 XML、樣式、編號、字型及外部連結相同；40 份 LO 預覽的
前後文字座標／字型／逐頁影像相同。這證明本 PDF 試作沒有改壞 Word，
**不是 Microsoft Word 實機驗收，也不等於所有 Word 原段落均已核對可見。**

前三案例的 12 組通過原有完整段落擷取檢查。32／33 筆另外保留診斷：

- 32 筆仍採 `Pilot Long Budget`；英文兩模式各有 3 個段落出現次數未能由
  連續文字匹配確認。中文兩模式連續匹配完整，但仍不據此宣稱版面驗收。
- 33 筆採一般 `Table`；英文每模式 6、中文每模式 4 個段落出現次數尚未確認。
- 人工檢視中文 33 筆 Word 第 12–13 頁，`MIX-LONG-09-PARA-07` 的句尾確實
  在下一頁，不是漏字。原始擷取卻在句中混入金額／經費，續頁欄名也會中斷段落。
  這一個確認不能代替所有未確認段落的證據；不以任意去字或排序讓檢查變綠。

完整未確認文字與次數保留於 `word_boundary_content.unresolved_paragraphs`。
`complete_word_content_acceptance=false`；`selected_checks_passed` 只代表
原生 PDF 內容、有界分頁與 Word **前後不變**等明列條件。
第一次檢查在 32 筆英文 Word 的連續段落比對停止；此後將該證據缺口獨立記錄，
沒有宣稱原檢查已修好或把未核對文字當成通過。

## 直接檢視

- 32 筆中文檢核：[基準 PDF](before/renders/mixed-bound-32-first-review-chinese.pdf)／
  [試作 PDF](after/renders/mixed-bound-32-first-review-chinese.pdf)。
- 32 筆尾頁：[原殘文](visual/mixed-boundary-32-before-zh-p12.png)／
  [試作完整資源](visual/mixed-boundary-32-after-zh-p12.png)。
- 長列在中間：[中文 PDF](after/renders/mixed-long-middle-review-chinese.pdf)／
  [英文 PDF](after/renders/mixed-long-middle-review-english.pdf)。
- 33 筆未解反例：[中文 PDF](after/renders/mixed-bound-33-last-review-chinese.pdf)／
  [英文 PDF](after/renders/mixed-bound-33-last-review-english.pdf)／
  [中文 Word](after/renders/mixed-bound-33-last-review-chinese.docx)。
- 中文 Word 原基準跨頁句子：[第 12 頁](visual/mixed-boundary-word33-before-zh-p12.png)／
  [第 13 頁](visual/mixed-boundary-word33-before-zh-p13.png)。

## 來源、重驗與清理

乾淨基準 `build-7me96gal`：英文 `200fac5239051e1a877493c7d52c3a199964c718`、
中文 `a4ccb12223530070964f7a15763b31b0fe81ee45`、工具
`25e339fbdfb1d20796471055790aad6a4226b6ed`。
基準 ZIP 與先前 0.3.42 完全相同；試作 ZIP 與
[前輪混合表頭試作](../2026-09-21-native-mixed-header/README.md) 完全相同。
程式、fixture 與收據另存於 `reproduce/`、`fixtures/`、`provenance/`。
公開合成答案在匯出前與本機 KM 路徑核對；新增資源只複製指定短列，
保留原有回答與明填零金額。沒有真實專案資料或憑證。

本批是 tables-only worker 的原生結果，未擷取 PDF-entry HTML；HTML 匯出
不是 PDF 輸入。封存 HTML 嵌入字型以 SHA256 引用縮存，收據保存原檔雜湊；
測試用鎖定工具內的 Noto Sans TC 還原全部 40 份原始位元組。
PDF 影像比較在同一 Poppler 25.03.0 下逐頁 72 DPI 執行；跨平台只要求
前後相同，不要求產生與本機一樣的影像雜湊。LO 25.2.3.2 不是 Microsoft Word。

本輪四個測試模板在確認零 project／document 引用後清除，ZIP 備份保留。
stock worker 已還原，四個指定 pilot 服務已停止；其他模板、專案與 volume
未刪除。未讀取 keyring、未接觸正式站。見 [清理紀錄](provenance/worker-lifecycle.json)。

## 下一步

1. 補足 Word 大量資源的欄位／跨頁內容證據，解決 33 筆退回窄表與缺續頁識別；
   不直接把 32 改大而跳過原有保護條件。
2. 決定表頭試作收回英文共用來源的範圍，另做版本提交；中文循既有轉換流程。
3. 全域提交提示開關仍獨立待辦：上一輪全空提交仍有 20 個系統提示節點，
   只能隱藏模板生成的診斷，不能刪掉使用者答案或把未知改成已完成。
4. 真實專案、整篇閱讀與 Microsoft Word 實機仍待驗收。
