# 雙輸出模式：分頁修正前的 A/B 樣張

這是以 0.3.38 原生成品做的離線排版實驗，**尚未修改模板、不是新的 DSW 匯出或可繳交版本**。
英文來源、中文翻譯、版號及 source lock 都不變。不使用 LLM、不補寫答案、不存取正式 DSW。

## 先看中文提交樣張

| 問題 | 原基準 | 實驗後 | 結果與代價 |
| --- | --- | --- | --- |
| Word Q11 標題與摘要分頁 | [預覽](word/profile-partial-submission-chinese-baseline.pdf) | [預覽](word/profile-partial-submission-chinese-joined-label.pdf)／[可編輯 Word](word/profile-partial-submission-chinese-joined-label.docx) | p4／p5 → 同在 p5；資料集名稱由 Heading5 改為粗體段首，Q11 本題仍為 Heading3 |
| PDF Q15 概述與小預算表分頁 | [基準](pdf/profile-partial-submission-chinese-baseline.pdf) | [實驗 PDF](pdf/profile-partial-submission-chinese-keep-short-q15.pdf) | p5／p6 → 同在 p6；仍為 6 頁，不是減頁實驗 |

Word 與 PDF 是兩個獨立實驗，不是同一個已整合套件。兩者皆保留全文、標點、0、金額、
網址及使用者自填「尚待補充」原文；沒有自動修訂中文。

## 中英、兩種模式的結果

| 格式／模式 | 原基準：題目與目標內容頁碼 | 實驗後 | 頁數 |
| --- | --- | --- | --- |
| Word 英文檢核 | 4／4 | 4／4 | 6 → 6 |
| Word 英文提交 | 4／4 | 4／4 | 6 → 6 |
| Word 中文檢核 | 5／5 | 5／5 | 6 → 6 |
| Word 中文提交 | 4／5 | 5／5 | 6 → 6 |
| PDF 英文檢核 | 6／6 | 6／6 | 6 → 6 |
| PDF 英文提交 | 6／6 | 6／6 | 6 → 6 |
| PDF 中文檢核 | 6／6 | 6／6 | 6 → 6 |
| PDF 中文提交 | 5／6 | 6／6 | 6 → 6 |

Word 比的是 Q11 題目／第一段摘要；PDF 比的是 Q15 題目／完整預算表內容。
共保存 8 份 Word 試驗文件及其 8 份 LibreOffice 預覽、8 份 PDF，合計 96 個 PDF 頁。
改版樣張的 48 頁概覽在 `visual/`，不是 96 頁逐頁細部的正式驗收。

### 中英樣張入口

| 模式 | Word 預覽 | PDF |
| --- | --- | --- |
| 英文檢核 | [Q11 試驗](word/profile-partial-review-english-joined-label.pdf) | [Q15 試驗](pdf/profile-partial-review-english-keep-short-q15.pdf) |
| 英文提交 | [Q11 試驗](word/profile-partial-submission-english-joined-label.pdf) | [Q15 試驗](pdf/profile-partial-submission-english-keep-short-q15.pdf) |
| 中文檢核 | [Q11 試驗](word/profile-partial-review-chinese-joined-label.pdf) | [Q15 試驗](pdf/profile-partial-review-chinese-keep-short-q15.pdf) |
| 中文提交 | [Q11 試驗](word/profile-partial-submission-chinese-joined-label.pdf) | [Q15 試驗](pdf/profile-partial-submission-chinese-keep-short-q15.pdf) |

## 哪些檢查通過、哪些沒有

- Word 四份基準預覽的逐頁座標都精確重現前輪成品。逐檔驗證只改指定 Q11 XML，
  文件／樣式 XML 重新序列化不視為內容修改；其餘套件項目保持原位元組。
  全文文字節點順序相同，改後每份少一個段落，但原段落文字全部保留。
- 加 direct keep、換摘要 BodyText、自訂 Heading5 樣式、取消 outline、摘要 keep 等五種
  純樣式試驗都沒有修好中文提交 Q11；不能把已有的 keep-with-next 再加一次當作解法。
- PDF 四組 A/B 的 Q15 之前文字座標完全一致，全文與已驗證的清單符號數目不變。
  英文原有兩個行框交集仍相同，不能把本輪寫成「所有行框皆無交疊」。
- **PDF 只有三份基準精確重現前輪；中文檢核版沒有。** 舊檔有 `Pilot-CJK-Semi-Bold`，
  新重建檔沒有，第一行 y 座標由 56.707117 變成 57.057117。獨立新程序重建仍有差異。
  原因未定，不宣稱已證明是快取、隨機性或模板錯誤。見 [字型紀錄](font-baseline-discrepancy.json)。
  所以 `completed=true` 只表示本輪 A/B 檢查跑完，`all_native_baselines_reproduced=false`，
  且 `release_acceptance=false`。
- 仍未做 Microsoft Word 驗收，也未把實驗接回 Jinja／Lua 後跑 DSW 原生匯出。
  原有 Q5／英文 Q1 跨頁、中文句號前空白等問題仍開放。

## 實驗紀錄與重跑

`word/report.json`、`pdf/report.json` 綁定輸入與輸出 SHA-256、引擎及腳本版本。
原始 DOCX／PDF／精簡 HTML 保留在 [0.3.38 原生封存](../2026-09-18-output-profiles/README.md)，
含字型的完整 HTML 留在本機 runtime 目錄，避免重複提交四份 16 MB 字型內嵌資料。

`diagnostics/` 保留先前試驗報告，包含無效樣式試驗與檢查器開發失敗，不覆寫成成功。
這些舊報告不是完整可重跑封存：早期腳本版本／所有衍生成品仍未一併封存；
可重跑與逐檔驗證的證據以本目錄 `reproduce/` 和最終兩份報告為準。
最初 PDF 試驗另曾在容器寫入本機掛載目錄時遇權限錯誤；沒有產出有效 PDF。
目前改為唯讀輸入、容器 stdout 回傳產物，未更改主機目錄權限。

在 repo 根目錄、使用已安裝依賴的 Python，指定**尚不存在**的輸出目錄：

```sh
python scripts/rehearse_profile_pagination.py --trials baseline joined-label --output outputs/new-word-rehearsal
python scripts/rehearse_profile_pdf.py --source outputs/runtime-tables-stkosfij/renders --output outputs/new-pdf-rehearsal
python -m unittest discover -s tests -p test_profile_pagination_trials.py -v
```

下一步是把「短且簡單」的適用條件先做成保守規則，再接回英文共用 Jinja／Lua，
中文仍循現有翻譯流程。長回答、多資料集、多計畫、漏填與未知結構須保留可分頁退路；
不能直接把本次整題 `break-inside: avoid` 規則套用所有 Q15。
