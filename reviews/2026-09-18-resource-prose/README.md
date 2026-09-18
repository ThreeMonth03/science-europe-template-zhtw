# 句號位置與短段落：0.3.40 上的診斷實驗

這輪確認兩件不同的事：Q15 指定句子的「句號前空白」並不是真正多了空白字元；
兩個很短的固定敘述各自成段，則可以改善。模板仍為 **0.3.40**，沒有發布新版。
本目錄是離線 PDF／修改原生 DOCX 的 A/B 診斷，不是新版 DSW 原生輸出。

## 先看樣張

| 語言／模式 | 合段 PDF 診斷樣張 | 合段 DOCX 診斷樣張 | Word 預覽 |
| --- | --- | --- | --- |
| 中文提交 | [PDF](trials/profile-partial-submission-chinese-joined.pdf) | [DOCX](trials/profile-partial-submission-chinese-joined.docx) | [PDF](trials/word-preview/profile-partial-submission-chinese-joined.pdf) |
| 中文檢核 | [PDF](trials/profile-partial-review-chinese-joined.pdf) | [DOCX](trials/profile-partial-review-chinese-joined.docx) | [PDF](trials/word-preview/profile-partial-review-chinese-joined.pdf) |
| 英文提交 | [PDF](trials/profile-partial-submission-english-joined.pdf) | [DOCX](trials/profile-partial-submission-english-joined.docx) | [PDF](trials/word-preview/profile-partial-submission-english-joined.pdf) |
| 英文檢核 | [PDF](trials/profile-partial-review-english-joined.pdf) | [DOCX](trials/profile-partial-review-english-joined.docx) | [PDF](trials/word-preview/profile-partial-review-english-joined.pdf) |

中文提交 Word：[原先第 5 頁](visual/word-before-chinese-submission-p5.png)、
[合段後第 6 頁](visual/word-after-chinese-submission-p6.png)。
各樣張的 `baseline` 版本保留在同一目錄；原生基準另存 `native-baseline/`，
不可把兩者混稱為新版原生樣張。

## 句號診斷：修正先前的說法

對中文檢核／提交兩種模式，逐一比對這兩句的原生 HTML、Word 段落及 PDF 文字：

> 除機構通常提供的資源外，我們不需要其他硬體或軟體。
> 預計使用的資料儲存庫會收取服務費。

三種格式的文字相同，句號前沒有空白字元。原生 PDF 也顯示整句使用 `Pilot-CJK`，
不是只有句號落入另一套西文字型。來源 Noto Sans TC 字型的預設實例中，
「。」字框寬 1,000 units，墨跡的 x 範圍是 360–646，顯示其置中位置；
這是來源字型預設 weight 100 的測量，不是重建 PDF 內嵌字形的精確外框。

臺灣常見的點號採全形字框內置中配置，與這個觀察一致。
參考 [W3C 中文排版需求：標點符號的位置](https://www.w3.org/International/clreq/#positioning_of_punctuation_marks)。
因此不使用全域刪空白、改半形句號或負字距來「修正」這兩句。
這也不代表其他題目絕無真正的多餘空白；結論只涵蓋已列出的文字。
完整字元、來源雜湊及字型量測見 [punctuation.json](provenance/punctuation.json)。

## 短段落實驗

只把「不需額外軟硬體」與已知的「儲存庫收費／不收費」兩句固定敘述合成一段。
不改任何字詞或標點；英文句間加入一個正常空格，中文直接接續。
培訓自由回答、清單、預算、其他問題、漏填提示均不合併。

HTML 保留原本硬體事實屬性，為收費句加入獨立的 span 事實標記。
Word 只合併兩個連續且同樣式的純文字段落；所有原文字 run、樣式、字型、
連結及其他 ZIP 部件保留。遇到不同樣式、書籤、欄位或未知文字即不套用。
這些中英句子在診斷程式中是有限的比對常數，不是另起兩套正式模板。

| 結果 | 中文 | 英文 |
| --- | --- | --- |
| 指定兩句的段落數 | 2 → 1 | 2 → 1 |
| PDF／Word 的行數 | 2 → 1 | 2 → 2，少一段段落間隔 |
| 四份部分漏填文件各自總頁數 | 6 → 6 | 6 → 6 |
| 提交 Word 的 Q15 標題／預算標題 | 第 5／6 頁 → 同在第 6 頁 | 原本及合段後均第 6 頁 |

其他三份目標 Word 的 Q15 也維持同頁，四份目標 PDF 維持第 6 頁。
這是局部改善，不是減少總頁數；中文提交 Word 的留白改分配到前一頁。

## 驗證範圍與限制

- 部分漏填／全空 × 中英 × 檢核／提交，共 8 組、每組 baseline／joined 兩版。
  產出 16 份離線 PDF、16 份 DOCX 及 16 份 LibreOffice 預覽。
- 4 組部分漏填各合併一處；4 組全空原樣保留。全文及標點保留，成對比較的
  Q15 之前所有文字座標相同、頁數不增，沒有新增行框重疊偵測警告。
  原有英文 PDF 的警告仍在，不能據此聲稱全篇零重疊。
- 8 份 Word baseline 的預覽座標均與原生 DOCX 的既有預覽相同。
  Word 只證明 LibreOffice 行為，未實測 Microsoft Word。
- **2 份中文檢核 PDF 的離線 baseline 與原生基準不同**：部分漏填與全空
  都有字型／座標差異；部分漏填的原生 PDF 多了 `Pilot-CJK-Semi-Bold`。
  其餘 6 份 baseline 的字型與座標相同。每組離線 A/B 內部字型及前文座標
  相同，但不能把中文檢核的成對比較當作原生驗收，也未查明此差異的根因。
- 沿用原有 PDF 短 Q15 的連頁提示；實驗才將原本已符合條件的提示帶至合段版。
  正式 helper 尚不認識新增 span，沒有放寬它的判定。這是尚未接回模板的另一原因。
- 人工檢視 8 份目標合段 PDF／Word 預覽的 48 頁概覽，以及中文提交目標頁細圖。
  不代表全空控制或所有可能回答都已逐頁人工驗收。

數值見 [成對檢查](provenance/trial-report.json) 與 [行數／頁位](provenance/line-metrics.json)。
`diagnostics/` 保存初輪 Word 樣式選擇、封面無頁碼及 PDF 字型編號解析的失敗報告；
它們沒有完整歷史程式快照，不視為可完全重現的候選版本。最後結果另存，不覆寫失敗。

## 下一步：把有效的規則接回英文共用來源

1. 在英文 Q15 保留兩個可追蹤事實，僅於答案完整、屬於固定句時合段。
2. 沿用既有翻譯樹，不建立中文分支邏輯；同步調整 PDF 短單元的精確結構檢查。
3. 重新產生中英原生 PDF／Word，加入部分缺答、長篇、多筆、明確否定與複雜自填控制。
   原生基準與離線字型差異分開檢查，不靠換字型掩蓋。
4. 只有原生成品也通過後，才升套件版號；保留同一英文來源及兩種輸出模式。

本輪未改英文來源、`pipeline.yml`、748 組譯文、字型或模板版號，也未存取正式 DSW。
僅執行會自動清除的隔離渲染容器與暫存 LibreOffice 程序，既有測試服務仍停止。
`reproduce/` 的腳本可在本 repo 執行，依賴的既有 helper 維持 `08a06b9` 版本。
完整帶內嵌字型的診斷 HTML 留在本機 `outputs/resource-prose-trial-3/`；此處只存
題目 DOM 與完整 HTML 雜湊。`release_acceptance` 保持 false。
