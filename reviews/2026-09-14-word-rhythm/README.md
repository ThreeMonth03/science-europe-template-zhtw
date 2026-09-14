# 0.3.8：Word 間距與保存政策對照

2026-09-14。本文件另封存為 `reviews/2026-09-14-word-rhythm/README.md`；
下列樣張連結以封存目錄為準。這是本機 DSW、合成回答的有限實驗，並非正式
發布或 Microsoft Word 驗收。已知內容缺陷仍存在，不能把樣式改善當成 DMP
已完整、正確的證明。

## 先看 Word 與預覽

表格修補 worker 的實際新版產檔：

- 完整保存安排：[中文 Word](tables/preservation-complete-chinese.docx)、[Word 預覽](tables/word-preview/preservation-complete-chinese.pdf)、[DSW PDF](tables/preservation-complete-chinese.pdf)。
- 部分缺答：[中文 Word](tables/preservation-partial-chinese.docx)、[Word 預覽](tables/word-preview/preservation-partial-chinese.pdf)。
- 自訂保存期限：[中文 Word](tables/preservation-custom-chinese.docx)、[Word 預覽](tables/word-preview/preservation-custom-chinese.pdf)。
- 一般案例：[中文 Word](tables/structured-chinese.docx)、[英文 Word](tables/structured-english.docx)。
- 80 段長回答：[中文 Word](tables/narrative-long-chinese.docx)、[Word 預覽](tables/word-preview/narrative-long-chinese.pdf)。
- 48 列長表格：[中文 Word](tables/table-long-chinese.docx)、[Word 預覽](tables/word-preview/table-long-chinese.pdf)。

原版 worker 對照：[完整中文 Word 預覽](stock/word-preview/preservation-complete-chinese.pdf)、
[空白中文 Word 預覽](stock/word-preview/empty-chinese.pdf)。原版仍有 Markdown
表格問題，不是推薦的正式輸出。

## 實際改動

本輪只改英文 repo 的 Word 樣式準備步驟；709 個翻譯單位沿用，沒有修 Jinja、
中文文字、PDF CSS 或 Word Lua。原始 reference.docx 二進位檔也保留不改，
仍由建置時的 `prepare_layout.py` 套用樣式。

| 樣式 | 原本 | 新版 |
| --- | --- | --- |
| 正文／自由回答 | 1.4 倍行距，段後 4 pt | 1.2 倍行距，段後仍 4 pt |
| Compact 清單／表格文字 | 1.4 倍行距，段後 4 pt | 1.2 倍行距，段後 2 pt |
| 題目標題 Heading 3 | 段前 12／段後 6 pt | 段前 12／段後 4 pt |
| 小節／資料集標題 Heading 4–5 | 段前 12／段後 6 pt | 段前 8／段後 3 pt |

正文字級維持 10.5 pt；頁面、邊界、標題字級、寡行控制、短區塊相鄰提示與
作者分段不變。採相對行距，不使用固定行高裁切混合文字，也不靠縮小字級減頁。

先在上一版的原版-worker 完整中文 DOCX 做 A／B：
[只改行距](rehearsal/line-only.pdf) 為 8 頁，[完整間距方案](rehearsal/rhythm.pdf)
為 7 頁，原本是 9 頁。兩份試改 DOCX 除 `word/styles.xml` 外的 ZIP 成員
逐位元相同。這是樣式隔離演練，不計入實際 DSW 產檔數量。

接回建置後，表格修補 worker 的中文 Word 預覽頁數如下：

| 同一案例 | 0.3.7 | 0.3.8 |
| --- | ---: | ---: |
| 完整保存安排 | 9 | 8 |
| 部分缺答 | 8 | 7 |
| 自訂保存期限 | 9 | 8 |
| 一般案例 | 7 | 6 |

原版-worker 完整案例為 9 → 7 頁，一般案例為 7 → 6 頁。兩個 runtime 的
分頁不能混算，真正的表格結構會影響版面。新版長回答與長表格 Word 預覽
分別為 9、7 頁；沒有拿不同內容版本的歷史案例作減頁比較。

## 內容對照的結論

詳見 [保存政策逐項對照與台灣版 KM 待審草案](selection-policy-review.md)。
本機編譯的英中 Common KM 2.7.0 各有 592 個可到達問題；以題目、guidance
及選項標籤篩出 47 個候選，再審查特定路徑。`selection-scope-report.json`
保留英中候選題目、選項、路徑、目前靜態引用與來源 hash。關鍵詞篩選不是
全 KM 語意缺欄位的證明，也不是 Science Europe 覆蓋率。

主要界線：不公開發布不等於不保存，續存依據不等於初次保存選擇；「其他研究
產出」的保存選擇不能冒充資料集選擇；工作空間下的原始資料備存決定也有自己的
適用範圍。這輪沒有新增 KM 題目、沒有虛構保存理由，亦未移除 Q11 的需核對提示。

草案列出資料集／版本引用、保存或處置決定、理由、適用要求、時間起算、保存
地點及責任等欄位。採用前仍須確認 KM 相容性與既有專案遷移，不要求使用者
現在重填，也不把草案當成正式 Science Europe 官方問題。

## 驗證範圍

- 英文 81 項測試與 TDK verify 通過；中文 58 項測試通過。
- 709 個翻譯單位，空白 0，translation／structure audit 無錯誤；保存 122 組
  分支／語言檢查與 715 次固定句比對、共享 52、格式 76、蒐集 24、品質 512
  組離線檢查通過。這些不是 DSW 產檔數量。
- 原版 worker：三案例 × 二語言 × HTML／PDF／DOCX，共 18 份產檔；所選
  語意檢查通過，仍有 8 筆既知表格阻擋，整體 acceptance 為 false。
- 表格修補 worker：六案例 × 二語言 × 三格式，共 36 份產檔；所選語意及
  檔案檢查通過。它仍是隔離的 runtime 實驗，release acceptance 為 false。
- 原版六組、修補版十二組案例／語言均通過 preservation、sharing、polish、
  format、reading、quality 及 word-rhythm 七種指定輸出檢查。
- 與 0.3.7 同案例、同 fixture 的嚴格歷史比較：原版 90 題，修補版 120 題，
  共 210 題 HTML 結構與文字完全相同。Word 保留正文段落／樣式分界與所有表格
  儲存格文字；同一 runtime 的 PDF 全文（只正規化空白）與頁數不變。
- 新產的長回答／長表格不列入上述歷史比較，另做原生樣式、回答保留、頁面
  邊界與分頁檢查。80 段長回答逐段保留，48 列表格的中英 ROW 標記均完整。
- 所有十八份新版 DOCX 均產生 LibreOffice 預覽，並檢查同一文字區塊內的
  文字行無重疊。這不是跨區塊碰撞、字形裁切或全部頁面美感的完整檢查。
- 相同 ZIP 在兩種 worker 的共同兩案例／二語言，共四組跨 runtime 比較
  通過。其他四個修補版案例沒有本輪原版對照，不擴大宣稱。
- `style-source-delta.json` 對照英中套件 `src` 內所有檔案，唯一改變的來源
  檔是生成的 Word reference。版本 metadata 另改為 0.3.8；不是宣稱 ZIP 相同。

人工檢視原版完整中文／英文 Word 第 6 頁及空白中文第 2 頁；修補版缺答、
自訂期限 Word 第 6 頁，長回答第 6–7 頁，長表格第 3 頁。長回答仍獨立跨頁，
不是合成巨大段落。長表格在 Word 第 2–4 頁仍完整，但跨頁表頭下方留白與
小節跨頁的銜接仍有改善空間。

## 尚未修好、下一輪優先項目

1. 空白案例的 Q5 仍有「上述對應回答已說明儲存安排與備份需求」引言，與
   無回答的情況不相符。這是原有內容問題，本輪忠實比較到它仍存在，不能把
   內容不變當成內容正確；應改為依回答狀態選擇引言。
2. Q11 專用儲存庫的長期支援欄位目前只輸出肯定分支，否定／缺答仍需補強。
   保存政策對照亦列出維護安排、持續性費用和具名保存地點的後續驗證項目。
3. 原版 Markdown 表格缺陷尚未修復；修補 worker 的部署／回退責任未驗收。
4. Word 的部分短尾行、長表格跨頁留白與標題銜接仍待校整。目標 Microsoft
   Word、字型替代與去識別真實專案尚未驗收，不能用合成案例取代。

## 版本與可重建性

英中皆在短期 `feat/word-rhythm`，套件版本 0.3.8。英文來源
`b28d9370dcb1594afff09a56662668381f368cb7`，實際產檔中文 checkpoint
`5d617661f730e098bfe92f42b97313ec695b1db1`，工具仍鎖定
`25e339fbdfb1d20796471055790aad6a4226b6ed`。官方基底仍為 1.30.1，沒有提高。

英文 ZIP：`e6614325f64513b6ac01a276678f8bd17462421d1f8488fe32a695ce68519187`。
中文 ZIP：`3d3e0fd0eac797ffab80552cb325aaa76463a45f18a8357a356405adc5908d9e`。

原版 `outputs/build-84b60kcv`，修補版 `outputs/runtime-tables-1rge_cb7`；
檢查器提交 `9234fc71131659ad38f5674f3516525827c78119` 的乾淨重建
`outputs/build-27unurfn` 與實際產檔 ZIP 逐位元相同。
`rebuild-manifest.json`、各報告與 `checksums.json` 保留來源和產物驗證資訊。
封存前有 25 MB 大小門檻，不複製內嵌字型的巨大 HTML，不覆寫舊審閱。

英文 [CI 34810514955](https://github.com/ThreeMonth03/science-europe-template/actions/runs/34810514955)
及中文檢查器 [CI 34811239766](https://github.com/ThreeMonth03/science-europe-template-zhtw/actions/runs/34811239766)
通過；最終樣張封存提交另外走分支 CI。未合併主線、未建立 tag／release、
未部署線上 DSW，也未讀取 keyring／線上專案。本機 worker 已回復原版映像，
四個 pilot 容器已停止，資料卷保留。工具 MinIO 修復分支未在本輪合併。

Word 的建置樣式腳本已列入 upstream 升級的高風險審閱範圍，未來須重新
跑雙語成品、短／長回答、表格及缺答案例，而不是只解 Git 文字衝突。
