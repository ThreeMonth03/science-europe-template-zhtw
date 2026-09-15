# 0.3.15：識別碼追問的缺答提示與回答保留

2026-09-15。本文件另封存於 `reviews/2026-09-15-identifier-followups/README.md`，
下列相對連結以封存目錄為準。這是合成資料、隔離 DSW 與 LibreOffice 預覽
實驗，不是正式發布、完整 Science Europe 或 Microsoft Word 實機驗收。

## 樣張

- 四個管道的缺答／否定組合：[中文 PDF](tables/identifier-followups-chinese.pdf)、
  [Word](tables/identifier-followups-chinese.docx)、
  [Word 預覽](tables/word-preview/identifier-followups-chinese.pdf)。
- 同填答舊版：[中文 PDF](prior-tables/identifier-followups-chinese.pdf)、
  [Word 預覽](prior-tables/word-preview/identifier-followups-chinese.pdf)。
- 完整填答控制組：[中文 PDF](tables/preservation-complete-chinese.pdf)、
  [Word](tables/preservation-complete-chinese.docx)、
  [Word 預覽](tables/word-preview/preservation-complete-chinese.pdf)。
- 英文缺答：[PDF](tables/identifier-followups-english.pdf)、
  [Word](tables/identifier-followups-english.docx)。
- 原版 worker：[中文缺答 PDF](stock/identifier-followups-chinese.pdf)、
  [Word](stock/identifier-followups-chinese.docx)。

`tables/` 使用既有隔離表格修補 worker，`stock/` 是原版；新版兩者使用相同
ZIP。舊版 0.3.14 套件原封不動複製到新的重播目錄，以同一批填答重新產檔，
沒有覆寫上一輪 outputs 或審閱封存。重播 manifest 的 checkouts 是原套件
建置紀錄，另有 artifact_replay 記錄來源與校驗碼，不冒充本輪重建舊 source。

## 修正內容

Q13 選擇「會指派持續識別碼」後，兩個追問分別是「誰會指派」與「儲存庫
是否確保識別碼可解析至數位物件」。本機編譯的英中 Common KM 2.7.0 已核對
這三個題目、選項及父子關係，詳見 `contract-audit.json`；新 fixture 也通過
路徑／選項可達性驗證，不是只根據 Jinja 變數名稱猜測問題意思。

| 輸入狀態 | 文件行為 |
| --- | --- |
| 三種已知指派者 | 保留原本指派敘述，狀態 complete |
| 明確保證可解析 | 保留肯定敘述，狀態 complete |
| 明確不保證可解析 | 保留否定敘述，狀態 explicit-no；不改成「無法解析」 |
| 未填或只有空白 | 顯示「尚待補充」，狀態 missing |
| 非空白、模板不認得的選項 | 顯示「無法判讀……請核對」，狀態 needs-review |

兩欄獨立判斷，漏填其中一欄不會吞掉另一欄。同一管道兩欄皆漏填時合成
一段提示，以頓號串接欄位、只保留一個結尾句號；缺答與未知選項若並存，
則分成兩段不同意義的提示，不混稱為漏填。未知原值不直接回顯，也不把
前後多空白的 UUID 自動修成有效答案。

已填政策維持 0.3.14 的連讀段落；提示緊接其後、位於 dataset-policy 外。
不為每個缺欄新增標題或清單。父題否定、未填、未知或不發布時，不輸出
殘留的子答案或子題提示。每個資料集／管道依 UUID 分別處理，不用名稱去重。

人工翻看第一版英文 PDF 時發現：管道 3 的回答在第 7 頁，但提示被擠到
第 8 頁。此版本沒有採用；[保留的失敗樣張](rejected/identifier-followups-english.pdf)
可直接對照。最終在政策與提示外加一個 `identifier-followup-unit short-reading-unit`，
重用既有短閱讀區塊規則。只有固定模板句，oracle 逐組檢查不超過 500 字元且
不含作者段落、清單或表格；不把整題或多個管道鎖成不可分頁的大區塊。
Word 只對區塊中非末段套用既有 Pilot Lead，最後提示不牽連下一個管道。
PDF／Word 預覽改查「標籤＋整段政策＋所有提示」同頁，不再只查第一句。
同一檢查也必須拒絕留存的失敗 PDF，詳見 `followup-source-delta.json`。

新增 `identifier-assigner`、`identifier-resolution` 事實標記，對應既有
SE-5d。父題 `persistent-identifier/complete` 只表示填了「會指派」的決定，
不代表追問或整份 Q13 完整。此映射也不代表每個答案都已滿足資助單位的實質
要求；本輪修的是忠實呈現與可見缺答，不是自動評定 DMP 合規。

只有英文 Q13 Jinja 修改。中文字句透過原有翻譯樹產生，新增四個譯文單位；
其餘詞句沿用已審閱內容。重新抽取後有四個舊單位因結構／位置變動需重套
既有審閱字串，沒有讓未翻文字混入成品。最終 720 單位，空白 0，translation／
structure audit 均無錯誤。CSS、Word Lua、reference、字型、頁面、問卷標題、
其他十四題與既有 fixture 不變；不改寫作者原文，不使用 JSON／LLM 摘要。

## 驗證範圍

- 英文 121、中文 95 項測試通過，英文 TDK verify 通過；8 個新英文測試及
  6 個新檢查器測試涵蓋分組、狀態、殘留子答案、同名資料集、不准刪改原文
  及提示跨頁時必須失敗。
- Q13 探針 1,136 組分支／語言檢查，另維持 1,176 次既有政策固定句比對；
  新獨立狀態 oracle 核對兩欄語意、提示文字、標點與歸屬。原有七類探針亦
  通過。未知 UUID 與惡意字串是離線健壯性測試，不冒充 KM 可接受的實際選項。
- 34 個 Jinja 的靜態 binding 稽核無未定義 UUID 變數或不存在 entity。它不是
  全問卷內容覆蓋率；原文問題與新 fixture 的實際 KM 查核另外留證據。
- 新舊版 × 原版／修補 worker × 二案例 × 二語言 × 三格式，共 48 份新產的
  HTML／PDF／DOCX，另有 16 份 Word 預覽。完整控制組和四管道缺答案例使用
  相同填答比對，不能拿不同內容文件的頁數直接比較。
- 每個 worker 嚴格比較 60 題，合計 120 題：只還原新提示、短區塊及兩種子題標記，
  再核對全題 DOM、文字、原文區塊、事實與歸屬。其餘十四題 HTML 相同。
- Word 全正文段落／樣式／keep 屬性與所有表格儲存格比較，只允許在指定
  管道政策後插入經驗證的提示段落及套用區塊內非末段的 Pilot Lead。
  完整組增加 0 段且樣式不變；缺答組增加 3 段。
  缺答組每語言為 4 個 missing、2 個 complete、2 個 explicit-no 子題事實。
- PDF／Word 預覽從第一題起的全文比對，只移除 Q13 中精確的新提示並正規化
  空白／可驗證頁碼，其他標點、檔名與文字不得改動；另查標籤、整段答案與提示同頁、
  Q13 沒有純標點行、實體頁面邊界與預覽區塊內文字重疊。
- 繼續檢查既有 Q11 論文原值及 PDF／Word 的連結目標；原版仍有 8 筆既知
  Markdown 表格阻擋，不能藉其他檢查通過而取得發布資格。

頁數如下，箭頭為同填答的 0.3.14 → 0.3.15。兩種 worker 的原生 PDF 頁數
相同，Word 欄則是 LibreOffice 轉出的預覽，不冒充 Microsoft Word 實機頁數。

| 案例 | 語言 | 原生 PDF | 原版 worker 的 Word 預覽 | 修補 worker 的 Word 預覽 |
| --- | --- | --- | --- | --- |
| 完整控制組 | 英文 | 8 → 8 | 7 → 7 | 7 → 7 |
| 完整控制組 | 中文 | 7 → 7 | 7 → 7 | 8 → 8 |
| 四管道缺答 | 英文 | 8 → 9 | 7 → 7 | 8 → 8 |
| 四管道缺答 | 中文 | 8 → 8 | 8 → 8 | 8 → 8 |

人工以頁面影像檢視修補版中文缺答 PDF／Word 的第 7 頁、英文 PDF 的第
7–8 頁與 Word 第 7 頁，並比對舊版中文第 7 頁及原版 worker 的新版頁面。
這些頁面中的三段提示均留在正確管道，沒有提示單獨跑到下頁、純句號行或
文字相疊。PDF 使用既有提示底色，Word 使用分開的文字段落，並非輸出遺漏。
英文缺答案例多一頁是新提示占用空間的結果，沒有為了壓頁數縮字或刪回答。
完整中文 Word 第 8 頁仍主要只有預算表，人工確認此已知問題未解；本輪不
宣稱整份文件的節奏已理想。全文中文潤稿與 Microsoft Word 仍須另外驗收。

## 版本、重建與剩餘問題

英中套件版本 0.3.15，工作分支 `feat/identifier-followups` 承接 0.3.14；
沒有新建永久維護線。英文 `b1391c059c23c97095b8c748d527d13516c8a74f`，實際產檔
中文 checkpoint `ef218d2a71d374388ae67cc19c6da1e9470b0248`；後續查核程式以
checksum 綁定。工具仍為 `25e339fbdfb1d20796471055790aad6a4226b6ed`，官方基底
仍是 1.30.1／`22d60aae4b63ee677477ac0c73097807284aaf9f`，未假裝升級官方版。

- 英文 ZIP：`7f16e2a52b48ffc85a0209b8690f7a0deddf441ad8ee3f90fa8b3428deb40715`。
- 中文 ZIP：`24949e6b6ea8a2b2cd5800f682d2302308b48efd5ee5d99d80d645739c3aeb7d`。
- 新原版／修補版：`outputs/build-o68nfhmu`／`outputs/runtime-tables-ufroz416`。
- 舊版重播：`outputs/baseline-followups-hijs64gd`／`outputs/runtime-tables-40kvjz0i`。

封存 PDF、DOCX、Word 預覽、fixture sidecar、manifest、報告與 checksum；
巨大內嵌字型 HTML 保留於 outputs，報告記錄完整 hash。乾淨重建須產出相同
ZIP；來源差異只允許 Q13，其他 src 包含 CSS／Lua／reference 逐位元相同。
未來上游升級須重驗追問父子關係、缺答／未知／否定區別與英中提示分組，
不能只以 Git 無衝突或 CI 通過判定成品相容。

尚未處理：中文 Word 的預算尾頁、Q13 未知儲存庫類型提示、其他尚未涵蓋的
問卷分支、全文中文潤稿及實際 Word 開啟環境。完整 DMP 與去識別真實專案
仍需驗收；表格修補 worker 的正式部署／回退責任也未驗收。

未合併主線、未建立正式 tag／release、未部署線上 DSW，沒有讀取 keyring
或線上 project。測試後恢復原版 worker 並停止本機容器，保留資料卷及歷次樣張。
