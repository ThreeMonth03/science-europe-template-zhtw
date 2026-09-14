# 0.3.14：Q13 閱讀單位與整份文件分頁

2026-09-15。這是合成案例、隔離 DSW 與 LibreOffice 預覽的局部實驗，
不是正式發布、完整 Science Europe 內容驗收或 Microsoft Word 實機驗收。
本文件另封存於 `reviews/2026-09-15-identifier-reading/README.md`，
下列相對連結以該封存目錄為準。

## 樣張

- 完整保存安排：[中文 PDF](tables/preservation-complete-chinese.pdf)、
  [中文 Word](tables/preservation-complete-chinese.docx)、
  [Word 預覽](tables/word-preview/preservation-complete-chinese.pdf)。
- 長網址與同名資料集：[中文 PDF](tables/paper-references-chinese.pdf)、
  [中文 Word](tables/paper-references-chinese.docx)、
  [Word 預覽](tables/word-preview/paper-references-chinese.pdf)。
- 舊版對照：[完整中文 Word 預覽](prior-tables/word-preview/preservation-complete-chinese.pdf)。
- 英文：[長網址 PDF](tables/paper-references-english.pdf)、
  [Word](tables/paper-references-english.docx)。
- 原版 worker：[完整中文 PDF](stock/preservation-complete-chinese.pdf)、
  [Word 預覽](stock/word-preview/preservation-complete-chinese.pdf)。

`tables/` 使用既有的隔離表格修補 worker；`stock/` 是原版，兩者使用相同
英中 ZIP。`prior-*` 是上一輪 0.3.13 的同填答產物，並非拿內容不同的舊文件
比較頁數。舊封存不覆寫。原版的 Markdown 表格缺陷仍阻擋正式發布。

## 問題與改法

上一輪完整中文 Word 的表格修補版有 8 頁，最後一頁主要是預算表。檢查原生
Word 後，沒有發現這張表前額外插入的手動分頁；表格本身也沒有新加的整表
keep 規則。前面 Q13 每個完整填答管道卻占四段：管道編號、儲存庫類型、
識別碼決定，以及指派／解析安排。短標籤各自帶著 keep-with-next，會影響
頁面剩餘空間能否容納下一個閱讀單位。

本輪把每個管道改成兩個閱讀單位：

1. 管道編號與儲存庫類型共用一行，保留粗體及與後文相鄰的設定。
2. 「資料將取得持續識別碼」與既有指派／解析敘述連讀。

不是刪答案或把整題鎖在同一頁；各管道仍分開，否定及未填決定仍有自己的
段落。只改英文 Q13 的容器、專屬 PDF CSS 與 Word Lua。中文字句、使用者
原文、十五題題目、分支條件、資料集／管道 UUID、表格儲存格、Word reference、
字級、行距與頁面邊界均不變。沒有手改生成中文，也沒有 LLM 改寫。

中文閱讀改善來自段落連貫，不是宣稱本輪完成潤稿。例如「資料將取得持續
識別碼。持續識別碼將由……」仍有名詞重複；這次保留原本意思，未為縮短
文字而合併不同責任或承諾。

## 比較與檢查

- 英文 113 項、中文 89 項單元測試通過，英文 TDK verify 通過。
- 716 個翻譯單位全部精確沿用、空白 0，translation／structure audit 無錯誤。
  翻譯 outline 同步反映上一輪已完成的論文標籤，不是本輪新增翻譯。
- Q13 雙語探針有 1,124 組分支／語言檢查、1,176 次固定句比對；涵蓋指派
  決定、三種指派者、解析保障、五種儲存庫類型、未填／未知選項與殘留子答案。
  原有七類探針亦通過。這些離線檢查不算成實際 DSW 文件數量。
- 在實際 worker 的 Pandoc 3.8.3 跑 11 個 Lua 結構案例。新規則最多合併
  兩個、合計 240 Unicode 字元的全粗體固定標籤；長標籤、三個標籤、混合
  自由文字、清單與 answer-detail 均拒絕合併，與舊 Lua 的對應 AST 相同。
  規則外的段落 AST 也不變。這不是原生產檔或 Microsoft Word 驗收。
- 34 個 Jinja 的靜態 UUID binding 稽核無未定義變數或不存在 entity；沒有新增
  問卷欄位或 fixture。靜態存在不等於已完成所有分支覆蓋。
- 新版兩案例 × 二語言 × 三格式 × 二 worker，共 24 份原生 HTML／PDF／DOCX，
  另有 8 份 Word 預覽。對照沿用上一輪的同案例產物，不冒充本輪重新產生。
- 每個 worker 比較 60 題，合計 120 題。先只還原 Q13 新容器與肯定句位置，
  再核對全題 DOM、文字、事實狀態與所屬項目；其餘十四題 HTML 完全相同。
  不將 Q13 整題排除。作者 answer-detail 原始 HTML 必須相同。
- 原生 Word 全部正文段落與表格逐項比對，只允許 Q13 中相鄰、同樣式的指定
  完整段落合併；每份少 4 段。其餘段落與表格不變，標籤粗體保留。
- 比較 PDF 與 Word 預覽從第一題起的完整文字，僅正規化空白並移除可驗證的
  頁碼，不刪標點或改檔名。另查頁面邊界、預覽文字區塊內重疊，以及 Q13
  標籤與第一個答案句同頁；不以頁數單獨當驗收標準。
- 保留上一輪論文原值、原生 Word／PDF 的完整連結目標與長網址換行檢查。
  原版仍有 8 筆已知表格阻擋，不能因其他檢查通過而轉成可發布。

兩種 worker 的同案例頁數如下（舊版 → 新版）：

| 案例／語言 | 原版 PDF | 原版 Word 預覽 | 修補版 PDF | 修補版 Word 預覽 |
| --- | --- | --- | --- | --- |
| 完整保存／英文 | 8 → 8 | 7 → 7 | 8 → 8 | 7 → 7 |
| 完整保存／中文 | 7 → 7 | 7 → 7 | 7 → 7 | 8 → 8 |
| 長網址／英文 | 9 → 8 | 7 → 7 | 9 → 8 | 8 → 8 |
| 長網址／中文 | 8 → 8 | 8 → 8 | 8 → 8 | 8 → 8 |

每個 worker 的 identifier、preservation、sharing、polish、format、reading、
quality 七類檢查各通過四組；相同 ZIP／fixture 的跨 worker 比較亦通過四組。
人工查看原版中文 PDF 第 6 頁、Word 第 7 頁，以及表格修補版完整中文 Word
第 7–8 頁。Q13 的標籤與敘述變得集中，抽查頁面未見裁切；Word 第 8 頁仍
主要是預算表，這個尾頁問題沒有解決，不能宣稱整份分頁已驗收。
長網址英文 PDF 少一頁只是同內容的分頁結果，不代表中文或 Word 也同步減頁。

## 版本與後續

英中皆為 0.3.14，短期工作分支 `feat/identifier-reading` 承接 0.3.13。
英文 `98b153364844930de772cbdcb1e13eb14e3555b7`；中文實際產檔 checkpoint
`9e60e82c1850664b3a3dd50ecdb2ce2889084853`，後續查核程式以 checksum 綁定。
工具仍鎖定 `25e339fbdfb1d20796471055790aad6a4226b6ed`；官方基底仍為
1.30.1／`22d60aae4b63ee677477ac0c73097807284aaf9f`。

- 英文 ZIP：`f210bcbb0ab48a69ee7a728193900bc6a4d302e9f14ebf7301ff19139b1df6ec`。
- 中文 ZIP：`dd69e83947e2b94324e23ba1eb59943cc60064908ef4295dbe169c46345b883a`。
- 新原版／修補版：`outputs/build-kbcwra8r`／`outputs/runtime-tables-1w7b4to9`。
- 舊原版／修補版：`outputs/build-jijf77dp`／`outputs/runtime-tables-4he_8ki7`。

封存 PDF、DOCX、Word 預覽、fixture sidecar、報告與完整校驗碼。內含巨大
字型的原生 HTML 留在 outputs，報告記錄 hash。乾淨重建須與產檔 ZIP 相同。
來源差異只允許 Q13、專屬 CSS、Word Lua；reference 及其他 src 檔案逐位元
相同。未來上游升級需連同這三者重驗，不是只解 Git 衝突。

下一輪優先補 Q13 的明確缺答／未知提示：肯定指派後，未填指派者或解析保障
目前仍會少掉該部分；未知儲存庫類型也沒有 Q13 專屬提示。本輪確認沒有
虛構肯定承諾，但未解決這些既有缺口。此後仍需整份中文語氣、實際 Word
開啟環境、去識別真實專案及表格 worker 部署／回退驗收。

未合併主線、未建立正式 tag／release、未部署線上 DSW，未讀取 keyring 或
線上專案。本機隔離 runtime 在檢查結束後恢復原版 worker 並停止，資料卷保留。
