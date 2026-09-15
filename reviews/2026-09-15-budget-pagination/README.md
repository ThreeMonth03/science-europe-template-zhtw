# 0.3.16：短預算的 Word 連頁對照

2026-09-15。合成資料、隔離 DSW 4.30 與 LibreOffice 預覽實驗；不是正式發布、
完整 Science Europe 內容驗收或 Microsoft Word 實機驗收。

## 先看成品

- 修正後：[中文 Word](tables/preservation-complete-chinese.docx)、
  [Word 預覽](tables/word-preview/preservation-complete-chinese.pdf)第 7–8 頁。
- 同填答舊版：[Word 預覽](prior-tables/word-preview/preservation-complete-chinese.pdf)。
- 原生 [中文 PDF](tables/preservation-complete-chinese.pdf)沒有改動正文排版。
- [英文 Word 預覽](tables/word-preview/preservation-complete-english.pdf)第 7 頁。
- 保護案例：[長篇預算](tables/word-preview/budget-long-chinese.pdf)、
  [八筆預算](tables/word-preview/budget-many-chinese.pdf)。這兩份是壓力測試，不是理想 DMP。
- 原版 worker：[中文 Word 預覽](stock/word-preview/preservation-complete-chinese.pdf)。

舊版修補 worker 的中文 Word，第 15 題說明在第 7 頁、預算表獨留第 8 頁。
新版將這個短題答單位移到第 8 頁一起讀。**仍是 8 頁，不是縮成 7 頁。**
第 7 頁留白增加，但不再需要翻頁接續一份只有兩筆的小預算。整份文件的
疏密、長表格跨頁與中文整體潤稿仍未全面驗收；不因這個局部改善宣稱已完成。

`tables/` 使用既有隔離 Markdown 表格修補 worker；`stock/` 使用原版 worker。
同一版本兩種 worker 的 ZIP 相同。原版仍有作者 Markdown 表格無法正確
轉換的既知問題，本次保留 4 筆阻擋結果，不能當成可發布版本。

## 為何採用這個修正

先在舊 Word 的副本做四組診斷，不改寫 DSW 原始輸出：

| 診斷 | 結果 | 決定 |
| --- | --- | --- |
| 縮小預算儲存格段落間距 | 仍有預算尾頁 | 不採用 |
| 解除儲存格連頁 | 第一筆在前頁、第二筆在後頁 | 不採用 |
| 同時縮間距及解除連頁 | 第二筆的名稱／金額與用途被拆到兩頁 | 不採用 |
| 只讓短篇概述接到預算表 | 題目、說明與兩筆預算同頁 | 採用其原理 |

[拆開同一筆資源的失敗預覽](diagnosis/compact-release.pdf)第 7–8 頁有具體反例。
四組 DOCX／PDF、原始 DOCX 及 hashes 均封存於 `diagnosis/`，且逐一確認只
變更副本的 `word/document.xml`。這些診斷檔不冒充原生 DSW 成品。

最終實作在英文 `src/word/pilot.lua`，原生 DSW 再生成新版文件。只有整題
符合保守界線才啟用：單一計畫、單一三欄預算表、1–2 筆預算、最多三個平面
清單項、24 個段落；整體最多 1,000 個寬度單位、每格最多 200 單位／三段。
CJK 碼位以兩單位估計。拒絕巢狀清單／表格、圖片、連結、程式碼、合併
儲存格、額外標題及表格後續文字等複雜結構；先完整驗證 AST 才修改。
界線是保守啟用條件，不是適用所有字型及 Word 版本的排版數學保證。

僅在預算表前的普通概述套用既有 Pilot Lead／Pilot List Lead；不改表格、
字級、行距、頁邊界或 Word reference，不插入強制分頁。作者段落、清單、
粗斜體、金額（包含 0）、經費來源及網址原樣保留。Jinja、譯文與 PDF CSS
沒有更動，不建立獨立中文邏輯，也不使用 LLM 改寫或 JSON 轉檔。

## 驗證與實際發現

- 英文 125、中文 100 項單元測試通過，英文 TDK verify 通過。新的 Pandoc
  測試已接進兩邊 CI，使用固定 image digest 的 Pandoc 3.8.3：24 個 AST
  案例中，5 個只准增加指定概述樣式，19 個拒絕案例須保留完整原 AST。
  此探針的對照是關閉新 handler；歷史整份模板的對照另外使用真實舊套件。
- 720 翻譯單位、空白 0，translation／structure audit 均空；原有八組翻譯
  探針通過。34 個 Jinja 靜態 binding 查核通過，但不代表完整回答覆蓋率。
  新長篇／多筆 fixtures 亦通過本機編譯 Common KM 的路徑與選項驗證。
- 新舊修補 worker 各三案例 × 二語言 × 三格式，共 36 份原生文件；另新產
  6 份原版 worker 控制文件，重用 6 份不可改寫的舊原版控制文件。合計比較
  48 份 HTML／PDF／DOCX，含 42 份本輪新產，另比較 16 份 Word 預覽。
- 逐題對照 120 題 HTML，全題 DOM 不變。Word 從第一題起逐個 XML 節點比對：
  短控制組每語言只允許三個概述段落換樣式，其餘全部原樣；長／八筆組連
  概述也不得更動。表格 XML、所有 inline 格式、連結目標及 styles.xml 不變。
- PDF／Word 預覽全文與頁數相同；Q13 整個閱讀單位、實體頁界及預覽區塊內
  幾何檢查通過。另重跑保存、共享、標點、容量、閱讀與品質六類既有檢查。
- `budget-long` 在第一筆用途追加 60 個有編號段落、清單、檔名和連結，
  不是測試時刪減回答。所有段落保留，但英文有兩段、中文有三段跨頁，
  舊新版相同。檢查器只移除精確且可核對的頁碼／重複表頭，辨識相鄰頁
  的完整文字；跨頁段落絕不算作「同頁」。刪字、改字或錯誤表頭必須失敗。
- 人工以頁面影像比對舊中文第 8 頁、新中文第 7–8 頁、新英文第 7 頁，
  並檢視長篇中文第 9–10 頁及八筆中文第 8 頁。短預算題答同頁；長篇仍有
  句子跨頁、續頁只有用途而缺少該筆名稱／金額的閱讀負擔。八筆表格自己
  一頁，但題目概述仍在前頁。這些均留作後續缺點，不以回歸通過掩蓋。

修補 worker 的頁數如下；每一列都是相同填答的 0.3.15 → 0.3.16。

| 案例 | 語言 | 原生 PDF | Word 預覽 |
| --- | --- | --- | --- |
| 短控制組 | 英文 | 8 → 8 | 7 → 7 |
| 短控制組 | 中文 | 7 → 7 | 8 → 8 |
| 長篇用途 | 英文 | 13 → 13 | 12 → 12 |
| 長篇用途 | 中文 | 12 → 12 | 12 → 12 |
| 八筆預算 | 英文 | 9 → 9 | 8 → 8 |
| 八筆預算 | 中文 | 8 → 8 | 8 → 8 |

原版 worker 的短控制組 Word 預覽則英中均為 7 → 7 頁；其與修補 worker
內容格式不同，不可用這個頁數差異宣稱原版更好。

## 版本與重建

英中套件 0.3.16，短期分支 `feat/budget-pagination` 承接 0.3.15，不增加永久
維護線、不合併 main、不發布 tag／release、不部署線上 DSW。官方基底仍為
1.30.1／`22d60aae4b63ee677477ac0c73097807284aaf9f`。
中文鎖定英文 `ff1a5bf51c008c24fc6598f670719387bdfefb43`，工具仍為
`25e339fbdfb1d20796471055790aad6a4226b6ed`。
原生產檔中文 checkpoint 是 `97f4abbfed4317be8e0ea43c3d6afeb4fd910e84`；
後續檢查器修正以報告 hash 綁定。第一個中文 checkpoint 的 CI 曾因 XML
命名空間比較器誤判失敗，已修復；後續乾淨重建須與實際測試 ZIP 完全相同。

- 英文 ZIP：`65366eb585ab7f0fbb7b0ad6f40427ddfc4797c7ec3f054f0f825884da638c04`。
- 中文 ZIP：`e957065036f4eaebd3292f83dfcb44aed7c0845eb19509c4ea4f16e31b9d6347`。
- 新原版／修補版：`outputs/build-z3arhpbp`／`outputs/runtime-tables-0act9nn7`。
- 舊修補版同填答重播：`outputs/runtime-tables-qh3pq98i`，沿用 0.3.15 精確
  ZIP；舊原版控制來自 `outputs/build-o68nfhmu`。未覆寫舊 output 或審閱封存。

`budget-source-delta.json` 核對英中 src 只差 Word Lua，其他檔案逐位元相同；
`rebuild-manifest.json` 留下乾淨重建紀錄。原生大 HTML 留在 outputs、報告
記錄 hash，封存包括 PDF、DOCX、預覽、fixture sidecar、manifest 和檢查結果。
未來 upstream／Pandoc／Word reference 升級須重跑 guard 的正反例、全 XML
保留與實際分頁，不能以 Git 沒有文字衝突當成版面相容。

下一個獨立實驗宜處理長預算的閱讀結構，再做整份中文語氣及實際 Microsoft
Word 驗收；本輪不繼續擴大改動，也不把局部修正當成正式上線授權。
