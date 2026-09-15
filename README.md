# Science Europe 客製繁體中文模板

這個 repo 翻譯 `ThreeMonth03/science-europe-template` 的客製英文模板。
原有 `depositar/science-europe-template-zh_Hant` 仍對應官方英文來源。

目前已由 Q1／Q5／Q15 切片擴充到十五題的合成輸出案例，另修正 Q3／Q12 的
部分漏出與錯誤否定分支；尚未宣稱全部 15 題完成內容驗收。
這是衍生客製模板，不代表 Science Europe 認可；目前不得當作已驗收正式版發布。
先看 [實驗結論](docs/pilot-results.md) 及 [PDF／Word 樣張](reviews/2026-09-11/README.md)。
下一輪 0.2.0 的內容與維護邊界見 [中文閱讀品質修改](docs/readability-review.md)。
前輪文件在 [0.2.0 中文 PDF／Word 樣張](reviews/2026-09-11-readability/README.md)。
0.2.1 實驗與原版英文對照見 [回答保留審閱](reviews/2026-09-11-answer-retention/README.md)。
0.2.2 的 HTML／worker 表格分層修正見 [結構與表格審閱](reviews/2026-09-11-structure-tables/README.md)。
0.3.0 樣張及已知問題見 [儲存與共享閱讀審閱](reviews/2026-09-11-storage-sharing/README.md)。
0.3.1 樣張見 [敘述與分頁審閱](reviews/2026-09-11-narrative-pagination/README.md)。
0.3.3 樣張見 [閱讀單位與短表格審閱](reviews/2026-09-14-reading-units/README.md)。
0.3.4 樣張見 [格式與容量審閱](reviews/2026-09-14-format-volume/README.md)。
0.3.5 樣張見 [缺答提示、數字單位與共享段落審閱](reviews/2026-09-14-reading-polish/README.md)。
0.3.6 樣張見 [共享限制、保存敘述與日期審閱](reviews/2026-09-14-sharing-preservation/README.md)。
0.3.7 樣張見 [保存回答覆蓋審閱](reviews/2026-09-14-preservation-coverage/README.md)。
0.3.8 樣張見 [Word 間距與保存政策對照](reviews/2026-09-14-word-rhythm/README.md)。
0.3.9 樣張見 [缺答與否定回答審閱](reviews/2026-09-14-answer-states/README.md)。
0.3.10 樣張見 [儲存庫管道對照與短清單分頁](reviews/2026-09-14-repository-reading/README.md)。
0.3.11 樣張見 [儲存庫聯繫回答歸屬與跨題引用](reviews/2026-09-14-repository-contact/README.md)。
0.3.12 樣張見 [Q11 資料脈絡與保存敘述連讀](reviews/2026-09-14-preservation-context/README.md)。
0.3.13 樣張見 [論文參考列與長網址完整性](reviews/2026-09-15-paper-reference/README.md)。
0.3.14 樣張見 [Q13 閱讀單位與整份分頁](reviews/2026-09-15-identifier-reading/README.md)。
0.3.15 樣張見 [識別碼追問、缺答分組與跨頁修正](reviews/2026-09-15-identifier-followups/README.md)。
0.3.16 樣張見 [短預算的 Word 連頁對照](reviews/2026-09-15-budget-pagination/README.md)：
短篇資源說明與預算表改為同頁，中文仍為 8 頁；長表格與整份留白尚未完成驗收。
0.3.17 樣張見 [長預算的全寬用途與續頁歸屬](reviews/2026-09-15-long-budget-reading/README.md)：
長篇 Word 保留完整回答，續頁帶出名稱／金額／經費來源；原生 PDF 與中文措辭未改。
0.3.18 樣張見 [長預算的分頁與留白](reviews/2026-09-15-budget-spacing/README.md)：
原生長 PDF 英文 13 → 11 頁、中文 12 → 10 頁，預算標題不再孤立；
英文 Word 10 → 9 頁。只改英文共用樣式，短／多筆控制組不變；
新增固定 worker 引擎的 CSS 探針。PDF 用途欄寬、續頁歸屬及整份閱讀品質仍待驗收。
0.3.19 樣張見 [PDF 長篇用途全寬與續頁歸屬](reviews/2026-09-15-pdf-budget-reading/README.md)：
中文長篇 PDF 10 → 9 頁、英文 11 → 10 頁；續頁保留資源名稱、金額與經費來源。
Word、HTML 和短／多筆控制組不變；原有 720 組譯文保留，只新增兩個幣別分支複本。
中英尾頁仍有留白，下一步回到整份中文閱讀與接近真實篇幅的案例。
0.3.20 見 [中英文漏填、續頁與 Q7 轉換修正](reviews/2026-09-15-missing-info-reading/README.md)：
修正 Q7 部分漏答提示、長 PDF 漏預算資訊時的續頁歸屬，以及空白中文 Q15 孤立提示。
初輪 22 份 PDF 抓到 Q7 中文段落未閉合，修正後另重產中英 Q7 與兩組控制組，
增加 6 份 PDF。初輪失敗紀錄與最後通過結果分開保存；未重產案例有明確的
套件／分支差異證明，不混稱全部使用最後 ZIP。短欄提示密度與整體留白仍待改善。
0.3.21 的 [個資追問與缺答修正](docs/personal-data-followups.md) 進一步處理 Q7
的漏填／明確否定、自由回答區塊，並移除 Q9 超出填答內容的固定推論；
版型和短預算欄寬未改，原生樣張驗證與既有發布門檻分開看待。
已完成 [8 組中英文 PDF／Word 原生對照](reviews/2026-09-15-personal-data-followups/README.md)：
每種格式各 16 份，缺答與內容保留檢查通過。但中文完整 Word 的 Q8 資料集名稱
與授權說明在第 4／5 頁分離，已保留失敗檢查；整份文件仍未驗收、未發布。
CI 失敗原因及隔離依賴修正見 [CI 修正紀錄](docs/ci-repair-2026-09-14.md)。
這批樣張仍包含已知失敗，不可作為已驗收的理想 DMP。
中文 Jinja 由既有 `dsw-document-template-tool` 的翻譯樹產生；主要分支邏輯
維護在英文 repo。翻譯來源是 `translation/**/translation.md`。

`pipeline.yml` 分開記錄英文來源版本與中文輸出版本。開發預覽允許明確標記的
未提交修改；正式建置要求來源與工具為乾淨且符合 lock 的 commit。

先 checkout `pipeline.yml` 中的英文與工具 commit，並在工具的 `.venv` 執行
`pip install -e '.[dev]' -r ../science-europe-template-zhtw/requirements-dev.txt`。
正式候選建置不加 `--preview`；候選建置成功不代表成品驗收通過。

```sh
../dsw-document-template-tool/.venv/bin/python scripts/build.py \
  --english ../science-europe-template \
  --tooling ../dsw-document-template-tool --preview
```

第一次建立或英文修改後加上 `--refresh`，會重新抽取並精確遷移現有翻譯。
初次匯入舊官方中文樹可指定 `--seed-tree PATH`。沒有精確對應的單位保留空白，
需由譯者編修。空白翻譯的預覽可能顯示英文，不能作為已完成的中文版本發布。

每次建置建立新的 `outputs/build-*` 目錄，保存英中套件、展開來源、翻譯檢查
與 manifest，不覆寫前次結果。正式版本須另通過成品驗收與不可覆寫的發布步驟。

字型：PDF 包含 Noto Sans TC；Word 的東亞字型使用 Noto Sans CJK TC，
開啟端字型替代可能影響分頁，需在實際使用的 Word 環境確認。

成品測試限隔離的本機 DSW（預設 `localhost:13300`），使用合成回答與公開
測試帳號，不讀取線上 keyring、不修改線上 project。先在英文 repo 產生並驗證
`fixtures/pilot`，再執行：

```sh
../dsw-document-template-tool/.venv/bin/python scripts/run_pilot.py \
  --build outputs/build-REPLACE_ME --english ../science-europe-template \
  --tooling ../dsw-document-template-tool
```

已知 Markdown 表格失敗會令此命令回傳 2，並留下 `pilot-report.json`；不可
將它忽略後發布。CI 僅涵蓋建置與單元測試，沒有假裝完成 Word／視覺驗收。
下一步與版本政策見 [版本管理](docs/version-management.md)。

原始英文源碼及本 repo 的程式碼採 Apache-2.0；保留上游貢獻者及授權。
初始翻譯精確沿用自 `depositar/science-europe-template-zh_Hant` 的已審閱樹，
來源 commit 記於 `pipeline.yml`。Science Europe 指南內容依原出版物署名，
Noto 字型依隨附 OFL 授權。本 repo 不維護第二套獨立中文分支邏輯。
