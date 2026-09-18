# 0.3.40：Q15 短概述與預算表接回同一頁

中文提交預覽的 Q15 標題／概述原在第 5 頁，預算表獨留第 6 頁；
現在同在第 6 頁。這是模板產生的原生 DSW PDF，不是事後編輯 PDF。
頁數仍為 6，前面的章節、字型和全文保留；Word 沒有改動。

## 直接看成品

| 語言／模式 | 原生 PDF | 原生 Word | Word 預覽 PDF |
| --- | --- | --- | --- |
| 中文提交預覽 | [PDF](after/native/profile-partial-submission-chinese.pdf) | [DOCX](after/native/profile-partial-submission-chinese.docx) | [預覽](after/word-preview/profile-partial-submission-chinese.pdf) |
| 中文內部檢核 | [PDF](after/native/profile-partial-review-chinese.pdf) | [DOCX](after/native/profile-partial-review-chinese.docx) | [預覽](after/word-preview/profile-partial-review-chinese.pdf) |
| 英文提交預覽 | [PDF](after/native/profile-partial-submission-english.pdf) | [DOCX](after/native/profile-partial-submission-english.docx) | [預覽](after/word-preview/profile-partial-submission-english.pdf) |
| 英文內部檢核 | [PDF](after/native/profile-partial-review-english.pdf) | [DOCX](after/native/profile-partial-review-english.docx) | [預覽](after/word-preview/profile-partial-review-english.pdf) |

中文提交的 [修正前第 5 頁](visual/before-chinese-submission-p5.png)、
[修正前第 6 頁](visual/before-chinese-submission-p6.png)、
[修正後第 6 頁](visual/after-chinese-submission-p6.png)。
其餘全空、未填幣別的長預算與多筆預算對照也在 `before/`、`after/`。

## 改動與維護邊界

只在英文 PDF 入口加入一個共用 helper，讀取已產生的 Q15，對符合保守條件的
外層加上 `break-inside: avoid`。不重組題目或答案，不改 PDF 共用 CSS、字型、
Word、問卷 Jinja 或 748 組譯文；HTML 匯出也不套用這個提示。
中文仍經原有工具轉換，準備後的中英文 helper 完全相同。

只接受單一計畫、一至兩筆短預算、已知簡單結構及限定的長度／段落數。
漏填、未知狀態、長篇、多筆、多計畫、連結、圖片、巢狀內容、強制換行等
維持原本可分頁結構。詳見 [適用條件](../../docs/short-resources.md)。
這不是任意 HTML 的通用解析器，也不保證未來更換字型後仍符合高度界線。

## 實際驗證

- 4 組合成問卷 × 2 種模式 × 2 種語言，共 16 組原生前後對照。
- 本輪產生 72 份原生 HTML／PDF／DOCX（前版控制組 24、新版 48）及
  24 份 Word 預覽；另沿用前輪同套件的 24 份原生基準與 8 份 Word 預覽。
  每份 fixture 的 recipe、events、知識模型及套件雜湊均核對。
- 240 組題目 HTML 完全一致；16 組 Word 正文 XML、樣式、字型表、
  編號及外部連結相同，LibreOffice 預覽的非封面文字座標與頁數相同。
  新版 2,366 個正文段落均在預覽文字中找到。
- 4 組短 Q15 都維持 6 頁；中文提交標題／表格 `[5,6] → [6,6]`，
  其他三組仍在第 6 頁。Q15 前的文字座標（包含封面）完全一致。
- 12 組全空／長預算／多筆對照不套用提示，PDF 非封面文字座標與頁數一致。
  全部 16 組 PDF 全文及字型清單相同；僅忽略字型子集前綴、物件編號及
  清單符號的擷取先後次序，符號數量和所有其他文字仍須相同。
- 中英文準備後來源各通過 57 組案例：autoescape 開／關共 114 項結構檢查，
  print／screen 共 114 項引擎前後比較。保留未套用案例的全部文字座標，
  套用案例不可增頁，單元須在單一頁且高度小於 650 CSS px。
- 來源門檻只還原已知 PDF 入口／helper 差異，再沿用所有歷史檢查；不更新
  舊雜湊來掩蓋變動。`diagnostics/` 保留開發中三次失敗報告（界線 fixture
  計算、autoescape／Markup 串接）；不是最後候選，也沒有完整歷史來源快照。

詳細數值見 [原生比對報告](provenance/native-comparison.json)。
人工檢視四份目標 PDF 的 24 頁概覽、中文提交前後目標頁細圖；
沒有宣稱所有控制組都已逐頁人工驗收，亦未實測 Microsoft Word。
英文原生 PDF 仍有既有的 1–2 項行框重疊偵測警告，前後清單相同；
「沒有新增」不代表全篇已證明零重疊。

## 仍未完成

這次改善連續閱讀，不減少總頁數；留白只是重新分配，尾頁仍不滿。
中文句號前空白、短句分段與語氣沒有修改。中文提交 PDF 的 Q11 保存敘述
仍延續至次頁；Word 的 Q5／Q15 分頁問題也不在此輪修正範圍。
提交預覽仍只切換已明列的提示，不能直接視為國科會正式繳交模板。

前輪離線重播的中文字型基準差異仍未查明原因。這輪改採原生對原生，
另外核對字型清單及正文座標，不能據此宣稱前輪的根因已修好。
原廠 worker 的 Markdown 表格支援、Word 實機與整份閱讀驗收仍是發布門檻。

## 來源與環境

兩 repo 都在 `fix/profile-pagination`；英文來源
`ede928f4950e2d382cd38041d2430765c22aea4e`，中文乾淨候選來源
`7f1c350b7aeb35e3d28768bdf211bcf32ce5de54`，版號同為 0.3.40。
review／submission 是同套件的輸出選項，不另維護永久分支；後續 QA 提交
不更動模板套件輸入。未合併 main、未 tag、未正式部署。

使用隔離的本機 DSW 4.30、tables-only worker 與 LibreOffice 25.2.3.2，
未套用實驗字型修補。前版兩個測試模板先清理，才開始新版 48 次產檔；
新版完成後也清理兩個自有模板，全部經零引用檢查與 ZIP 備份驗證。
所有 ZIP、樣張與 volumes 保留；worker 還原原廠映像，四個測試服務已停止。
正式 DSW、使用者專案及桌面 keyring 均未存取。

`question-content/` 保存題目 DOM 與原始 HTML 雜湊，避免重複提交內嵌字型；
完整 HTML／ZIP 留在本機 `outputs/`。`reproduce/` 保存比對程式與來源鎖，
`checksums.json` 綁定本輪證據。`release_acceptance` 維持 false。
