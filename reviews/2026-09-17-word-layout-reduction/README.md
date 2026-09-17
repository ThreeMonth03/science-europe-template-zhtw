# Word Q5 縮減反例（不是修正版）

保留 0.3.34 原生 `metadata-partial` 的第一節至 Q5 共 53 個段落／表格節點，
只換成診斷封面、移除書籤及 Q6 之後的內容。原有樣式、字型、頁面設定及
其他 DOCX ZIP 部件不變；**省略後半份文件是診斷用途，不是可以交付的 DMP**。

| LibreOffice 25.2.3.2 預覽 | 原生文件 | 縮減反例 | Q5 五段所在頁 |
| --- | --- | --- | --- |
| 中文 | 6 頁 | 4 頁 | 都是 3,3,4,4,4，仍失敗 |
| 英文 | 6 頁 | 3 頁 | 都是 3,3,3,3,3，仍同頁 |

兩種語言均驗證保留的段落／表格 XML 相同（僅移除書籤），且第二頁起至
第三節標題之前，所有正文文字行的頁碼與座標都和原生文件相同。
因此不是靠字級、段距或前文折行變化才再次看到同樣結果。
全文 hash 不同是刻意省略內容的結果，不能宣稱完整文件文字相同。
這是可重現的**縮減反例**，未證明已是最小反例，也未定位引擎程式碼根因。

## 看哪些檔案

- 中文：[DOCX](reduced/reduced-chinese.docx)、[PDF](reduced/reduced-chinese.pdf)、
  [第 3 頁](visual/chinese-page3.png)、[第 4 頁](visual/chinese-page4.png)。
- 英文：[DOCX](reduced/reduced-english.docx)、[PDF](reduced/reduced-english.pdf)、
  [第 3 頁](visual/english-page3.png)。
- [機器檢查](reduced/report.json)含原始與衍生檔案 hash、段落頁碼及幾何一致結果。
- 原生來源仍在[前輪 after](../2026-09-17-storage-context-pagination/after/)，
  沒有改寫；完整六頁的失敗證據仍有效。

## 重跑

從 repo 根目錄，使用具備 lxml 的 Python、LibreOffice 及 Poppler：

```bash
../dsw-document-template-tool/.venv/bin/python scripts/reduce_word_layout_case.py \
  --output outputs/word-reduction-repeat
```

輸出目錄必須尚不存在。`completed=true` 只表示兩語言縮減檢查完成，
`release_acceptance=false` 保持不變；中文 Q5 仍是 `q5_together=false`。
不同引擎／字型若改變版面，工具會失敗，不會把原生反例偷偷更新成新答案。
`reproduce/` 保存原碼供比對；預設路徑以 repo 的 `scripts/` 執行為準。
`checksums.json` 涵蓋本目錄其他全部檔案。

## 診斷更正與界線

先前將 UNO `reformat()` 稱為「完整重排」不準確；
[25.2.3.2 實作](https://github.com/LibreOffice/core/blob/libreoffice-25.2.3.2/sw/source/uibase/uno/unotxdoc.cxx#L444)
並沒有執行排版動作。原始實測保留，解釋在[診斷文件](../../docs/word-import-layout.md)更正。
也不能把 `writer_layout_dump` 當成純讀取的排版快照：
[該版本實作](https://github.com/LibreOffice/core/blob/libreoffice-25.2.3.2/sw/source/core/layout/dumpfilter.cxx#L88)
會改可見區域並使 layout size 失效。不可先呼叫它再聲稱取得「未干預」基準。

本批未修改英文來源、翻譯、套件、原生 PDF 或 DSW worker，未測 Microsoft Word，
未向上游提交 issue，也沒有正式發布。
