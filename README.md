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
最新 0.3.8 樣張見 [Word 間距與保存政策對照](reviews/2026-09-14-word-rhythm/README.md)，
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
