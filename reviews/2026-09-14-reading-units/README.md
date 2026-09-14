# 0.3.3：蒐集／文件說明段落與短表格分頁

2026-09-14。本機合成資料實驗，未發布、未部署正式 DSW。
仍衍生自官方 Science Europe 1.30.1，六節十五題不變。
以下樣張連結以本文件複製到的 review 目錄為準。

## 先看樣張

- [中文 PDF：相同回答、改後段落與小表格](tables/structured-chinese.pdf)
- [同份可編輯 Word](tables/structured-chinese.docx)
- [Word 的 LibreOffice 預覽](tables/word-preview/structured-chinese.pdf)
- [多段自由回答反例](tables/reading-rich-chinese.pdf)
- [部分缺答與未命名資料集](tables/reading-partial-chinese.pdf)
- [48 列長表格 PDF](tables/table-long-chinese.pdf)
- [48 列長表格 Word 預覽](tables/word-preview/table-long-chinese.pdf)
- [原版 worker 對照](stock/structured-chinese.pdf)

`tables/` 仍使用獨立的 Markdown 表格實驗 worker；**只安裝這版模板，
不會讓原版 DSW 4.30 突然支援 Markdown 表格**。樣張是測試用 DMP，
不能視為內容完整、已核定或可直接照抄的正式文件。

## 本輪改動

Q2 的儀器資料集改成一段交代資料集、蒐集者、設備說明，不再是資料集
名稱加兩個固定短段。中文以完整句子翻譯，沿用現有 Sentences 連接規則。
例如：

> 沿岸水溫觀測資料的蒐集方式：此資料集將由計畫內的專家使用自有設備蒐集。所用設備已有完整說明，且為研究團隊所熟悉。

蒐集者／設備未填時分別提示，已填的另一項仍保留；兩項皆未填也不會只剩
資料集名稱。外部單位的所有權選項保留；選「其他」但漏填說明時提示不足。
所有權自由回答另外排成段落／清單，不嵌入固定敘述的 `<p>`。
非儀器資料集原有的 `<p><ul>` 結構也拆開，說明放在獨立 answer-detail。

Q3 使用既有、僅限模板固定敘述的 `dataset-policy`：後設資料標準／公開
方式相接；容量、檔案系統、版本管理等連續固定段落相接。HTML／PDF 由
CSS 呈現，Word 由 Lua 真正合成段落。自由回答的 `div`／清單會中斷合併。
後設資料不公開的理由、資料夾規則、檔案及物件命名規則均保持獨立的
Markdown 區塊，不把生成的 `<p>` 塞在另一個 `<p>` 裡。

這輪未改全域字級或段距，也沒有全文件刪換行、補句號或 LLM 改寫。
Q1／Q4 上輪修好的「措施短語以頓號連接、完整句末才有句號」保持不變。

## 小表格不是整題鎖頁

Q1 的 `provenanceReading` 只給符合以下條件的溯源回答加同頁提示：

- 一個簡單 HTML 表格，含表頭共 2–4 列，每列最多 4 欄。
- 回答總文字長度至多 500 字元，個別儲存格至多 80 字元。
- 僅接受列出的簡單標籤；圖片、複雜 markup、帶屬性儲存格等不套用。

不是通用 HTML parser，也不改寫回答；不能判定安全的小型表格就維持可分頁。
PDF 只對被標記的區塊設 `break-inside: avoid`。Word 依據
[Pandoc 的 Table／Row／Cell 結構](https://pandoc.org/lua-filters.html)
另驗證一次界限，讓非最後列使用 `Pilot Table Lead` 樣式，最後列不與下一題
綁在一起。樣式由英文的 reference 準備程式產生，不直接覆寫 upstream binary。

相同 structured 中文輸入在表格實驗環境的結果：0.3.2 兩資料列分在 PDF
第 2／3 頁，0.3.3 兩列都在第 3 頁。Word 預覽也都在第 3 頁，且本輪
Q2／Q3／Q4 可同在該頁；總頁數仍為 PDF 6、Word 預覽 7。
長表格的 48 列在中英 HTML／PDF／DOCX 都各出現一次；中文 PDF 分布於
第 2–4 頁、Word 預覽第 3–4 頁，英文兩種輸出均在第 3–4 頁。
長表格沒有取得短表格標記。多列測試不代表已解決超長單一儲存格的一切問題。

## 驗證與可追溯性

套件建置 checkpoint：

- 英文：`59082118f6f3b21c22eb583681e9a22df58b836b`，0.3.3。
- 中文：`bec61e518ca94a33fa7069a9b9c9cb11443dcd43`，0.3.3。
- 工具：`25e339fbdfb1d20796471055790aad6a4226b6ed`，本輪未改。
- 官方 baseline：`22d60aae4b63ee677477ac0c73097807284aaf9f`，1.30.1，未上移。

英文 54 項、中文流程 29 項單元測試通過；643 個翻譯單位、空白 0，翻譯
及結構稽核皆為空。中英 compiled Common KM 2.7.0 驗證所有 fixture 路徑
可到達；靜態檢查全部 30 個 src Jinja 檔，未定義／不存在 binding 皆為 0。
另有 24 次中英蒐集者×設備狀態 probe，以及原有 512 次 Q1／Q4 措施 probe。
這些是局部 Jinja 檢查，不是額外 536 份 DSW 文件，更不是完整答案涵蓋率。

原版 worker：structured、reading-rich、reading-partial、table-long、
quality-rich、quality-partial、archive-only、empty、negative 九案例，
兩語言三格式，共 54 份全部生成成功。reading／quality checker 各通過
18 個配對。與 0.3.2 六個相同輸入案例作 180 項控制比較：Q2 只排除已辨認
的儀器區塊，其餘各題文字保留；Q2 新敘述另由預期句子、缺答、Word 段落
及格式間保留檢查驗證，不是無條件忽略整題。先驗證三格式 recipe／events／
KM 的 hash 相同，才接受前後比較。

原版仍有 24 筆已知表格阻擋紀錄（六表格案例×兩語言×兩類）；runner
回傳 2，pilot-report.passed=false，沒有偽裝成可發布成品。

表格實驗 worker：前四案例，兩語言三格式，共 24 份全部生成成功；語意、
表格及 reading／quality checker 的 8 個配對均通過。與同 worker 的 0.3.2
structured 有 30 項控制比較。兩種 worker 的 8 個配對使用逐位元相同 ZIP，
三格式的輸入 hashes 相同，十五題 markers 一致，Q2–Q15 文字相同，Q1
表格儲存格內容保留；這仍不是 Q1 全文等價證明。

自由回答反例有兩段正文、兩個清單項目、`v1.2` 及大小寫敏感檔名。
除了 HTML 結構和 Word 獨立段落，亦檢查實際 PDF 文字行座標：兩個正文
段落不能落在同一行或重疊，rich 四處、partial 三處都須保留。
新增負向單元測試會拒絕合併、重疊與漏掉段落的假成品。

## 視覺範圍與仍待處理事項

抽查原版 structured PDF／Word 第 3 頁、reading-rich PDF 第 3 頁；
表格組 structured PDF 第 2–3 頁／Word 第 3 頁、partial PDF 第 3 頁、
長表格 PDF 第 2／4 頁與 Word 第 3–4 頁。短表格移到下一頁會增加前頁
留白，這是保住小型閱讀單位的取捨，不以最少頁數為唯一目標。
26 個案例／語言配對的 PDF 及 10 份 Word 預覽通過紙張邊界檢查。
Word 預覽來自 LibreOffice，尚未在目標 Microsoft Word 環境驗收。

**本輪指定修正通過，不等於整份 DMP 已達正式視覺／內容驗收。**
仍需後續處理：

- Q2 格式／資料量區塊仍有清單及固定短句；部分容量分支仍會因另一數字
  缺填而不輸出，非標準格式理由仍有 capitalize／句號拼接問題。
- Q3 個別條件只填一部分時，尚未逐項提示所有欠缺；資料夾固定清單也
  尚未全面改成敘述。這輪主要驗證公開理由、檔案／物件命名與容量敘述。
- Q1／Q4 品質內容重複、再利用資料的品質對應、Q8／Q14 部分答案的主題
  完整性、全文用語一致與標點節奏，仍需逐題處理。
- 很長的單一表格儲存格、不可斷的長識別碼、圖片／複雜表格仍須新增實際
  格式反例；本輪不聲稱任意回答都已排得好。
- 正式環境的 Markdown 表格支援要作為獨立 runtime 相依決策，不能靠
  中文翻譯或安裝這個模板偷渡解決。

## 版本、重跑與環境

英中 repo 同用短期 `feat/reading-units`，沒有為 0.3.3 建永久分支。
中文仍由已鎖定的客製英文加既有翻譯流程產生，不另維護一套中文條件邏輯。
Q2 已加入 upstream critical overlap；Q1、Q3、macro 原已列入。上游升級
要重跑段落／缺答／表格輸出，不只看 Git 有無衝突。未合併主線、建立 tag、
發布套件或覆寫既有 reviews。報告／測試程式的後續提交由 report hash
識別，套件內容以以上 checkpoint 為準。

原版建置：`outputs/build-3czltj8s`；表格組：`outputs/runtime-tables-ne60xpql`。

- 英文 ZIP SHA-256：`d95317c2e8d99df193abb66ffb77544ff63da3cc41fd0a8e47520ae909126346`
- 中文 ZIP SHA-256：`0a82ee6d84ee003959bbb8d0147b210797bc9ced5cd2ef66f265885c84318911`

```sh
../dsw-document-template-tool/.venv/bin/python scripts/check_reading_outputs.py --build outputs/build-3czltj8s --prior outputs/build-i8o2vf6b --cases structured reading-rich reading-partial table-long quality-rich quality-partial archive-only empty negative
../dsw-document-template-tool/.venv/bin/python scripts/check_reading_outputs.py --build outputs/runtime-tables-ne60xpql --prior outputs/runtime-tables-klu9hu6b --cases structured reading-rich reading-partial table-long
../dsw-document-template-tool/.venv/bin/python scripts/collect_reading_review.py --baseline outputs/build-3czltj8s --variant outputs/runtime-tables-ne60xpql --destination reviews/2026-09-14-reading-units --review-document docs/reading-units-review.md
```

本輪發現舊 `/tmp` bind-mount 設定已遺失。僅依現有 synthetic pilot 的
容器資訊重建隔離設定；沒有刪除資料庫或 volume。新 compose 位於
`outputs/pilot-runtime-i4p70xgd/docker-compose.yml`，設定檔不納入 Git／review。
不再使用失效的 `/tmp/science-europe-pilot.CphfA1/...` compose。
完成後 worker 恢復原版 4.30，image
`sha256:5e5c5e1e436feb49fc4cbcd62c2e0ab2785db2141b0fe40d2926906bcfeaebfc`，
postgres／minio／server／docworker 四服務停回原狀，容器與資料保留。
未使用 keyring、讀寫正式 DSW 專案或觸碰其他正在執行的服務。
