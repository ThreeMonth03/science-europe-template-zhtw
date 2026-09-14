# 0.3.5：缺答提示、數字單位與共享段落審閱

2026-09-14。本文件另封存為 `reviews/2026-09-14-reading-polish/README.md`，
下列樣張連結以該封存目錄為準。本輪仍為合成回答、隔離本機 DSW 的實驗，
不是正式發布或全部 Science Europe 內容／中文／Microsoft Word 驗收。

## 先看成品

以下使用表格修補 worker；同一份套件在原版 worker 的結果保留於 `stock/`：

- 一般案例：[中文 PDF](tables/structured-chinese.pdf)、[Word](tables/structured-chinese.docx)。
- 缺答提示：[中文 PDF](tables/format-partial-chinese.pdf)、[Word](tables/format-partial-chinese.docx)。
- 微小容量與自由回答：[中文 PDF](tables/format-rich-chinese.pdf)、[Word](tables/format-rich-chinese.docx)。
- 多個共享管道：[中文 PDF](tables/storage-sharing-chinese.pdf)、[Word](tables/storage-sharing-chinese.docx)。
- 部分共享資訊：[中文 PDF](tables/storage-sharing-partial-chinese.pdf)、[Word](tables/storage-sharing-partial-chinese.docx)。
- 長篇限制條件：[中文 PDF](tables/narrative-long-chinese.pdf)、[Word](tables/narrative-long-chinese.docx)。
- 英文對照：[PDF](tables/structured-english.pdf)、[Word](tables/structured-english.docx)。
- 原版 worker 全空案例：[PDF](stock/empty-chinese.pdf)、[Word](stock/empty-chinese.docx)。

## 修改範圍

**Q2 缺答提示**：每個格式只寫一次「尚待補充」，以頓號串接缺少的欄位，
最後一個句號；英文使用英文清單標點。每個缺項仍保留獨立 fact ID／missing
標記，已填的事實不會因旁邊缺答而消失，也不把缺答寫成已承諾的安排。
原先 0.3.4 的「自由填答不擅加句號、不改檔名大小寫」規則保留。

**Q2 數字單位**：短值與 GB 使用不換行空白，PDF 另加局部 nowrap；
Word 保留實際 U+00A0。未改全域換行，也不把長篇自由文字鎖成不可換行。
範圍是數值與 GB，不是所有含單位的標籤或所有日期。

**Q10 段落**：公開／限制取用的固定敘述，可與簡單的國家／機構／計畫專用
儲存庫說明合段；CC0／CC BY 的固定授權句可接續。只處理明確標記的模板
區塊。資料管道標籤、缺答提示、自由回答、受限授權詳細條款及複雜儲存庫區塊
仍是邊界，不為了排成長段落而把它們全部攤平。

主要邏輯仍維護於客製英文 Jinja；繁中仍經既有翻譯樹與工具產生，沒有另寫
第二套中文條件邏輯，沒有使用 JSON／LLM 改寫使用者回答。

## 實際產檔抓到的問題

第一次 0.3.5 建置 `outputs/build-u84mkie4` 雖然生成了 42 份文件，完整 Q10
檢查仍失敗：較長、含受限授權的 distribution 不符合短段落規則，而 Word Lua
修改後沒有回傳該 Div，合段結果被捨棄。修正於英文 `f8b7aaa`，不是放寬文字
檢查來通過；此輪正式審閱樣張重新建置、重新產出。

另確認 Pandoc 可能不保留 HTML p 的 class，故缺答須以明確的外層 Div 保留
段落邊界。檢查器用實際 DOCX paragraph 判斷合段／隔離，不只看 HTML class。
失敗重跑也會覆寫成功狀態，避免較小案例集的舊成功報告被誤用。

## 驗證結果

- 英文 64 項測試及 TDK verify 通過，中文 40 項測試通過。
- 656 個翻譯單位，空白翻譯 0；translation／structure audit 無錯誤。
- 76 組格式／容量、24 組蒐集方式、512 組品質措施雙語 probe 通過。這是本機
  reply adapter 分支測試，不是 612 次 DSW 產檔。
- 沿用的 fixtures 已通過編譯後英中 Common KM 2.7.0 路徑檢查。30 個 Jinja
  檔案的靜態 binding audit 無未定義變數或不存在實體，不等於問卷答案全覆蓋。
- 表格修補 worker：6 案例 × 2 語言 × HTML／PDF／DOCX = 36 份產出，
  所選語意／表格檢查通過；polish／format／reading／quality 輸出檢查亦通過。
- 原版 worker：7 案例 × 2 語言 × 3 格式 = 42 份產出，語意檢查通過；
  六個含表格案例仍有 24 筆既知阻擋（2 語言 × 2 類檢查），不是 24 個新根因。
  其 acceptance 仍為 false，沒有忽略失敗後發布。
- 原版 14 組與表格版 12 組案例／語言的 polish、format、reading、quality 檢查
  均通過。相同輸入的 0.3.4 比較：原版 120、表格版 90 個題目比較通過；
  沒有舊版同名案例的 storage-sharing／partial／narrative-long 不算入這個數字。
- 兩種 worker 的 12 組對照確認英中 ZIP、回答事件、recipe、KM 相同；15 題
  fact markers 不變，Q2–Q15 文字不變，Q1 表格儲存格內容保留。不是 Q1 全部
  散文等價或全問卷覆蓋率的證明。
- 所有本輪 PDF 與 14 份 LibreOffice 預覽的文字座標均未越出頁面。表格版的
  短溯源表格仍同頁，一般英中案例在 PDF／Word 預覽皆為第 3 頁；本輪未重跑
  48 列長表案例。長篇限制回答的各段在 PDF／DOCX 仍保留，不因合段而消失。

`polish-report.json` 檢查 Q2 每段缺答只出現一次引言及句號、每個 missing fact
仍在；Q10 合段必須與實際 Word 的單一段落完全相符，自由回答與缺答也要分開
對應 Word 段落。數字單位同時檢查 Word 的 U+00A0 與 PDF／預覽的實際同行座標。

`format-report.json` 與 0.3.4 比對時，只排除 Q2 明確識別的格式區塊，不排除
整題 Q2 或 Q10。`reading-report.json`／`quality-report.json` 本輪不使用其舊版
專用的 `--prior` 比較。所有報告均綁定套件與產物 checksum，release acceptance
仍為 false；原始內嵌字型的 HTML 保留在本機 outputs，不放入 Git 審閱封存。

## 人工觀察與未完成項目

| 中文案例 | 原版 PDF／Word 預覽 | 表格版 PDF／Word 預覽 |
|---|---|---|
| 一般案例 | 6／7 | 6／7 |
| 微小容量與自由回答 | 6／7 | 6／7 |
| 部分格式缺答／零值 | 6／7 | 6／7 |
| 多個共享管道 | 7／8 | 7／8 |
| 部分共享資訊 | 6／8 | 6／8 |
| 長篇限制回答 | 9／10 | 9／10 |

已人工檢視表格版 Q2 微小容量／缺答的 PDF 及 Word 預覽第 3 頁、多共享管道
PDF 第 5 頁與 Word 第 5–6 頁、部分共享資訊 PDF 第 5 頁、長篇回答 PDF 第 6 頁。
這不是每份每頁的人工審美驗收。格式缺答案例的表格版 Word 由 0.3.4 的 8 頁
降至 7 頁；不能只用頁數下降判定成功，仍需同時保留已填事實及缺答提示。

Q10 固定措施已較連續，但不是每個區塊都完成中文編修。多管道案例的受限
授權日期、限制引言、作者自由回答仍分段；其網址後仍沿用英文句點。
Q11 的保存安排也仍偏零碎，「本計畫／專案／我們」尚待全文一致性審閱。

Word 預覽可見日期 `2027-12-31` 跨行；本輪只修數值與 GB，不宣稱已修日期。
Q2 缺答標籤的「預估平均檔案大小（GB）」仍可能只把括號單位排至次行，
與數值 `0.0001 GB` 的不換行處理是不同範圍，不能混為已解決。
受限授權整塊可以跨頁，這是避免把長回答鎖死，但頁間銜接仍有改善空間。
LibreOffice PDF 預覽不是實際 Microsoft Word，不把兩者視為同一驗收環境。

下一輪優先採用同一組回答，整理 Q10 受限授權與 Q11 的模板固定句、日期換行
及全文術語；自由回答仍保留作者段落。再用去識別真實專案檢查「已填回答是否
有對應輸出」，與 Science Europe 要求逐項核對，不能只用字數或頁數判斷完整。

表格問題必須另外決定正式 runtime 路徑：目前的修補 worker 是受控反證實驗，
不是模板 ZIP 本身就能修好原版服務的 Markdown parser。正式採用前需由維運方
確認 upstream 納入或自有 worker 的維護責任、版本鎖定、升級測試及回退方案。
本輪沒有部署這個 worker，也沒有建立可上線的 release。

## 版本與可重現性

英中工作分支均為短期 `feat/reading-polish`，版本 0.3.5。真正的來源對應靠
`pipeline.yml` 完整 commit 與 manifest／套件 checksum，不靠同名 branch。
官方基底仍為 1.30.1／`22d60aae4b63ee677477ac0c73097807284aaf9f`。
Q2、Q10、共用 macro、PDF CSS、Word Lua 都是自有升級審閱面；未來 upstream
更新須重跑缺答／自由回答／雙語成品測試，沒有 Git 衝突不等於可以直接採用。

實際產檔來源為英文 `f8b7aaad355d82b6011685b4bf283f973cc2fdf9`，
中文 checkpoint `29c22bc32eb39a897b83d98c7545d6ed07b06923`；工具仍鎖定
`25e339fbdfb1d20796471055790aad6a4226b6ed`。

英文 ZIP：`57bf56f0b7855f822e0c1c61e7404dffb66edd643d354ed546526dcc0653a5e8`。
中文 ZIP：`b9eab974616dc0d704a3e6c9a6b452d5d2a42bd70502641e35f5a5496e98c772`。

英中套件各使用 `PACKAGE_README.md`，repo README 僅作導覽。metadata 時間
取最後一次英文套件輸入變更，而非無關文件提交時間。英文新增 README 連結
後為 `7d991b69fd3862a9932fe5cf1965be0d4060846f`；中文更新 lock／文件後為
`b444913256bf208eb94915fc358d15b001f46110`。乾淨重建
`outputs/build-yna95k87` 的兩個 ZIP 與實際產檔版本逐位元相同；時間戳同為
`2026-09-14T03:36:37Z`，佐證 manifest 另封存為 `rebuild-manifest.json`。
這次純導覽變更不再使中文套件產生無意義的新 checksum。

## CI 與操作邊界

- 英文來源 [CI 34803336207](https://github.com/ThreeMonth03/science-europe-template/actions/runs/34803336207) 通過。
- 中文鎖定建置 [CI 34803407927](https://github.com/ThreeMonth03/science-europe-template-zhtw/actions/runs/34803407927) 通過。
- 工具 `fix/minio-ci-images` 的 [CI 34801962645](https://github.com/ThreeMonth03/dsw-document-template-tool/actions/runs/34801962645)
  通過 offline checks 及 DSW 4.26／4.30 的實際 render regression。
  MinIO 映像來源及 digest 修正與模板 lock 分開；詳見 repo 的
  `docs/ci-repair-2026-09-14.md`。

工具修復分支尚未合併，故不能說 master 每日排程已恢復；其排程另含發布副作用，
沒有手動觸發。未合併主線、未建立 tag／release、未 stage 或部署線上 DSW，
未讀取 keyring 或修改線上 project。舊審閱樣張保持不變。

本機原版建置為 `outputs/build-1bsndkwy`，表格對照為
`outputs/runtime-tables-yg5620t8`。worker 已恢復為原版映像
`sha256:5e5c5e1e436feb49fc4cbcd62c2e0ab2785db2141b0fe40d2926906bcfeaebfc`，
四個 pilot 容器均已停止；資料 volumes 保留，沒有清除其他服務。
