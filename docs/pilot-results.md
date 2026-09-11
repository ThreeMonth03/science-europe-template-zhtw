# 英中模板端到端實驗結果

2026-09-11。判定：路線可行，但尚不可當作正式完成的 DMP 模板發布。
本輪用合成回答及隔離的 DSW 4.30 測試，沒有讀取或修改線上專案／keyring。

## 已建立的串接

官方 1.30.1 → 客製英文 Jinja → 既有 expand／translation tree／sync → 客製中文。
不維護第二套中文分支邏輯，不加入 runtime LLM 或 JSON-to-prose 替代流程。
JSON 在本實驗只用於正常的 DSW 測試輸入、metadata 與驗收報告。

| 層次 | 本輪固定來源 |
| --- | --- |
| 官方基底 | `22d60aae4b63ee677477ac0c73097807284aaf9f`（1.30.1） |
| 客製英文 | `93fc4ff5994a79df6f64a972966ee1b6daaa5e09`，0.1.0 |
| 客製中文 | 建置 commit 見 review manifest；來源 lock 與中文輸出版本分開 |
| 工具 | `25e339fbdfb1d20796471055790aad6a4226b6ed` |
| KM | `dsw:root:2.7.0`、`dsw:root-zh-hant:2.7.0` |
| runtime | DSW／worker 4.30，TDK 4.30.2；實際 Docker image IDs 記於 review |

中文模板的新 ID 為 `threemonth03:science-europe-enhanced-zhtw:0.1.0`，
英文為 `threemonth03:science-europe-enhanced:0.1.0`。原有官方繁中 repo 未修改。

## 內容、語序及中文

Q1／Q5／Q15 為先行切片：

- 缺少父題不預設成 No；部分子題缺漏會顯示「尚待補充」，保留其他已填資訊。
- 資料重用目的、版本、培訓內容等改成完整引導句／標籤加獨立內容區塊；
  不再把任意長段落或中文清單硬接到英文 `in order to` 後面。
- 機器用的 requirement／fact IDs 移出翻譯文字；中文可在結構保護下重排 placeholder。
- 中文新增文字採研究計畫書面語，保留否定、未定及計畫中的語氣；沒有自動替使用者補答案。
- 632 個翻譯單位沒有空白，翻譯及結構 audit 通過；沿用既有已審閱翻譯，
  不等於本輪已逐句重審其餘 12 題。

五種輸入為空白、明確否定、部分回答、已填回答、長文字。每種各有英中 HTML、
PDF、DOCX，共 30 個產物。合成案例包含兩筆重用資料集、刪除其中一筆使用目的、
刪除一筆幣別但保留金額、5000／0 TWD、Markdown 多段文字與列表，以及表格探測。
路徑另與 DSW 編譯後的英中 KM graph 核對，不只依模板中的 UUID 猜測。

最終以乾淨、鎖定的三個 checkout 重跑：**30／30 格渲染成功，10 組英中案例的
所選事實／狀態檢查通過；整體驗收仍失敗。** 表格產生 12 筆缺口紀錄（6 個
語言案例，各記 HTML 表格及 Word 可編輯表格缺口），不是 12 個不同根因。
[`review`](../reviews/2026-09-11/README.md) 保存樣張與報告；實際呼叫候選封存
也被拒絕，沒有建立候選發布目錄。

`data-status="complete"` 在此只代表所測欄位已提供，不代表回答實質充分或符合
全部 Science Europe 要求。這一點須與 [Science Europe 的內容要求及評估 rubric](https://www.scienceeurope.org/our-priorities/open-science/research-data-management/)
分開判斷。

## PDF 與 Word 分開處理

PDF 使用自有 layout layer、內嵌 Noto 字型、標題與首段同頁、長區塊可跨頁、
段落／清單間距及頁尾留白。未命名版本的空白紀錄頁不再出現。

Word 由相同資料邏輯經獨立 reference styles 和小型 Pandoc 標籤 filter 產生。
已取消舊 Heading 2 每題群強制換頁，設定東亞字型、段距及標籤 keep-with-next，
並在建置副本移除官方 logo，避免暗示客製版受到背書。原始 Word reference
仍保留在英文 Git 歷史中，客製樣式可重做，不靠手改發布後的 docx。

實際 PDF 頁面及 Word 經 LibreOffice 轉出的頁面有做抽樣影像檢查；Word
仍為可編輯的段落／清單，不是貼上 PDF 截圖。但未在 Microsoft Word 開啟，
不能宣稱各 Word 版本、作業系統和字型替代結果完全相同。

## 真正跑過的升級與修版

官方 `1.30.0 → 1.30.1` 回放使用獨立 snapshot，不改客製分支基底：

| 檢查 | 結果 |
| --- | --- |
| 官方變更 | 15 檔，67 行新增／62 行刪除；不只是 metadata |
| 1.30.0 既有翻譯整理 | 608 單位中沿用 607，1 單位空白 |
| 遷移到 1.30.1 | 611 單位中精確沿用 529，82 單位待審閱 |
| 同一已填案例的 Q1／Q15 `<p>` 內巢狀 block | 1.30.0 為 0／0，1.30.1 為 8／2 |

舊翻譯來源為 `science-europe-template-zh_Hant-v1.30.0-round3` 的
`b4a9ba93ffd3d57f0cbd8586baa13709a6f65edb`。82 是本次保守遷移產生的
待審閱數，不是保證未來每次 patch 都要重翻 82 句。測試只回放官方更新對抽取與
渲染的影響，不宣稱模擬了所有客製 merge 衝突，也未重譯這 82 單位。

升級判斷是：接納資料路徑／拼字修正的目的；對已重寫句型和 Word 樣式，按目的
移植，不直接覆蓋。例如 1.30.1 的 `markdown` 改善富文字支援，卻也在原本行內
位置造成巢狀段落，不能照單全收。官方基底仍固定 1.30.1，沒有假稱已合併不存在
的新版本。

中文 0.1.0 → 0.1.1 的獨立修版演練則固定英文 commit 和工具：英文 ZIP 的
SHA-256 必須完全相同，中文 ZIP 與套件版本不同，證據另列 `version-rehearsal.json`。
正式版號只准由已提交的設定產生；preview override 不能進候選封存。

重建也抓到既有工具的全域 file UUID 碰撞：複製模板只換外層 ID 時，新模板會
匯入成沒有檔案，接著報找不到 `src/index.html.j2`。已修正測試副本的 file／asset
UUID 命名空間，並以新 staging scheme 避開舊失敗快取；沒有清空資料庫掩蓋問題。

工具 381 項、英文 10 項、中文 lifecycle 9 項測試通過（共 400 項）；這個數字
不包含、也不能取代上述成品驗收。不可覆寫、dirty lock、空白翻譯、套件 hash
不符及未通過驗收的封存拒絕機制都有測試。完整分支政策見
[版本管理](version-management.md)。

## 尚未完成，以及下一步

1. **Markdown 管線式表格仍不支援。** 實際 DSW 4.30 的 `render_markdown`
   只啟用 DSW 自有 extension，沒有 tables extension；表格會變成一般文字，
   Word 也沒有對應的可編輯表格。保留失敗案例，`pilot-report.passed=false`，
   候選封存必須拒絕。若要支援，應評估 worker 的 Markdown 設定／升級，不在
   Jinja 手刻另一個 Markdown parser，也不交由 LLM 掩蓋。
2. **三題仍非全分支驗收。** 測試主線包含參考資料重用；未窮盡儀器、非參考資料、
   所有條件組合、矛盾或不可達回覆。其餘 12 題也仍有舊的漏填與推論問題。
   例如樣張前置頁的經費未填，仍沿用「尚未申請」的舊預設；Q12 也仍可能把
   未填發布資料呈現為沒有資料。英文部分既有冗句仍須重寫，不能把本輪視为
   全文文體完成。
3. **Q5 的地點／頻率尚未完整映射。** 提示是本切片的映射缺口，不證明整個 KM
   沒有問。下一輪先做全 KM × SE 要求對照，再決定是否加臺灣版問題。
4. **文體與成品還需領域使用者驗收。** 自由文字不由 DT 自動翻譯；本輪使用人工
   編寫的對應英中回答與中文 KM。仍需用去識別化的代表性真實案例，以及實際
   使用的 Microsoft Word 環境檢查，不能只看合成案例。

建議先決定是否將 worker 表格能力納入修改範圍，再依這套切片方式逐題擴充；
目前沒有理由改走 runtime LLM workaround。保留兩個 repo 的分工與精確版本引用，
比立即維護兩套獨立 Jinja 更容易保持英中事實一致。

本輪 GitHub 交付使用 `experiment/completeness-contract`、
`feat/custom-template-pipeline`、`experiment/bilingual-pilot`，不合併主線、不建立
正式 release。英文分支後續另有 CI cache 路徑修正，不改本輪鎖定的模板來源
`93fc4ff`；如需重建，仍須 checkout manifest／pipeline.yml 指定的 commit。
