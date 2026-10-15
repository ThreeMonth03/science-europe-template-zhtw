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
CI 的 `current-candidate-not-a-release` artifact 包含五件交付資產及 manifest。
失敗時也可能保留診斷產物；下載成功不等於建置成功或已核准發布。

## 翻譯防線

建置檢查目前英文 Jinja 與 PO 的有效鍵是否精確配對。缺鍵、多餘鍵、重複鍵、
漏譯、未確認譯文或具名參數不一致均會阻擋建置。PO 的 `Language` 必須是
`zh-Hant`；MO 必須由同一份 PO 編譯。這些檢查不會自動判斷中文通順與否，
也不保證未標記的固定文字已被翻譯。

譯文以整句或完整子句為單位，保留參數名稱；不要用改寫作者回答來修正文句。
需要調整段落結構或缺答條件時，修改英文 repo 的共用 Jinja。
`scripts/refresh_po.py` 使用官方抽取器，遇到無法解析的 Jinja 會中止，
不產出不完整的 POT。唯讀檢查若發現新增／移除鍵、fuzzy 或空譯文會回傳失敗；
指定新輸出目錄則只產生待審稿，不能作為翻譯核准或成品驗收。
更新譯文後，仍須執行建置的鍵／參數檢查與下列原生成品驗收。

## PDF／Word 成品驗收

### 本機重跑入口

先建置，再用 `preview_native.py` 驗證既有建置目錄。它不重寫回答、不重建 DT、
不連 Server，也不更換 Worker／Pandoc。需要 Docker、pipeline 鎖定的兩個
官方 Worker image，以及本機各版本的 Worker 設定與 document context。
設定只用於離線渲染，無須線上帳密；不要把設定或真實專案 context 提交到 repo。
document context 是渲染測試輸入，不是改用 JSON／LLM 產生 DMP 的另一套流程。

三個 context 分別符合 4.34 中文、4.35 英文與中文的 wire schema，且必須有
完全相同的 `project.replies`。允許知識模型的介面文字依語言不同，逐份記錄其
雜湊。先用 `--plan-only` 核對資產與配對，不啟動 Worker、不產文件：

```sh
python scripts/preview_native.py \
  --build outputs/build-REPLACE_ME \
  --context-434-zh /private/case-434-zh.json \
  --context-435-en /private/case-435-en.json \
  --context-435-zh /private/case-435-zh.json \
  --config-434 /private/worker434.yml --config-435 /private/worker435.yml \
  --output outputs/native-NEW --plan-only
```

移除 `--plan-only` 才產生三組 PDF／DOCX。預設為提交版；用 `--profile review`
檢查內部提示。要驗多個案例，按相同順序重複每個 context 參數，三組數量必須
相同。每次使用全新輸出目錄；失敗目錄也不重用。Worker 不連網，image 必須
預先取得，腳本不自動更新或拉取別的版本。

再產逐頁預覽，明確指定本機 LibreOffice 與 Poppler，不自動挑 PATH 上的版本：

```sh
python scripts/render_previews.py \
  --native outputs/native-NEW --output outputs/pages-NEW \
  --soffice /absolute/path/to/soffice \
  --pdftoppm /absolute/path/to/pdftoppm
```

預設在 `pdftoppm` 同目錄找 `pdfinfo`，也可用 `--pdfinfo` 指定。若有 canonical
`render_docx.py`，加上 `--docx-renderer /absolute/path/render_docx.py` 及
`--renderer-python /absolute/path/python`；仍使用上述明確指定的 LibreOffice。
預覽會核對原生檔及頁數／PNG 雜湊，不修改原生文件。輸出依序放在編號子目錄，
`preview-receipt.json` 對應原生路徑、語言、PDF 或 Word 及各頁影像。

兩個入口的 receipt 永遠 `accepted: false`，只聲明渲染是否成功。
它們不產生 `pilot-report.json`、不自動完成目視驗收，也不能作為 staging 核准。
本機設定、context、logs、頁面影像與 receipts 都是私有 QA 資料，不上傳 CI。

### 人工驗收範圍

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
