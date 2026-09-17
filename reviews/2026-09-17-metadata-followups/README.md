# Q3 資料字典與後設資料追問：中英文前後樣張

這是 **0.3.32 → 0.3.33 的限定內容實驗，不是正式驗收版**。
本輪補回資料字典是／否，並呈現後設資料政策的漏填追問。內容、翻譯與
可編輯 Word 比對通過；人工檢視另發現 **3 個 Q5 說明跨頁反例**，尚未修正。
不能把本輪自動檢查通過解讀成整份 PDF／Word 已經好讀。

## 先看這幾份

| 案例 | 前版 | 本輪 PDF | 本輪可編輯 Word |
| --- | --- | --- | --- |
| 中文部分漏填 | [PDF](before/native/metadata-partial-chinese.pdf) | [PDF](after/native/metadata-partial-chinese.pdf) | [DOCX](after/native/metadata-partial-chinese.docx) |
| 英文部分漏填 | [PDF](before/native/metadata-partial-english.pdf) | [PDF](after/native/metadata-partial-english.pdf) | [DOCX](after/native/metadata-partial-english.docx) |
| 中文自填多段原因 | [PDF](before/native/metadata-private-text-chinese.pdf) | [PDF](after/native/metadata-private-text-chinese.pdf) | [DOCX](after/native/metadata-private-text-chinese.docx) |
| 英文完整、追問明確否定 | [PDF](before/native/metadata-complete-english.pdf) | [PDF](after/native/metadata-complete-english.pdf) | [DOCX](after/native/metadata-complete-english.docx) |
| 中文只填資料字典「否」 | [PDF](before/native/metadata-dictionary-no-chinese.pdf) | [PDF](after/native/metadata-dictionary-no-chinese.pdf) | [DOCX](after/native/metadata-dictionary-no-chinese.docx) |

所有八組案例皆有英／中文、前／後兩版，放在 `before/`、`after/`。
Word 預覽放在各自的 `word-preview/`，使用 LibreOffice，並非 Microsoft Word 執行結果。

## 本輪通過的範圍

- 前後各 48 份原生輸出（HTML／PDF／DOCX），共 96 份；另有 32 份 Word PDF 預覽。
- 同一份問卷、事件及編譯 KM 的 SHA256 綁定前後成品。15 題、6 節、缺答與自填
  文字保留、頁面邊界、題目與第一段回答等限定檢查通過。
- 中英文合計 3,452 組完整 Q3 DOM 比較，保留前版 1,732 組容量比較，
  以及 Q2 的 528 組、Q11 的 548 組分支與 128 組缺答組合。
- 新增 9 組譯文，原有 735 組完全保留。除了 Q3 與三個已核對 UUID，
  準備好的英文／中文 `src` 檔案雜湊與前版一致；字型、CSS、Word Lua／參考文件不變。
- 兩段自填原因、兩個條列、粗體檔名與連結保留。Word 非本輪固定敘述的正文 XML、
  自填區塊 XML、編號與連結目的地均逐一核對。突變測試拒絕漏提示、錯誤否定、
  數值／標點／字型或自填文字被改。
- 所有案例 PDF／Word 預覽頁數不增加。空白／否定控制組正文位置相同，
  另以 100 dpi 比對 18 個正文頁面，像素完全一致（排除封面）。

完整型案例仍是 6 頁 PDF／6 頁 Word 預覽；資料字典單題、空白、否定案例為
英文 4／3 頁、中文 3／3 頁。頁數相同不等於斷頁相同。

## 視覺檢查與尚未修正的反例

`visual/` 保存 49 張 Q3 起始／延續頁與 Q4 銜接的完整頁面圖。
已人工抽看中英部分缺答、完整答案、資料字典否定與中文自填原因的 PDF／Word。
新增提示未遮住回答；英文部分缺答的 Q4 從第 3 頁移到第 4 頁，題目與回答一起移動。
中文完整固定敘述仍成段；自填原因保留自己的段落與清單。

但 Q3 加字會影響後面的分頁。新增
[Q5 位置量測](diagnostics/q5-context-reflow.json) 比較所有 8 × 2 × 2 組：

| 新反例 | 前版 | 本輪 |
| --- | --- | --- |
| 中文部分漏填 Word | Q5 回答與限制說明同在第 3 頁 | 回答在第 3 頁，限制說明移到第 4 頁 |
| 中文不公開、原因漏填 PDF | Q5 回答與限制說明同在第 3 頁 | 回答在第 3 頁，限制說明移到第 4 頁 |
| 中文不公開、原因漏填 Word | Q5 回答與限制說明同在第 3 頁 | 回答與限制說明引言留在第 3 頁，兩個限制條列移到第 4 頁 |

前後 9 張完整反例頁面保存於 `diagnostics/`。沒有隱藏此結果或放寬原有內容檢查。
下一輪應針對短 Q5 回答與其限制說明做有界的連頁修正，保留長篇可跨頁能力，
不採全篇禁止分頁或縮小字級。中文缺答密集時的閱讀節奏仍可改善。

其他限制：DC／DataCite／DDI／關鍵字／W3C PROV 的明確否定仍未完整呈現；
所有父層／追問的缺答覆蓋與完整 Science Europe 要求對照尚未全部驗收。
問卷欄位核對不等於 Science Europe 認可，也不證明填答內容本身完善。

## 可重現性與安全邊界

- 英文：`d63a944b51a270a6cd19cef26bdd26712ff0ff98`，0.3.33。
- 中文候選來源：`cc6302d`；另以加入檢查器後的 `e49920a` 乾淨重建，兩個 ZIP 相同。
- 英文 ZIP：`844d3fbe6d46cd5a7145861a9bc36c5b3d27f38643a321b39434f90aefdb0c5f`。
- 中文 ZIP：`4073991a685ea4e8c43fb786891383d849da2573baa5de99d58d14eaa176c22e`。
- 前版英文：`4f8546a363574a0eda0a8df2a6eee05df67029a2`；中文：`99c7fb181d5d0cf087740efb6fd3f61fab9c7dcd`。
- `candidate-manifest.json`、`rebuild-manifest.json`、`probes/`、`source/`、
  `fixtures/`、`reproduce/` 及各格式收據保留來源、工具與資料雜湊。
  `after/metadata-followup-report.json` 是限定通過報告，不包含宣稱 Q5 跨頁已修好。
- 只有本機公開合成問卷；沒有讀取正式站專案、keyring 或使用真實憑證。
  每批兩個無引用暫存模板已在確認 ZIP 備份後移除，可由 ZIP 重建。
  原版 worker 已恢復，四個本機容器已停止，volume 未刪除。
- 分支維持 `fix/q3-metadata-followups`；未合併、未標 tag、未發布或上傳正式站。

重跑本輪比較可使用 `scripts/check_metadata_followup_outputs.py --build AFTER --prior BEFORE --english EN_REPO`，
另用 `scripts/probe_q5_followup_pagination.py` 量測 Q5 反例。需完整原生輸出及既有
依賴環境；快照並非可獨立執行的整個工具庫。所有封存檔案索引見 `checksums.json`。
