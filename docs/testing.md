# 目前檢查與成品驗收

## 可重複執行的檢查

先使用 `pipeline.yml` 鎖定的英文及 Tool checkout，安裝宣告的依賴。
以含鎖定 Tool 的隔離 Python 環境執行：

```sh
DSW_ENGLISH_CHECKOUT=../science-europe-template \
  ../dsw-document-template-tool/.venv/bin/python -m unittest discover -s tests -v
```

保留的測試涵蓋 PO 建置、候選不可覆寫／來源配對，以及套件說明與時間戳記。
正式建置後，檢查實際準備好的兩個語言包：

```sh
../dsw-document-template-tool/.venv/bin/python \
  ../science-europe-template/scripts/check_current.py \
  --build outputs/build-REPLACE_ME \
  --output outputs/build-REPLACE_ME/current-behavior.json
```

既有 CI 的三組工作分工如下：

| 工作 | 檢查內容 |
| --- | --- |
| english-unit | 鎖定英文的現行測試與 4.34 相容匯出器。 |
| chinese-unit | 本 repo 的 PO 建置、候選生命週期及套件說明。 |
| integration | 配對建置、兩語言行為檢查及官方抽取結果對 PO。 |

保留的 aggregate check 要求三組均成功。舊來源回放不再是現行 CI 的模式；
需要研究歷史時，從 Git 取得當時的程式與依賴，不混入目前驗收。

## 翻譯防線

建置檢查目前英文 Jinja 與 PO 的有效鍵是否精確配對。缺鍵、多餘鍵、重複鍵、
漏譯、未確認譯文或具名參數不一致均會阻擋建置。PO 的 `Language` 必須是
`zh-Hant`；MO 必須由同一份 PO 編譯。這些檢查不會自動判斷中文通順與否，
也不保證未標記的固定文字已被翻譯。

譯文以整句或完整子句為單位，保留參數名稱；不要用改寫作者回答來修正文句。
需要調整段落結構或缺答條件時，修改英文 repo 的共用 Jinja。
本輪清理不改譯文；POT／PO 更新操作另行處理。

## PDF／Word 成品驗收

使用相同合成回答，分別驗證 4.34 中文相容包、4.35 英文及 4.35 中文原生 PO。
納入完整、部分漏填、全空、明確否定、未命名、多筆與長文／清單／表格案例。
逐頁檢查：

- 原始十五題及已填的有意義資訊保留，不把缺答當成否定。
- 提交版不出現內部漏填提示；檢核版保留必要提示。
- 原作者回答、段落、清單與表格不因翻譯或分組而遺失。
- 沒有裁切、重疊、破表、缺字、孤立引導句或難以閱讀的換頁。

PDF 原生成品與 Word 的 PDF 預覽是不同渲染路徑，不應期待逐頁相同。
LibreOffice 預覽不等於 Microsoft Word 實機驗收。案例通過與 CI 綠燈都不代表
所有未來輸入一定沒有問題。

## 候選保存

`stage_candidate.py` 僅保存已通過聲明範圍的本機候選，不發布 GitHub release，
也不上傳 DSW。它要求 `pilot-report.json` 明確通過、沒有 blocking issues，
並綁定該 manifest 與五件 PO 交付資產的完整 SHA256；不能拿另一輪報告放行。

```sh
../dsw-document-template-tool/.venv/bin/python scripts/stage_candidate.py \
  --build outputs/build-REPLACE_ME --store /path/to/local-candidate-store
```

舊的兩 ZIP 候選契約已退役。現行候選包含英文 ZIP、中文相容 ZIP、
PO、MO 與相容包來源 sidecar。
