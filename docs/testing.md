# 中英文模板的日常檢查

目前仍是 `fix/answer-mapping` 的未發布修正，正式鎖定來源仍為 0.3.51。
共用英文 Jinja 經既有工具產生中文；中文 repo 維護譯文與配對設定，
不另寫一套中文 Jinja，也不在產出時用 LLM 補答案。

## 共用入口

假設三個 repo 分別位於 `../science-europe-template`、本 repo 與
`../dsw-document-template-tool`，已安裝各自宣告的相依套件。
在本 repo 執行：

```sh
# 未提交的本機修正必須明確使用 preview；不是可發布套件。
SE_BUILD_DIR=$(../dsw-document-template-tool/.venv/bin/python scripts/build.py \
  --english ../science-europe-template --tooling ../dsw-document-template-tool --preview)
../dsw-document-template-tool/.venv/bin/python ../science-europe-template/scripts/check_current.py \
  --build "$SE_BUILD_DIR" --output "$SE_BUILD_DIR/current-behavior.json"
```

已有同一份來源的建置目錄時，直接重跑第二個命令，不必每次重建。
只改某題時可加 `--suite repository_profiles` 等選項；整合前跑完整八組。
八組共涵蓋每語言 8,990 個組合，檢核／提交、漏填／明確否、內容保留、
編號、跳脫及分支有效性等斷言沿用同一份英文測試程式，沒有複製中文測試。
各組定義與完整命令見英文 repo 的 `docs/testing.md`。

## CI 配對整合：不可單獨推送 workflow

本輪補上的 workflow 命令會在候選建置後檢查英文與中文兩棵目錄。
`pipeline.yml` 必須鎖定包含新 runner 的英文精確 commit：先推英文，再一起
推送中文 workflow 與來源鎖定更新。不能改成追蹤浮動 branch 或略過檢查。
目前仍沿用實驗用 0.3.51 身分，這不授權覆寫既有發布套件。

英文 `make check` 已透過 unittest discovery 使用相同入口。既有歷史
原始碼／Word 參考檔檢查仍全部保留，未改成 skip；新增的候選差異契約會先
精確驗證整棵來源、異動範圍、支援檔與未變的 0.3.51 身分，再提供舊版視圖。
目前英文 297 項、中文 482 項單元測試、TDK 驗證及兩邊 workflow 的命令
已在本機通過；現行雙語行為檢查通過 17,980 組合。歷史版本的投影測試另計，
不能宣稱是在測目前的文句。另以斷網的完整 worker 重播中英文檢核／提交案例，
涵蓋大量漏填、資料儲存庫組合與超長回答：28 次產出共 154 頁原生 PDF、
140 頁 LibreOffice Word 預覽。機械掃描未發現空白頁、文字越界、缺字型或空標題，
受影響頁面亦經人工檢視；案例內 96 筆啟用的非空自由文字都保留。
這仍不是所有輸入組合或 Microsoft Word 驗收。本機結果不等於 GitHub Actions
成功，遠端須以配對提交的實際執行結果為準，也不能宣稱發布完成。
多個歷史失敗可能源於同一個未登記的來源層，不代表新增同樣多個排版問題；
舊文句／段落數期待仍須核對修正意圖，不能直接略過。

## 不再每輪另建一套測試

一般修正：改共用模板／譯文 → 擴充既有案例 → 跑受影響組別 → 配對驗證。
CSS、Word filter 或樣式變動才擴大原生排版驗證範圍。
保留原題、緊縮空白；未具名但有內容的項目保留中性編號；提交版不加
漏填提示，但不能因此隱藏明確的否定答案或使用者原文。

這套快速檢查使用簡化的 Markdown／reply adapter，不是完整 worker，
也不能自動保證中文語氣、PDF 分頁或 Microsoft Word 顯示。既有原生引擎
檢查與中英文實際頁面審閱仍不可省略；LibreOffice 預覽不能代稱 Word 驗收。
先前私有測試依賴本機快照與自建 worker，仍留在本機，不冒充乾淨 CI 可重跑的
流程。本輪不另增原生 runner；公用的完整 worker 合成案例仍是後續工作。

八份逐輪 development 文件已收斂到本頁與英文指南，刪除前的原檔已在本機
封存，可還原；既有已提交的歷史證據未刪除。往後只記錄重要的長期決策，
數值結果放 `outputs/`，不要再為每輪增加大量重複說明。真實專案與憑證不進 Git。
