# 0.3.19：PDF 長篇用途全寬與續頁歸屬

2026-09-15。隔離 DSW 4.30、WeasyPrint 68.1、Pandoc 3.8.3、LibreOffice，
只使用合成回答。不是正式發布、完整 DMP 或 Microsoft Word 驗收。

## 先看成品

- [中文原生 PDF](tables/budget-long-chinese.pdf)：第 7–9 頁。
- [英文原生 PDF](tables/budget-long-english.pdf)：第 8–10 頁。
- [中文 Word](tables/budget-long-chinese.docx)、[Word 預覽](tables/word-preview/budget-long-chinese.pdf)：正文與分頁沿用前版。
- [短篇控制組](tables/preservation-complete-chinese.pdf)、[八筆預算控制組](tables/budget-many-chinese.pdf)。
- 同填答的 [0.3.18 對照](../2026-09-15-budget-spacing/README.md)。

60 段編號用途是保留答案與跨頁的壓力測試，不是理想 DMP 寫作示範。
本輪不潤飾作者原文，不縮字，不合併作者段落來減頁。

## 修改範圍

英文共用 Q15 仍負責同一套回答、缺答、金額與資源歸屬。原始標題、用途、
金額、經費來源各擷取一次；僅 PDF 新入口啟用呈現旗標。符合條件的長篇
資源改為全寬用途，上方兩列保留原欄名與資源資訊，跨頁由引擎重複。
短項目仍用三欄表格；同名資源依完整 item path 區別，不重複計算經費。

新 `budget-reading.html.j2` 沒有可翻譯句子或 KM UUID。HTML、Word、ODT、
LaTeX 入口、Word Lua／reference、字級、行距與頁邊界都不改。中文仍由
客製英文走既有翻譯管線，不維護第二套中文分支判斷。

保守界線：每計畫至多 32 筆資源，12–160 個用途／支援項目段落，每段
至多 400 字元，純文字合計至多 30000 字元；至多一個八項以內簡單清單。
名稱／金額／經費文字限 80／80／100 字元與簡單標記。圖片、巢狀表格、
複雜清單、換行標記、過長或帶連結的經費來源、缺少必要資料等保留原列。
這是有限排版提示，不是通用 parser；不保證所有長回答都已改善。

## 同填答結果

| 案例 | 語言 | PDF 0.3.18 → 0.3.19 | Word 預覽 |
| --- | --- | --- | --- |
| 短控制組 | 英文 | 8 → 8 | 7 → 7 |
| 短控制組 | 中文 | 7 → 7 | 8 → 8 |
| 長篇用途 | 英文 | 11 → 10 | 9 → 9 |
| 長篇用途 | 中文 | 10 → 9 | 10 → 10 |
| 八筆預算 | 英文 | 9 → 9 | 8 → 8 |
| 八筆預算 | 中文 | 8 → 8 | 8 → 8 |

原版 worker 另有英中短控制組：PDF 英文 8／中文 7 頁，Word 都是 7 頁，
亦與前版一致。共新產 24 份 HTML／PDF／DOCX、8 份 Word 預覽。
兩個 worker 使用相同 ZIP；原版仍有四項 Markdown 表格相容性阻擋。

長篇 PDF 的 60 段用途各自完整、唯一、單行出現；全文序列保留用途引言、
清單、支援項目、第二筆短資源與 0 TWD。中文第 7／8／9 頁與英文第
8／9／10 頁都有原資源名稱、5000 TWD、經費來源。PDF 外部連結目標和
連結文字不變；Word Q1–Q15 XML、段落、外部關聯、styles.xml 與分頁不變。
120 題 HTML 比較只允許已核對的中文模板自有「支援項目」外緣縮排差異。

已看過上述六頁原生 PDF 影像：用途不再擠在第一欄，續頁資源清楚；末尾
清單、連結與第二筆資源保留。英文尾頁仍只有最後一段用途與短資源，中英
尾頁均有留白。不能把少一頁當成整份閱讀品質完成。

## 翻譯與驗證

- 翻譯樹由 720 變成 722 單位，空白 0。首次重抽有 8 個單位未能自動沿用，
  核對後接回原譯文。[遷移證據](pdf-budget-translation-proof.json)精確比較
  舊 commit 的全部 sentence／translation pairs：原有 720 組不改，新增兩組
  僅是既有幣別分支重複。不把這項比對當成中文語氣評分。
- 中英各 28 組 Q15 結構案例，含閾值、零元、缺答、同名、多計畫、混合列、
  32／33 筆、連結與複雜內容回退。英文固定引擎驗證用途寬度超過頁面內容
  的 90% 與重複表頭；中文實際字型以 native 產檔驗證，不用診斷 HTML 代替。
- 英文 133、中文 117 項測試及 TDK verify 通過。八組翻譯探針、24 個短 Word、
  28 個長 Word、8 個 PDF CSS 引擎案例通過。36 個 Jinja binding 沒有未定義
  UUID 或不存在的 entity；translation／structure audit 無錯。
- 保存、共享、標點、容量、閱讀、品質六類 native 檢查重跑；
  [同填答報告](tables/pdf-budget-reading-report.json)與
  [原版控制報告](stock/pdf-budget-reading-report.json)綁定套件與成品 hash。
- `pdftotext -raw` 將外側清單圓點列在頁末，不等於畫面錯位。僅對這個已知
  沒有作者字面圓點的案例，排除經 bbox 數量核實的頁尾符號；另驗證兩個
  預算清單圓點與原項目在同一行。作者字面圓點、非頁尾符號、錯位、漏字
  或重複文字均不能被這個例外掩蓋；不得直接套用到一般回答。
- 英文原有兩處字型量測框交疊與前版完全相同，中文無此情況。量測框不是
  字形輪廓；Word 預覽另核對行框，不宣稱這些檢查等於完整視覺評分。

## 版本與升級

英中 0.3.19，短期 `feat/pdf-budget-reading` 承接 `feat/budget-spacing`；
不是永久版本分支，未合併 main、未建 tag／release、未修改線上 DSW。
英文 `62338c59135d6067f492116964d58e31928a5d5a`，原生產檔中文 checkpoint
`bd7976d7cfa38313d30e3d11b0bfd8fb12e43d53`，工具仍為
`25e339fbdfb1d20796471055790aad6a4226b6ed`。官方基底仍是 1.30.1／
`22d60aae4b63ee677477ac0c73097807284aaf9f`，不是全面升級 upstream。

- 英文 ZIP：`ed4e79220b558adf0452a8ffd4c353458796cc48f352133a274fcbafe98f01f7`。
- 中文 ZIP：`c3601525adde55bd6a9c633f909f7e75ce282ecf88a9fa5db8c7b5ee59c792bc`。
- 原版 `outputs/build-yws03af7`；修補版 `outputs/runtime-tables-bvqnw9bt`。
- 乾淨重建 `outputs/build-wkiygn0v`：相同 ZIP 逐位元一致。

下一次 upstream 修改 Q15，要一起審查片段擷取的 namespace scope、PDF
helper／入口、資源歸屬與翻譯重分組。金額不能改回會被外層 set capture
隔離的區域變數。升級先進 `upgrade/**`，通過內容、翻譯、native 同填答
與引擎回歸，再更新中文 lock；不只解 Git 衝突，也不在中文重做一次樣式。
大型 HTML 保留在 outputs；本封存記錄其 hash，舊二進位以核實的前輪封存引用。

## 下一步

應回到接近真實 DMP 的篇幅，審閱整份中文的段落節奏與語氣，再增加混合
長短資源的 native 案例，不能只調整 60 段壓力測試。長尾頁、複雜資源、
Science Europe 內容覆蓋、真實專案及 Microsoft Word 實機仍須分別驗收。
模板固定翻譯與作者回答分開處理，不用執行期 LLM 改寫原文。

worker 已還原；本輪使用的四個本機服務停止後資料卷仍保留。未讀 keyring
或私人專案，未部署。原版 worker 的 Markdown 表格相容性仍阻擋正式發布。
