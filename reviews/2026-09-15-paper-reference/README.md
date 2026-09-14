# 0.3.13：論文參考列與長網址完整性

2026-09-15。本文件另封存於 `reviews/2026-09-15-paper-reference/README.md`；
下列相對連結以封存目錄為準。這是合成案例的局部實驗，不是正式發布或完整
Science Europe／Microsoft Word 驗收。

## 樣張

- 一般中文：[PDF](tables/preservation-complete-chinese.pdf)、
  [Word](tables/preservation-complete-chinese.docx)、
  [Word 預覽](tables/word-preview/preservation-complete-chinese.pdf)。Q11 從第 5 頁開始。
- 長網址／文獻文字／空白欄位：[中文 PDF](tables/paper-references-chinese.pdf)、
  [Word](tables/paper-references-chinese.docx)、
  [Word 預覽](tables/word-preview/paper-references-chinese.pdf)。PDF 第 5–6 頁、Word 第 6 頁可見參考列。
- 舊版長網址失敗對照：[中文 PDF](prior-tables/paper-references-chinese.pdf)。
- 英文：[長網址 PDF](tables/paper-references-english.pdf)、[Word](tables/paper-references-english.docx)。
- 原版 worker：[一般中文 PDF](stock/preservation-complete-chinese.pdf)、
  [長網址 PDF](stock/paper-references-chinese.pdf)、[Word](stock/paper-references-chinese.docx)。

`tables/` 是既有隔離表格修補 worker，`stock/` 是原版；新版兩者使用相同 ZIP。
`prior-*` 是以同一批填答重新產生的 0.3.12 對照。原版的 Q1 Markdown 表格仍
未正常解析，不因 Q11 修好就取得正式發布資格。

## 內容與排版調整

Q11 的「資料處理階段／發布／保存安排」維持連讀；相關論文改在保存敘述後、
儲存庫列表前另成一列。標籤與值仍在同一段，沒有額外標題或巢狀清單。
參考資料仍屬於原資料集，不因同名資料集而重新分配或去重。

論文欄位可能是網址、DOI 或一般文獻文字。原值完整保留、作純文字跳脫，
不套 Markdown、不補寫、不摘錄。只移除模板自動附加的結尾句號；使用者
自己輸入的句點、大小寫、百分比編碼、查詢參數與片段識別碼均保留。

只有整個值符合保守 HTTP(S) 條件時才建立連結：小寫 `http://`／`https://`、
無空白、有 authority，且不含登入資訊、引號、角括號或反斜線。這不是通用
網址有效性驗證器；不會從文獻敘述中自行抽網址，也不自動修補格式。
其他值照原文顯示。欄位空白仍不產生空參考列，資料階段與其他答案照常保留；
這輪沒有新增「所有未填論文均須提示」的完整性契約。

論文依自己的資料階段題目判斷是否有效，不受獨立的「資料集是否發布」決定
控制。改答其他階段後的殘留論文不顯示；不發布資料集仍可有已發表的研究論文。

新長網址有 20 段連續的 `LongReference2027` 與 query／fragment。舊版英中 PDF
均把部分網址畫到頁面右邊界以外，文字擷取也無法還原完整原值。新版參考列
使用專屬換行 CSS，完整值可跨行／跨頁；原生 Word 原先並未出現同樣的截斷。
沒有插入零寬字元、改 href、縮寫網址或縮小字級。極長網址仍佔多行，這是
保留完整原值的壓力案例，不是建議使用者撰寫的理想文獻格式。

## 翻譯結構與預覽查核

第一個原型把標籤 span 與條件式連結放在同一翻譯區塊；套用已審閱中文標籤
後，生成 HTML 遺失 span。`outputs/build-p3k_9q9m/structure-audit.json` 記錄
此失敗，該原型未納入接受樣張。修正是在英文 partial 先單獨擷取標籤，再
組成參考列；沒有直接修生成後的中文，也沒有放寬 structure audit。

Word 原生 hyperlink 的可見文字與 relationship target 均須等於原值。DSW PDF
亦核對實際 URI 與各行連結文字。LibreOffice 轉成 PDF 後，連結註記範圍可能
碰到旁邊中文標籤，`pdftohtml` 因而把「文：」一併列為連結文字。預覽檢查
只容許已知標籤的精確尾綴，原值與 URI 仍不得更動；任意前綴、缺字、改大小寫
或多出句號均拒絕。此容許不套用於原生 Word 或 DSW PDF。

## 驗證範圍與限制

- 英文 107 項測試與 TDK verify、中文 85 項測試通過。
- 716 個翻譯單位，空白 0；translation／structure audit 均為空。
- 七類雙語探針：格式 76、共享 52、保存 122、回答狀態 110、管道 26、
  聯絡引用 30、論文參考 48 組；保存另有 776 次固定句比對。這些是離線分支
  檢查，不能混算成實際 DSW 文件。
- 新 fixture 經英中編譯 KM 的選項／路徑可達性驗證；34 個 Jinja 靜態 binding
  稽核無未定義 UUID 或不存在 entity。既有 fixture 與正式十五題標題未修改。
- 每個版本／worker 各兩案例 × 二語言 × 三格式，共 48 份 HTML／PDF／DOCX，
  另有 16 份 Word 預覽。新版兩個 worker 的 paper、preservation、sharing、
  polish、format、reading、quality 七類檢查通過；原版仍各有 8 筆既知表格阻擋。
- 同 fixture 新舊比較共 120 題。只允許論文節點移位、額外模板句號移除及新增
  合格網址連結；重建原位置後再核對整題文字、事實、狀態、資料集歸屬、原文
  區塊與連結。其餘十四題 HTML 不變，不將 Q11 整題排除。
- 原生 Word 從第一題起逐段比對文字、樣式、keep 屬性；只允許指定論文片段
  移成獨立段落，其他段落與所有表格儲存格不變。每個 worker 的四份新版文件
  共保留 6 個參考列、4 個 HTTP(S) 連結。一般文獻中的 `<review>` 保留為字面文字。
- 新版 PDF／Word 預覽均保留完整參考值與 URI，並檢查參考文字的頁面邊界。
  兩種 worker 四組同套件／同填答比較通過。這不等於 Microsoft Word 實機驗收。

頁數沒有全面下降：兩種 worker 的 PDF 頁數皆不變；原版 Word 預覽皆不變。
修補表格版的完整中文 Word 預覽由 7→8 頁，其餘 Word 預覽頁數不變。
獨立參考列改善正文閱讀，但後續分頁會移動；這一頁的代價仍需整份文件的
段落與表格分頁調整。不能只因局部檢查通過就稱整體版面已完成。

人工查看新版一般中文 PDF／Word 第 5 頁、長網址中文 PDF 第 5–6 頁、Word
第 5–6 頁，以及舊版原版 worker 長網址 PDF 第 5 頁。新版抽查頁面未見文字
裁切；長網址跨頁可讀、原文清單與資料集對應保留。未逐頁驗收所有歷史案例。

## 版本與下一步

- 英中版本 0.3.13；工作分支 `feat/paper-reference`，承接 0.3.12。
- 英文 `7f43c9b2ba083dfeb75f0ee940b01f235f2d2aa1`。
- 產檔中文 checkpoint `3a1004b3ddef9ec7baebeb90e45dd04ef7947e77`；查核程式與封存
  提交另行記錄，報告以 checker／helper checksum 綁定。
- 工具 `25e339fbdfb1d20796471055790aad6a4226b6ed`，未修改。
- 官方基底仍為 1.30.1／`22d60aae4b63ee677477ac0c73097807284aaf9f`。
- 英文 ZIP `dc914149ba89270e0a12be84fe60cb60c63b0facc65657b97750dc95a3b0bcc0`。
- 中文 ZIP `0a0098beaffce60480b5df59932380291f838c0245efd53dfa7b7da3f0d78e9f`。
- 新原版／修補版：`outputs/build-jijf77dp`／`outputs/runtime-tables-4he_8ki7`。
- 舊原版／修補版：`outputs/build-_qwei9yh`／`outputs/runtime-tables-5o00h44a`。

Git 封存 PDF／DOCX、fixture 紀錄、預覽與報告；每份含約 16 MB 嵌入字型的
原生 HTML 留在上述本機目錄，完整校驗碼保留於報告。乾淨重建須產生相同 ZIP，
歷次封存不覆寫。來源差異限定 Q11、資料脈絡 partial、專屬 CSS 與新增論文
partial；Word Lua／reference 與其他來源不變。升級須一起審查這些檔案及翻譯
標籤邊界，Git 沒有衝突不等於成品相容。

下一步處理模板固定中文敘述的銜接與整份 Word 分頁，繼續保留作者原文。
本輪沒有實作全域網址重排、JSON／LLM 摘要或臺灣版新 KM。原版 Markdown 表格、
整份 DMP 與目標 Microsoft Word 驗收仍未完成。未合併、未發布正式 tag／release、
未部署；測試後恢復原版 worker 並停止四個本機容器，保留資料卷與歷次樣張。
