# 0.3.18：長預算的分頁與留白

2026-09-15。只修局部樣式；合成資料、隔離 DSW 4.30、WeasyPrint 68.1、
Pandoc 3.8.3 與 LibreOffice。不是完整 DMP、Microsoft Word 或正式發布驗收。

## 先看成品

- [中文原生 PDF](tables/budget-long-chinese.pdf)：預算標題不再獨占一頁。
- [中文 Word 預覽](tables/word-preview/budget-long-chinese.pdf)、[可編輯 Word](tables/budget-long-chinese.docx)。
- [英文原生 PDF](tables/budget-long-english.pdf)、[英文 Word 預覽](tables/word-preview/budget-long-english.pdf)、[可編輯 Word](tables/budget-long-english.docx)。
- [短控制組](tables/word-preview/preservation-complete-chinese.pdf)、[八筆預算控制組](tables/word-preview/budget-many-chinese.pdf)。
- 同回答的 [0.3.17 對照](../2026-09-15-long-budget-reading/README.md)。

這是保留 60 個編號用途段落的壓力測試，不是要推薦使用者這樣撰寫 DMP。
本輪不翻譯或潤飾作者回答，不刪字、不縮字，也不把減少頁數當成品質證明。

## 兩個局部修正

PDF 的舊規則只看表格列數，兩筆資源即使包含數頁的用途，也要求整表不拆頁。
這會造成預算標題孤立、前頁大片空白。現在只對 Q15 資源用途有至少 12 個
直接 block 的表格，解除這項整表限制；短／八筆短用途控制組沿用原規則。
這不是所有長文字的判斷器：一個巨大段落及其他複雜內容仍需另外處理。

Word 沿用 0.3.17 的全寬用途、原段落／清單邊界和續頁資源資訊。只有專屬
`PilotLongBudget` 的上下儲存格邊距由每邊 57 twips（2.85 pt）改成 28 twips
（1.4 pt），避免每個段落都累加過多表格留白。字級 10.5 pt、行距 1.2、
一般段距、其他表格及表頭設定不變；不是事後手修匯出的 DOCX。

所有 Jinja、Lua、問題／回答結構、譯文、金額（含 0 TWD）、清單、檔名及
連結均不變。樣式由英文 repo 維護，中文仍走原有翻譯樹與精確英文 lock。

## 實測結果

同填答的 0.3.17 → 0.3.18；Word 欄為 LibreOffice 預覽：

| 案例 | 語言 | 原生 PDF | Word |
| --- | --- | --- | --- |
| 短控制組 | 英文 | 8 → 8 | 7 → 7 |
| 短控制組 | 中文 | 7 → 7 | 8 → 8 |
| 長篇用途 | 英文 | 13 → 11 | 10 → 9 |
| 長篇用途 | 中文 | 12 → 10 | 10 → 10 |
| 八筆預算 | 英文 | 9 → 9 | 8 → 8 |
| 八筆預算 | 中文 | 8 → 8 | 8 → 8 |

長篇 PDF 的預算從英文第 8 頁／中文第 7 頁開始，同頁有標題、資源、金額、
經費來源、首段用途及第一個編號段落，不再只有孤立標題。60 個編號段落各自
完整位於唯一一頁。Word 的長用途仍在英文第 7–9 頁、中文第 7–10 頁，
最後一筆短資源與末段用途同頁；英文原本只放第二筆短資源的第 10 頁消失。

另有原版 worker 的短控制組：英中 Word 都維持 7 頁。最終新產 24 份
HTML／PDF／DOCX，與 24 份舊版對照，共 16 份新舊 Word 預覽；前述失敗嘗試
不計入通過結果。[原生對照報告](tables/budget-spacing-report.json)及
[原版控制報告](stock/budget-spacing-report.json)記錄逐項判定與檔案 hashes。

已看過原生中文 PDF 第 7、8 頁、英文 PDF 第 8 頁，以及英文 Word 第 9 頁、
中文 Word 第 10 頁的影像。標題有接到用途、第二筆預算保留；PDF 續頁仍有
兩個空的右側欄位，Word 中文尾頁也仍有留白，沒有宣稱整份閱讀品質完成。

## 檢查與失敗對照

- 英文 130、中文 110 項測試及 TDK verify 通過。原有 24 個短預算、28 個
  長預算 Pandoc 探針通過；新增 8 個 PDF 引擎探針（3 個命中、5 個不命中），
  核對真正的 selector matching 與 computed `break-inside`，已接入雙 repo CI。
- 初次 native 嘗試發現 `:has(> tbody > ...)` 在 SoupSieve 命中，卻不在
  固定 worker 的引擎命中。英文 `2f5f2ac` 的原生 PDF 因此沒有改善，
  `outputs/build-zyfm6ims`／`outputs/runtime-tables-rr1sec5p` 保留，長篇驗收
  明確失敗。修正為 `:has(tbody > ...)`，重新建置、完整重跑，沒有沿用假成功。
- 本機服務中途停止的 `outputs/runtime-tables-wqmxvyxz` 沒有成功產檔，
  另留連線失敗紀錄；不是模板內容失敗，也不作為通過證據。
- 原生 PDF 的英文封面／章節標題有兩處字型量測框交疊，旧新版的文字及交疊
  大小完全一致。檢視影像未見字形互壓；報告保留這兩處，要求不得新增／改變。
  量測框不是字形輪廓，不能把 Word 預覽檢查直接當成 PDF 的視覺判決。
- PDF 正文用 layout extraction 保序比對，只去掉精確表頭列及已核實頁碼；
  段落是否完整在同一頁則用 raw extraction，避免跨欄文字交錯把經費來源
  拆開。Word 仍核對每個用途段落所在頁皆有同筆名稱、金額、經費來源與欄名。
- 720 個翻譯單位，空白 0，translation／structure audit 無錯，8 組翻譯探針
  通過；34 個 Jinja 的 KM binding 無未定義 UUID 或不存在 entity。
- 最終報告要求新旧 fixtures 的 recipe、events、KM hash 相同，120 題 HTML
  DOM 相同，Word Q1–Q15 正文 XML 與外部連結完全相同；所有 reference styles
  只能多出指定的 28-twip 邊距。短／多筆控制組文字及分頁不得改變。
- 保存、共享、標點、容量、閱讀、品質六類檢查也重跑。各項通過只涵蓋本批
  合成資料，不表示 Science Europe 的全部問答語意已驗收。

## 還沒有解掉的問題

原生 PDF 的用途仍放在三欄表格的第一欄，續頁還沒有帶出資源名稱／金額／
經費來源；本輪解除錯誤的整表分頁限制，**沒有把 PDF 改成 Word 的全寬版型**。
下一輪應獨立實驗這個結構問題，並保護原文及各筆歸屬，不以縮字或 LLM 重寫補救。
中文 Word 頁數沒有減少，不是失敗；最後頁的閱讀節奏、真實案例、中文語氣及
Microsoft Word 實機仍須審閱。

`stock/` 是原版 worker：短控制組保留 4 筆 Markdown 表格能力阻擋紀錄，
仍不得正式發布。`tables/` 是已存在的隔離修補 worker 實驗，不是線上部署。
兩者使用同一組 ZIP。沒有讀取 keyring 或私人專案，沒有改線上 DSW。

## 版控與重建

英中 0.3.18，短期 `feat/budget-spacing` 承接 0.3.17，不新增永久版本分支。
英文 `0945a807870b0b74e3e5c09301e46f2ac15922b4`，原生產檔中文 checkpoint
`1a13e51598790ee44d40d20e265a9a3f06e08c7c`。工具維持
`25e339fbdfb1d20796471055790aad6a4226b6ed`，官方基底仍是 1.30.1／
`22d60aae4b63ee677477ac0c73097807284aaf9f`。未合併 main、未建立 tag／release。

- 英文 ZIP：`5450cfffa106a7912c5473306036edef3d58ae59d08c7b61c9568420ba78352c`。
- 中文 ZIP：`58bb9a1b5950852489b568c833a4aa725b22721081e496c8e13a04d2876ce4f0`。
- 原版：`outputs/build-yn1voepv`；修補版：`outputs/runtime-tables-snbp9ayf`。

乾淨重建須與原生測試 ZIP 逐位元相同。source delta 僅允許建置來源中的
`layout.css` 及 `word/reference.docx` 改變；reference ZIP 只准 styles.xml
發生上述局部差異。本次不重複保存舊版二進位檔：核對前輪封存的 hashes 後引用，
新檔、報告與來源差異仍完整封存。大 HTML 在 outputs，報告保存其 hash。

未來 upstream／worker／Pandoc 升級先進獨立 `upgrade/**` 分支，再重跑原生
同填答對照及引擎探針；不能只看到 Git 沒有衝突就接受。中文不再移植一次樣式，
只更新英文 lock、翻譯檢查及重建。分支整合與正式發布仍須另行確認。
