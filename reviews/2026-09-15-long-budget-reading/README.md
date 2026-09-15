# 0.3.17：長預算的全寬用途與續頁歸屬

2026-09-15。合成資料、隔離 DSW 4.30、Pandoc 3.8.3 與 LibreOffice 預覽；
不是正式發布、完整 Science Europe 或 Microsoft Word 實機驗收。

## 先看樣張

- 長篇中文版：[Word 預覽](tables/word-preview/budget-long-chinese.pdf)第 7–10 頁、
  [Word 檔](tables/budget-long-chinese.docx)。
- 相同回答的舊版：[中文 Word 預覽](prior-tables/word-preview/budget-long-chinese.pdf)。
- 英文：[Word 預覽](tables/word-preview/budget-long-english.pdf)、[Word 檔](tables/budget-long-english.docx)。
- 短預算控制：[中文 Word 預覽](tables/word-preview/preservation-complete-chinese.pdf)。
- 八筆預算控制：[中文 Word 預覽](tables/word-preview/budget-many-chinese.pdf)。
- 原生 [中文 PDF](tables/budget-long-chinese.pdf)沒有套用這次 Word 版型，仍有舊長表格問題。

舊 Word 把很長的用途放在三欄表格的第一欄：續頁只能看見用途，名稱、
金額和經費來源留在前面，且有句子拆到兩頁。新版讓這筆用途使用全寬，
每一原有段落／清單作為可分頁的閱讀單位；續頁重複同一筆的資源表頭。
本批英中長篇均由 12 頁變成 10 頁，60 個有編號段落皆完整保留。
它們是刻意重複句子的壓力測試，不是假裝自然、完成潤稿的 DMP。

重複的名稱、5000 TWD 與經費來源是「這仍是同一筆資源」的頁面脈絡，
不是新增預算。DOCX XML 中金額與資源身分只存一筆，由重複表頭呈現於續頁。
第二筆 0 TWD 資源仍獨立保留，不改成缺答、不計算或改寫總額。

## 採用與不採用的試驗

先修改舊原生 Word 的副本診斷，沒有覆寫舊輸出：

| 試驗 | 結果 |
| --- | --- |
| 用途全寬，但仍是一個巨大的儲存格 | 仍不好分頁，續頁缺資源名稱 |
| 再重複資源表頭 | 可以辨認資源，但「資料管理預算」獨留第 8 頁，不採用 |
| 依原有段落拆成全寬列、重複資源表頭 | 標題能接到用途，但每段之間的橫線太密 |
| 原生 Lua 結構＋專屬無內橫線樣式 | 本輪採用，保留原文及原段落邊界 |

[失敗的全寬預覽](diagnosis/full-width-repeat.pdf)第 8 頁只有預算標題。
[有密集橫線的診斷](diagnosis/paragraph-rows-repeat.pdf)也保留供對照。
`diagnosis/` 全部是副本實驗，不冒充原生 DSW 成品；報告核對它們只改
`word/document.xml`。正式候選檔則重新經 DSW 產出，沒有事後修 DOCX。

## 實作與保護範圍

英文只改 `src/word/pilot.lua` 和 `scripts/prepare_layout.py`。Jinja、譯文、
PDF CSS、頁面、字級、行距及所有既有樣式不動。新增 `Pilot Long Budget`
表格樣式，沿用 Table 的基本樣式、明確複製表頭底色／粗體，移除內橫線。
Pandoc 的表格 custom-style 使用 reference 的 style ID `PilotLongBudget`，
不是帶空白的顯示名稱；原生 DOCX 核對引用正確，避免樣式設定看似存在卻沒生效。

長資源分成「原本欄名＋資源身分」兩列表頭，及原有用途的全寬列。相鄰短
資源仍維持三欄表格。不另加翻譯標籤、不改作者字句、不使用 LLM 或 JSON
轉檔。既有金額、用途、FAIR 支援項目、清單、檔名、粗斜體與連結全都保留。
Pandoc 在兩個表格間自動放一個空段落；只允許完全空的分隔節點，不放寬
到忽略任意文字、樣式或超連結。

完整表格先通過保護檢查才修改：三欄、單一表頭／body、1–32 筆資源、無
既有合併儲存格／表尾／caption；原本粗體名稱最多 160 寬度單位。金額欄
最多 80、經費來源最多 160 單位，最多三個段落單位，不能把長經費說明變成
巨大重複表頭。用途至少 12、最多 160 個單位才套用；每單位最多 800 寬度
單位，平面清單最多八項。CJK 碼位算兩單位。拒絕巢狀表格／清單、圖片、
強制換行、額外標題、未知樣式及其他不支援結構，保留舊 AST，不猜測內容。
這些是保守啟用條件，不保證任意字型、極端長單字及所有 Word 版本都完美。

## 驗證

- 英文 128、中文 105 項單元測試通過，TDK verify 通過。28 個新 Pandoc
  案例中 9 個允許指定結構轉換、19 個必須完整保留原 AST；涵蓋邊界值、
  同名但不同金額、多計畫、短長混排、連結／code 原值及複雜結構。原有
  24 個短預算探針亦通過，兩組都接進英中 CI。探針比較關閉新 handler 的
  對照；歷史整份模板另以實際 0.3.16 原生檔案驗證，不混為同一種證據。
- 三個案例的 fixtures 均沿用 0.3.16，沒有修改輸入。720 個翻譯單位、
  空白 0、translation／structure audit 無錯，八組翻譯探針通過；34 個
  Jinja binding 無未定義 UUID 或不存在 entity。這不是全問卷回答覆蓋率。
- 新產 18 份修補 worker 文件與 6 份原版控制文件，對照既有 24 份舊檔；
  合計 48 份 HTML／PDF／DOCX 與 16 份 Word 預覽。大 HTML 留在 outputs，
  檢查報告保留 hash；封存原生 PDF／DOCX、預覽、fixture sidecar 與 manifests。
- 120 題 HTML 全題 DOM 完全相同；原生 PDF 正文與頁數相同。短／八筆
  Word 正文 XML、文字、分頁完全相同，短中文仍維持第 15 題與小預算同頁。
- 長 Word 預算外的正文 XML 完全相同；第一筆名稱、金額、經費來源的段落
  XML 精確保留，用途區 64 個 XML 段落（包括 60 個編號段落及兩個清單項）
  原樣保留，第二筆整列 XML 相同。所有既有樣式相同，只新增一個表格樣式。
- 每個編號段落必須在唯一一頁完整出現，該頁也須同時有此資源的名稱、
  金額、經費來源及欄名。預算標題須接到名稱、首段用途與第一個編號段落，
  不能再獨留一頁。篡改文字、刪段、換金額、移除重複表頭或全寬設定都必須失敗。
- 原生 Word 的外部連結目標一致；另核對頁面邊界與預覽區塊內文字重疊，
  並重跑保存、共享、標點、容量、閱讀及品質六類既有檢查。

修補 worker 的同填答頁數，0.3.16 → 0.3.17；Word 欄是 LibreOffice 預覽：

| 案例 | 語言 | 原生 PDF | Word |
| --- | --- | --- | --- |
| 短控制組 | 英文 | 8 → 8 | 7 → 7 |
| 短控制組 | 中文 | 7 → 7 | 8 → 8 |
| 長篇用途 | 英文 | 13 → 13 | 12 → 10 |
| 長篇用途 | 中文 | 12 → 12 | 12 → 10 |
| 八筆預算 | 英文 | 9 → 9 | 8 → 8 |
| 八筆預算 | 中文 | 8 → 8 | 8 → 8 |

原版 worker 的短控制組，英中 Word 皆 7 → 7；仍有 4 筆作者 Markdown
表格轉換阻擋，沒有因其他檢查通過而取得發布資格。`tables/` 是既有隔離
修補 worker，`stock/` 是原版；新版兩者使用相同 ZIP。

人工看過中文第 7、8、10 頁、英文第 7–8 頁的頁面影像：預算標題有接到
第一筆用途，續頁表頭清楚，最後仍有 0 TWD 第二筆資源。英文第 10 頁仍
只有第二筆短資源（文字擷取確認），尾頁留白偏多；**這個剩餘問題沒有解完**。
原生長 PDF、超出保護範圍的長經費／複雜用途、整份中文語氣與 Microsoft
Word 實機均仍待驗收。這次不是把 10 頁當作理想排版的證明。

## 版本與重建

英中套件 0.3.17，短期 `feat/long-budget-reading` 承接上一輪，不新增永久
維護線。英文 `b7327b9e9fd976046fc440ec7bf5c82aac54b8ed`，原生產檔中文
checkpoint `5dc66c2c606e40f87f20eaa20e4e3d75e595bf04`；後續檢查器以報告
checksum 綁定。工具仍為 `25e339fbdfb1d20796471055790aad6a4226b6ed`，官方
基底仍是 1.30.1／`22d60aae4b63ee677477ac0c73097807284aaf9f`。

- 英文 ZIP：`263977cd228706b0772c3d34d0846240589bab7129868ae2fe6bff6724024211`。
- 中文 ZIP：`36f2b07611dcf37de44ec70744e0a319d5beb15b7cc30a8e6906054f2d0c1a3b`。
- 新原版／修補版：`outputs/build-udhlpyp1`／`outputs/runtime-tables-0ezjgab0`。
- 舊原版／修補版：`outputs/build-z3arhpbp`／`outputs/runtime-tables-0act9nn7`。

乾淨重建須與原生測試 ZIP 逐位元相同；source delta 檢查 Jinja／CSS 等
不變，建置 reference 的 ZIP 內也只有 styles.xml 新增專屬樣式。升級
upstream／Pandoc／reference 時須連同結構、style ID 與實際分頁一併驗證。
未合併 main、未建立正式 tag／release、未部署線上 DSW，未讀私人 project
或 keyring；只使用本機合成資料。下一個實驗宜處理長 PDF 及尾頁配置。
