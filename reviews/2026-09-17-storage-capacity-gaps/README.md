# Q3 儲存容量漏填：0.3.31 → 0.3.32

六組相同填答的中英文對照通過：前後各 36 份原生 HTML/PDF/DOCX，
另有前後各 12 份 LibreOffice Word 預覽。只修容量追問的顯示與固定句子，
不是整份 DMP、所有 Q3 欄位或 Microsoft Word 的正式驗收。

## 先看樣張

- 部分缺答：[中文 PDF](after/native/storage-partial-chinese.pdf)、[英文 PDF](after/native/storage-partial-english.pdf)。
- 可編輯文件：[中文 DOCX](after/native/storage-partial-chinese.docx)、[英文 DOCX](after/native/storage-partial-english.docx)。
- 最小反例：[中文 PDF](after/native/storage-missing-chinese.pdf)、[英文 PDF](after/native/storage-missing-english.pdf)。
- 原值：[0 GB 中文 PDF](after/native/storage-zero-chinese.pdf)、[2048 GB 英文 PDF](after/native/storage-complete-english.pdf)。
- 控制組：[全空白中文 PDF](after/native/empty-chinese.pdf)、[明確否定英文 PDF](after/native/negative-english.pdf)。

原本「選擇填寫總量、數量沒填」只留下小標；空白字元更產生「儲存空間
為 GB」這類殘句。現在顯示「尚待補充：計畫所有資料與軟體（含暫存空間）
所需的預估儲存容量（GB）。」已填 0、2048、其他回答與檔名不改寫。
提示沿用獨立 reading-gap 區塊，沒有縮字級、改行距或另改中文 Jinja。

## 頁數與閱讀

下表前後頁數均相同。欄位中的數字依序為英文／中文。

| 案例 | 原生 PDF | Word 預覽 |
| --- | --- | --- |
| 缺容量、有後設資料 | 4／3 | 3／3 |
| 全空白容量、其他回答完整 | 6／6 | 6／6 |
| 0 GB | 6／6 | 6／6 |
| 2048 GB | 6／6 | 6／6 |
| 整份空白 | 4／3 | 3／3 |
| 明確否定 | 4／3 | 3／3 |

中英缺答提示均完整保留；原生 PDF 沒有空頁、超出頁面的文字、缺答框
跨頁或題目與第一段回答分離。Word 以可編輯 XML 和新產生的預覽分別檢查。
空白／否定控制組的正文幾何完全相同（封面版本資訊不列入比較）。

已視覺查看中英最小／部分缺答的 PDF、代表性 Word 預覽及 0／2048 頁面。
英文部分缺答 PDF 的 Q5 由第 3 頁移至第 4 頁；原本落單在第 4 頁的
欄位對應限制框，現在與 Q5 標題、回答一起呈現。代價是第 3 頁末留白增加，
但總頁數維持 6 頁。這是新增必要提示後的內容重排，不是假稱整篇座標不變。
Word 保持原有純文字提示樣式；是否為 Word 增加視覺區分仍是另一項設計議題。
36 張實際頁面圖與來源 hash 見 [頁面索引](visual/page-index.json)，
擷取頁面不等於全部頁面都經人工驗收。

## 可追溯與限制

- 英文來源：`4f8546a363574a0eda0a8df2a6eee05df67029a2`，兩 repo 工作分支 `fix/q3-storage-gaps`。
- 官方基底仍為 Science Europe template 1.30.1；不是升級官方版本。
- 中英共 1,732 組 Q3 whole-DOM 檢查；保留 Q2 的 528 組、Q11 的 548 組分支和 128 組缺答組合。
- 翻譯 734 → 735 組，733 組精確沿用、1 組替換、1 組新增；Q3 以外來源與翻譯不變。
- HTML 精確比對整份正文；PDF 僅正規化空白並逐項核對已證明的清單符號；不刪除標點。
- Word 除 Q3 容量區塊外，正文 XML 完全一致；保留原字元格式、連結、編號與樣式定義。
- 量值改文、漏填提示及獨立政策段落的限定變化另有 mutation tests；不容許任意改寫或粗體化。
- 案例經本機 DSW 編譯的公開 Common KM 2.7.0 驗證追問可達性；未使用真實計畫資料或正式站憑證。
- 兩次乾淨候選建置與實際原生產檔使用相同 ZIP；manifest、來源、fixtures、產檔收據、比較報告及檢查器均保存。
- 本機 worker 使用已審查 tables-only 引擎，整批候選輸出期間未重啟；結束後還原 stock 映像並停止四個 pilot 容器。
- 前後各兩個暫用模板在確認沒有 project/document 引用後刪除；ZIP 備份保留，資料卷未刪除。

英文 ZIP SHA256：`f1076287688b52a0e87e372fa60092a527b6b720921da29d554a75717585beb5`。
中文 ZIP SHA256：`117efbcd01a210ad80b13d4bf133f6610874d3f8f0a6c5d7170056e7a7311838`。

這一輪只處理已選擇指定容量的漏填。其他 Q3 追問（例如不公開後設資料
卻未填原因）、全部 Science Europe 要求、臺灣版 KM 與實際 Microsoft Word
環境仍未全面驗收。沒有合併 main、發布 tag/release 或安裝至正式 DSW。

## 重現

依 `reproduce/pipeline.yml` 取得精確英文／工具來源，在中文 checkout 執行
`scripts/build.py` 建置乾淨候選。以保存的六組 fixtures，使用
`run_missing_info.py`、`preview_word_short_budget.py` 產生前後對照，再跑
`check_storage_gap_outputs.py --build <after> --prior <before> --english <english>`。
`probe_storage_gap_scope.py` 驗證 Q3-only 來源／翻譯範圍與歷史行為。
既有候選建置不可拿 preview 或不同引擎的輸出冒充；正式 release 門檻另列。
