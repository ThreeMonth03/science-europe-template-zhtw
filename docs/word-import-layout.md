# Word 匯入／重排診斷：模板仍為 0.3.34

**剩下的中文 Q5 分頁尚未修好，不升模板版號。** 這輪只有診斷工具、測試與
證據；英文 Jinja／Lua／reference、744 個譯文及 `pipeline.yml` 均未改動。
原生版面失敗門檻仍保留，沒有把另存、記憶體操作或換引擎的輸出冒充修正版。

## 找到的邊界

以同一份 `metadata-partial` 原生 DOCX，每項測試重新開啟私人 LibreOffice
25.2.3.2 process/profile；唯讀載入、禁用巨集及外部更新、不儲存回來源。

| 操作 | 中文 Q5 五段所在頁 | 英文 Q5 五段所在頁 |
| --- | --- | --- |
| 直接開啟匯出 | 3,3,4,4,4 | 3,3,3,3,3 |
| refresh／完整 reformat | 3,3,4,4,4 | 3,3,3,3,3 |
| 在政策段重新指定原值 `ParaKeepTogether=true` | 4,4,4,4,4 | 3,3,3,3,3 |
| 改指定題目、引言、第一／最後條列的原值 | 3,3,4,4,4 | 3,3,3,3,3 |
| 政策段關閉再恢復連頁 | 4,4,4,4,4 | 3,3,3,3,3 |
| 將政策段實驗另存 DOCX，再重新開啟 | 3,3,4,4,4 | 3,3,3,3,3 |

每份仍是六頁。政策段匯入時的有效連頁值本來就是 `true`；重新指定原值後，
可觀察到 property state 從繼承值改為 direct value，且版面重排。
這支持「完整 DOCX 匯入後的排版狀態相關」的假說，**尚未定位到引擎程式碼根因**。
不能據此宣稱 Microsoft Word 也有同一問題、單靠 direct keep XML 可修好，
或說所有短回答都只需這樣操作。

兩語言共 18 個直接／記憶體操作 PDF 的全文擷取相同（只忽略空白及驗證位置的
頁碼，不刪標點）。另外四個另存重開 PDF 的比較明確為不同：均新增 13 個
`U+F020` 擷取字元，出現在原有清單續段邊界；不偷偷將它正規化掉。
另存重開既沒有修好中文分頁，也不能當成全文表示不變的處理流程。

## 引擎升級不能只看 Q5

另外在已存在、固定 image ID 的隔離容器測 LibreOffice 26.2.0.3：無網路、
唯讀來源／根目錄，掛入本機相同 `/usr/share/fonts` 與 `/etc/fonts`，逐檔記錄
SHA256。這控制了字型檔，但**沒有控制作業系統與字型函式庫版本**，不是單一
變數的引擎版本因果實驗。

十個案例 × 英中，共 20 份未修改的原生 DOCX 重做 Word 預覽：

- 十份英文頁數相同；十份中文**各增加一頁**，包含空白、否定與長預算案例。
- 中文 `metadata-partial` Q5 變同頁，但文件 6 → 7 頁，Q5 之前的段落已經重排。
  不接受為局部分頁修正，也不直接升級預覽器。
- 20 份均通過原 DOCX 正文段落保留檢查。19 份全文擷取逐字相同；中文長預算
  因跨頁位置改變，兩組重複表頭／資源識別列的出現位置變動，嚴格全文比較
  保持 `false`。段落保留不等於閱讀順序／全篇版面已驗收。

本輪未重新產生 DSW 原生 PDF，未改 DSW worker。引擎警告 `dconf` 無法寫入
唯讀 cache 保留在執行紀錄；匯出完成不代表環境等同本機或 Microsoft Word。

## 重跑與下一步

主實驗可直接使用 repo 已保存的原生 DOCX（需要本機 LibreOffice、`python3-uno`
與 Poppler；一般單元測試不需要 UNO）：

```bash
/usr/bin/python3 scripts/diagnose_word_import_layout.py \
  --source reviews/2026-09-17-storage-context-pagination/after/native/metadata-partial-chinese.docx \
  --output outputs/word-import-repeat-chinese
```

英文將來源改為 `metadata-partial-english.docx`，且指定另一個新目錄。
工具的 `completed=true` 僅表示診斷完成；`unmodified_docx_q5_together=false`
仍是中文失敗證據，`release_acceptance` 永遠為 false。
跨引擎工具需原實驗完整的本機 build 目錄（含 native HTML、ZIP、預覽及 receipts），
以及已安裝的確切 image，不能只用截圖或精簡 HTML 冒充端到端重測：

```bash
../dsw-document-template-tool/.venv/bin/python scripts/compare_word_preview_engines.py \
  --build outputs/runtime-tables-2xbk2apb \
  --output outputs/word-engine-repeat \
  --image sha256:d71ab8c13b6bd47c7bc81195082005dfb17eaa75e8b1fadd347a64ee66ed98d5
```

下一步應用完整合成反例核對目標 Microsoft Word，再縮減 DOCX 匯入的觸發條件。
只有有界、能在重新開啟後仍成立的規則，才值得改英文共用 Word 輸出；之後須
同時重跑英中、漏填、長篇及原生 PDF。不要加入定頁碼換頁或空白段落來追一張樣張。

這次的 `fix/word-context-layout` 是短期診斷分支，不是新增永久模板版本線。
英文仍鎖定 `8528898c28e44f91d1b5a912261e51061f8c36a9`，英中套件維持 0.3.34，
官方 baseline 不移動。未來上游／引擎升級要連同原生反例及這份輸入／引擎身分
重驗；Git 無衝突、單元測試綠燈或頁數相同，都不能取代成品驗收。

詳見[兩語言實測、跨引擎輸出與頁面影像](../reviews/2026-09-17-word-import-layout/README.md)。
