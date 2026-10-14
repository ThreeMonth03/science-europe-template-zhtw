# 中英文模板的日常檢查

## 現行 PO 建置

只修改本 repo 的 `locales/zh-Hant.po`，不修改生成後的中文 Jinja／MO。
`pipeline.yml` 鎖英文及 Tool 完整 commit、TDK 4.35 與建置相依套件。
在隔離環境安裝該 Tool checkout 與本 repo 的 `requirements-dev.txt` 後，沿用：

```sh
python scripts/build.py --english /path/to/english --tooling /path/to/tool --preview
# 提交並符合所有 lock 後才移除 --preview；建置成功仍不等於驗收通過。
python /path/to/english/scripts/check_current.py --build /path/to/build \
  --output /path/to/build/current-behavior.json
```

建置只準備一次英文 reference，產出 `english.zip`、`chinese.zip`（4.34）、
`zh-Hant.po`、`zh-Hant.mo`、`chinese.zip.json`，由同一份 manifest 綁定。
4.35 使用英文 ZIP 加 PO；4.34 使用獨立相容 ZIP。候選保存要求五份產物與
完整 manifest 的雜湊都與驗收報告相符，並拒絕預覽、漏譯、錯配或覆寫版本。

既有 `pilot-checks.yml` 現在以 `profile=current` 檢查 PO 線，沒有新增 workflow。
push／PR／一般手動執行使用三個群組：英文現行單元、中文 PO 建置／候選生命
週期／套件文件單元，以及整合建置。英文群組只用其宣告的獨立相依環境，驗證
TDK source，並執行 `CurrentI18nTests`、`CurrentBudgetLayoutTests`、
`DerivedSubmissionHeadingsTests`、`DocumentMetadataTests` 與全部
`experiments/legacy434` 匯出器測試。中文群組執行 `test_po_build`、
`test_artifact_lifecycle`、`test_package_docs`。整合群組只建置一次乾淨配對，
用官方 4.35 抽取檢查權威 PO，再對實際 prepared packages 執行完整 16 個
雙語行為 suite。JSON 記錄每個 suite 的案例數；verbose unittest log 保留
`Ran N tests` 與失敗細節，失敗也上傳。這是明確選取的現行檢查範圍，
不是將 27,044 個行為案例稱為全 repo 測試。既有 required check `build`
保留，所選 profile 中任何群組失敗、取消或跳過，都不能當作通過。

下方 translation-tree／歷史封印檢查改由同一 workflow 的手動
`profile=historical` 完整五群組回放，不套用到新 PO source。固定配對為中文
`4a1e1086d878c76e99bab794fffa4f806100baed`、英文
`0b06afd1b2983ae53d21232926a3e3b933c468bf`、Tool
`25e339fbdfb1d20796471055790aad6a4226b6ed`（0.3.67）。原英文 source seal
與中文 Word preflight 已在獨立副本重驗通過；不代表完整 hosted CI 已通過。
本機保存的 0.3.78 舊副本已有來源 lock／封印不一致，維持失敗紀錄，不能
以重算封印當成歷史回歸通過。新包仍須有原裝 Worker PDF／Word 逐頁驗收；
CI 綠燈不等於發布、4.34 原生文件驗收或 Microsoft Word 驗收，也不會部署。

英文 repo 的同名既有 workflow 另外執行 8 個現行英文行為 suite，以及原裝
4.35 的 Markdown parser、Word 追溯資訊 guard、4.34／4.35 的 PDF 追溯資訊
分頁／長內容 flow 和英中 reference styles，共 5 項明確原生／樣式測試。英文來源與 Tool
的精確 commit 必須先推上游，再推中文配對；不得用浮動 branch 取代 lock。
以下舊 CI 說明與數字屬 pre-PO 歷史，不冒充此次執行結果。

## 舊翻譯樹歷史基準

`fix/answer-mapping` 目前包含 0.3.78 本機預覽，尚未正式發布或部署。
共用英文 Jinja 經既有工具產生中文；中文 repo 維護譯文與配對設定，
不另寫一套中文 Jinja，也不在產出時用 LLM 補答案。

0.3.75 保留 Q1 不需整合、不使用需先轉成機器可讀形式資料的明確否定答案，
以及 Q10 不編配持續識別碼的選擇；識別碼值空白不再使這項答案消失。
漏填與失效選項不當成否定；已填的識別碼值仍保留。

0.3.76 補回特殊儲存庫的伺服器系統管理與硬體維護安排（已安排／尚未完成），
以及在 Q15 呈現一次其他定期費用（有／無）。兩者不以長期支援能力或儲存庫
服務費代替；漏填與失效答案不推成任一狀態。

## Markdown 與版本配對的界線

目前本機修補將 Q2「採用非標準化格式的原因」，以及 Q3 資料夾／檔案／
物件命名的五個自由文字入口接到既有解析路徑，條件與固定文字不變。
858 組中文譯文內容全部保留；六個 Q3 翻譯檔只更新 Wrapper Key 與追蹤路徑。
中文建置依終端 WeasyPrint 步驟選擇 PDF 字型與行距，同時涵蓋檢核／提交，
不套用到 HTML／Word。不修改 Worker，也不遷移 PO；未提交套件仍是預覽。

0.3.68 在八種格式前加入共用的 Jinja → 官方 Pandoc → 原 Jinja 步驟；
0.3.69 再將已確認的六個自由文字入口接上同一路徑：Q1 再利用用途、
Q2 非儀器資料描述、Q3 後設資料取用說明、Q1／Q4 共用品管詳情，
以及 Q15 資源用途與經費來源。原有溯源、資料登錄入口保持不變。
0.3.70 再接上已確認的九個 Q1 版本／再利用條件、Q6 擬匿名化、Q8 自訂原因／
再利用條件、Q9 同意／處理目的欄位。Q1／Q8 重複呈現仍保留各自歸屬，
單一／多重原因分支不合併。固定導引與作者區塊分開，長答不綁成整頁。
其他行內句子、名稱、金額與整合識別用途沒有一併改動。
中文照原 tool 產生，不另改中文 Jinja，也不更換 worker／Pandoc binary。
原格式 UUID、入口、PDF／Word 轉檔、字型與排版資產保持不變。
新的解析回歸在英文 `tests/test_answer_markdown.py`，原有快速 body adapter
不代表實際 Markdown 解析驗收。完整套件的原生產檔／頁面檢查仍須另驗。

本機未提交的修改只用 `--preview`。目前 `pipeline.yml` 的來源 commit
仍是前版鎖定：發布前須先提交已驗過的英文來源，再填入它的精確 commit。
不能直接以目前預覽宣稱乾淨候選完成，也不改成追蹤浮動分支。

0.3.71 讓 Q8 自訂理由清單自然跨頁，包含長純文字答案；固定短理由的 keep
不變。Q1 版本答案改用標籤加流動內容，移除外層資訊表。原先 PDF 留白與
Word 超正文右界問題仍須用相同輸入修前／修後比較才驗收。
本機配對重播已修復英文長理由留白與兩語版本表格溢出；中文 Q8 原本即可
排入同頁，作為無退化控制。原有理由測試也用鎖定 worker 的實際選擇器引擎
檢查，不只依賴測試用 HTML parser；有限預覽不代表正式發布驗收。
Q8 permission 段落實際沒有 Word keepNext；前批預覽沒有
孤立導引，不代表所有分頁邊界都已保證。

0.3.72 將既有 Q15 的有界兩欄短列規則沿用到 Q8 再利用條件表格，僅處理
資料集清單中作者詳情的直接表格。短而簡單的資料列保持完整，長／複雜列、
表頭、其他題目與相鄰段落仍沿用原分頁；不綁整表、不改 worker 或譯文。

0.3.73 僅覆寫既有有界 Q15 預算列的 Word 名稱段連頁屬性，保留短列完整性
與重複表頭。歷史表、未標記／無界列及共用名稱樣式不變。Local 單因素對照
已將英文檢核版留白定位到名稱段的連頁設定；不代表 Microsoft Word 實機
或所有輸入的分頁保證。中文仍沿既有流程產生，不另改中文 Jinja。

0.3.74 補上 Q9 的 DPIA 明確「否」答案，文字標明是依問卷填答，
不代表獨立法律評估。漏填與失效分支不當成否定答案；兩語保留原有「是」句。

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
八組共涵蓋每語言 13,522 個組合，檢核／提交、漏填／明確否、內容保留、
編號、跳脫及分支有效性等斷言沿用同一份英文測試程式，沒有複製中文測試。
各組定義與完整命令見英文 repo 的 `docs/testing.md`。

## CI 配對整合：不可單獨推送 workflow

本輪補上的 workflow 命令會在候選建置後檢查英文與中文兩棵目錄。
`pipeline.yml` 必須鎖定包含新 runner 的英文精確 commit：先推英文，再一起
推送中文 workflow 與來源鎖定更新。不能改成追蹤浮動 branch 或略過檢查。
本次候選使用 0.3.54 身分，不能覆寫既有 0.3.53 套件。

英文 `make check` 已透過 unittest discovery 使用相同入口。既有歷史
原始碼／Word 參考檔檢查仍全部保留，未改成 skip；新增的候選差異契約會先
精確驗證整棵來源、異動範圍、支援檔與登記的 0.3.54 身分，再提供 0.3.51 舊版視圖。
前批英文 297 項、中文 482 項單元測試、TDK 驗證及兩邊 workflow 的命令
已在本機通過；現行雙語行為檢查通過 17,980 組合。歷史版本的投影測試另計，
不能宣稱是在測目前的文句。另以斷網的完整 worker 重播中英文檢核／提交案例，
涵蓋大量漏填、資料儲存庫組合與超長回答：28 次產出共 154 頁原生 PDF、
140 頁 LibreOffice Word 預覽。機械掃描未發現空白頁、文字越界、缺字型或空標題，
受影響頁面亦經人工檢視；案例內 96 筆啟用的非空自由文字都保留。
這仍不是所有輸入組合或 Microsoft Word 驗收。本機結果不等於 GitHub Actions
成功，遠端須以配對提交的實際執行結果為準，也不能宣稱發布完成。
前版 0.3.52 本機複驗涵蓋 26,940 組雙語行為案例、同一批 4,000 次隨機漏填渲染、
28 組原生產檔及全部 185 頁提交 PDF／LibreOffice 預覽的逐頁檢視。
此證據綁定受測來源雜湊；乾淨配對候選必須保留相同渲染輸入，不能只換版號
便宣稱任意輸入或 Microsoft Word 全面通過。歷史輸出與本輪成品證據分開。
0.3.54 的 Word 修正已在本機驗證 52 組中英文檢核／提交產出與全部 356 頁預覽，
涵蓋相鄰長資源表、14–18 段的分頁邊界、漏填與長文控制；英文 334、中文 492 項
單元測試通過。只更動長表的分隔與短末列規則，801 份譯文、PDF 資產與歷史
驗收基準保留。新套件仍須核對與已驗收修正版的渲染輸入一致，不以版號代替驗證。
多個歷史失敗可能源於同一個未登記的來源層，不代表新增同樣多個排版問題；
舊文句／段落數期待仍須核對修正意圖，不能直接略過。

## CI 耗時與排程

維持原本的 workflow 與總檢查名稱，不增加長期分支或另一套 CI。全部既有
檢查指令保留，改成五個固定並行群組：鎖定英文單元測試、中文單元測試、
套件整合／目前答案、譯文範圍、原生 PDF／Word。英文 repo 則分單元測試與
原生回歸兩組。原本的 `build`／`contract-and-template` 成為總檢查，只有
所有群組成功才通過；失敗、取消或跳過都不算成功。某組失敗不取消其他組。

每組自行取得相同精確來源鎖定與經雜湊驗證的公開問卷模型，不依賴前一組
下載的檔案。三個需要套件的群組各自建置；不搬運準備目錄或沿用別組輸出。
31 個原生回歸仍由 `scripts/check_native_regressions.sh` 按中英文分成兩路，
每路內依序執行；任何一路失敗，原生群組即失敗。

同分支／PR 的舊執行會被新提交取消；手動執行各自獨立，不被新提交取消。
兩路的完整 log、逐項秒數／退出碼及所有 JSON 報告在失敗時仍上傳 artifact，
保留 14 天。只有整合組上傳候選 ZIP，譯文／原生組各自上傳診斷報告，避免
名稱衝突與重複套件。GitHub 的 job／step 頁面可直接比較各組耗時。
PDF 測試僅共用相同 CSS／媒體的字型與樣式編譯結果，不快取文件或答案，
且須確認優化前後文字、座標與分頁一致。
最近兩次完整中文 CI 約 29、33 分鐘；並行後的改善須以實際推送紀錄確認，
不能拿本機時間當成 GitHub 加速倍數。並行主要減少等待，未必減少計費分鐘。

目前不移除歷史原生測試，也暫不取消中文 CI 對精確英文來源的獨立驗證。
舊 Q3 接句引擎回歸先驗證完整候選來源，再使用只還原 Q3 問句的測試視圖；
字型、CSS、Word helper 與其他題目仍用目前來源。視圖不是套件，其歷史範圍
與來源雜湊另存 JSON；不能把舊版文句比對當成目前中英文語氣驗收。
日後將歷史回放降頻，須先補上乾淨 runner 可重播的「目前完整套件」原生案例；
不可只留下快速的 reply adapter 測試。這次調整不改模板位元組或發布狀態。

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

## Word 變更紀錄的分頁界線

版本表只對有名稱、長度受限且內容單純的紀錄列加入列內不分頁屬性。
長列、複雜內容與空名稱維持原行為，不把整張版本表綁在同一頁。
中英文的檢核／提交版已以多筆、缺說明、長短混合及不變控制案例核對；
短列不再拆頁、長列仍可跨頁，HTML／PDF 與其他 Word 內容保持不變。
這是 LibreOffice 預覽及 DOCX 結構驗證，不代替 Microsoft Word 實機驗收。
升級時須一起核對版本表標記、`short-tables.lua` 與 `short-tables.xml`，
沿用既有列處理，不另養一套中文分頁邏輯。
