# 計畫、資源與軟體：提交預覽中性名稱原型

這是 **0.3.44 套件上的局部原型**，不是新版正式套件。英文／中文各改五個 Jinja 檔、
七處來源位置，尚未接回英文來源與翻譯樹；CSS、字型、Lua、reference DOCX、
格式 UUID、metadata／版號與轉換步驟均不改。沒有正式 DSW 上傳或 release。

## 成品與規則

- [中文提交 PDF](after/renders/entity-labels-submission-chinese.pdf)、[中文 Word](after/renders/entity-labels-submission-chinese.docx)、[LibreOffice 預覽](after/word-preview/entity-labels-submission-chinese.pdf)
- [英文提交 PDF](after/renders/entity-labels-submission-english.pdf)、[英文 Word](after/renders/entity-labels-submission-english.docx)
- [中文檢核 PDF](after/renders/entity-labels-review-chinese.pdf)、[英文檢核 PDF](after/renders/entity-labels-review-english.pdf)

這些都是公開合成測試資料，不是真實計畫，也不是示範一份已完成的 DMP。

計畫名稱漏填時，在概要、第 9 題倫理審查、第 15 題經費段落使用同一個「計畫 N」。
編號來自原問卷清單位置；第一個計畫沒有倫理回答，第二個在倫理段落仍是「計畫 2」。
資源在各自計畫內編號，軟體在各自資料集內編號，不把不同清單的第二項當成同一項。
若使用者日後真的調整問卷清單順序，編號隨新順序變動；這不是永久識別碼。

只更換系統擁有的名稱佔位文字，不解析 PDF 後替換字串。新標籤使用純文字宏，
避免額外 span 讓既有長表格／短列的排版分類失效。兩種語言、兩種 escape、兩種
PDF／Word 排版分支、65 組既有案例與一組新增案例、名稱原樣／全漏填變體，
合計 **1,056 組**結構比對。檢核／預設／未知模式均與原版逐字相同。

## 原生檢查

新增案例包含三個計畫、兩組資源清單、兩個資料集與兩組軟體清單。
原型在每種語言的提交版各替換十處名稱。以下是同模式修改前 → 修改後，
不是把模式差異誤稱為本次縮頁效果。

| 語言／模式 | 原生 PDF | Word 的 LibreOffice 預覽 |
|---|---|---|
| 英文檢核 | 7 → 7 | 5 → 5 |
| 英文提交 | 4 → 4 | 4 → 4 |
| 中文檢核 | 6 → 6 | 6 → 6 |
| 中文提交 | 4 → 4 | 4 → 4 |

四組原生前後比對共 **24 份 HTML／PDF／DOCX 與 8 份 Word 預覽**。
檢核版 HTML 位元組、DOCX 組件（僅允許經驗證的建立／修改時間）、PDF／Word 預覽
逐頁座標及影像不變。提交版以問卷 identity 對照獨立 DOM oracle；全文字元、標點、
段落、網址、Word 樣式與編號定義保留，沒有文字越界或增加碰撞篩檢項。
這不是通用 PDF 語意解析或 Microsoft Word 原生驗收。

已目視中文軟體、資源、倫理頁，英文資源頁，以及中文 Word 資源頁；影像見 `visual/`。
短資源列與所屬計畫保持可辨識，沒有為名稱替換增加空白頁或拆散表格。

## 不能誤判的測試文字與未完成事項

- 資源第一列的「（尚未填寫資源名稱）」／`(no resource name given)` 是刻意填入的
  **實際名稱**，必須保留；第二列才是名稱真的漏填，因此顯示「資源 2」。
- 第三個軟體的實際名稱刻意叫「軟體工具 2」／`Software tool 2`，所以會與第二個
  系統標籤同名；仍依原問卷項目及不同網址區分，不能擅改使用者的名稱。
- `N/A`、0、Original.csv、AUTHORED 標記與計畫摘要中的「尚待補充」也是已填內容。
- **第 9 題仍有系統產生的「尚未說明是否包含個人資料或敏感資料。」提示**，
  是本案例新確認的未標記分支；原版即存在，本次名稱原型沒有隱藏它。不能宣稱全域
  提示切換完成，應另做明確來源分支／所有回答狀態的回歸驗證。
- 人員名稱、未命名資料格式、空經費項目、空計畫預算標題與 ORCID 解析未處理。
  本輪也沒有改善全部中文語氣、CJK 標點視覺間距、短資料集跨頁或第 9 題重複文字。

## 環境事件與清理

第一次原型原生輸出因**本機 DSW 配額**失敗：HTML 需要 15.96 MB，當時只剩 11.99 MB。
不是硬碟滿，也不是 Jinja 例外。保留失敗報告與 log，不改寫成通過。
只將隔離環境的 storage 欄位從 -1,500,000,000 暫調為 -1,750,000,000；worker 以
絕對值執行限制。成功後已還原原值，其他 limit 欄位逐欄比對未變。

只移除本輪基準兩個、失敗一個、成功原型兩個暫存模板；刪除前確認沒有 project／document
引用並保留本機 ZIP 備份。未刪除其他模板、歷史產物、MinIO 物件或 volume。worker 已還原
stock image，四個 pilot service 均停止。相關證據見 `provenance/` 與兩側 cleanup receipts。
另一次套件建置曾在重新讀取被 zipfile 修改的 ZipInfo CRC 時失敗，未匯入服務；已修正為
寫入前計算來源 digest。成功套件逐 member 比對僅 template/template.json 改變。

## 重現與後續整合

使用 repo 內 `experiments/entity-labels/` 的 recipe／probe／trial／native／collector；
`reproduce/` 保存當時程式副本供稽核，並非脫離 repo 即可執行的獨立工具。
`checksums.json` 是一次性封存，**不得改寫或重新封存**。

原始輸入來自已凍結的 `2026-09-21-submission-preview-integration`：EN `41bb0ac`，
中英配對 0.3.44；本輪使用 ZH `7678935` 乾淨建置，套件位元組與該原生 archive 相同。
EN ZIP SHA256 為 `930cbfa5f19d3236341b23ae2b288f65cdb845732f4d1c7fbf50268ce0735a0c`，
ZH 為 `dbe2b058cb7bac9d14dcf149cb44c7d1d253144417e99ac7c6d9b2338d1fb3b9`。
原型仍用同版號，但只能在 runtime-experiment 路徑，不得拿去覆寫正式版本。

HTML 封存只將內嵌公開字型換成雜湊引用，保存原始 HTML 雜湊及每字型大小／次數；
這份 compact HTML **不是 PDF 渲染輸入**。PDF／DOCX 不改動。KM bundle 不重複封存，
recipes、events、KM 雜湊及本機驗證結果保留；重新跑原生需提供雜湊相同的公開 KM。
頁面產生日是 2026-09-21；另日重現不得直接移除日期差異冒稱逐頁完全相同。

下一階段仍是英文來源 → 既有翻譯流程 → 翻譯增量審核 → 新配對版本 → 中英兩模式
原生比較；不建立永久中英文 Jinja 分岔，也不建立 review/submission 永久分支。
