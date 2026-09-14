# 0.3.12：Q11 資料脈絡與保存敘述連讀

2026-09-14。本文件另封存於 `reviews/2026-09-14-preservation-context/README.md`；
下列相對樣張連結以封存目錄為準。所有填答均為既有合成案例；本輪是小範圍
閱讀結構實驗，不是正式發布、完整 Science Europe 覆蓋或 Microsoft Word 驗收。

## 先看前後對照

- 完整中文：[新版 PDF](tables/preservation-complete-chinese.pdf)、
  [Word](tables/preservation-complete-chinese.docx)、
  [Word 預覽](tables/word-preview/preservation-complete-chinese.pdf)。
  Q11 在 PDF 第 5–6 頁、Word 第 5–6 頁。
- 同填答 0.3.11：[舊 PDF](prior-tables/preservation-complete-chinese.pdf)、
  [舊 Word 預覽](prior-tables/word-preview/preservation-complete-chinese.pdf)。
- 漏填中文：[PDF](tables/preservation-partial-chinese.pdf)、
  [Word](tables/preservation-partial-chinese.docx)。第 6 頁保留冷儲存相關缺答。
- 英文：[完整 PDF](tables/preservation-complete-english.pdf)、
  [Word](tables/preservation-complete-english.docx)。PDF 第 6 頁可見合併後的段落。
- 原版 worker：[中文 PDF](stock/preservation-complete-chinese.pdf)、
  [Word](stock/preservation-complete-chinese.docx)。它仍無法正確解析 Markdown 表格。

`stock/` 與 `tables/` 使用完全相同的 0.3.12 ZIP，只有隔離測試 worker 不同。
`prior-stock/` 與 `prior-tables/` 是本輪重新產生的 0.3.11 同填答對照，不挪用
不同版本或不同案例冒充基準。四組原始建置均保留 HTML、PDF、DOCX、fixture
校驗碼與 Word 預覽。Git 封存收錄 PDF／DOCX、其 fixture 紀錄與預覽；含約
16 MB 嵌入字型的每份原生 HTML 留在文末所列本機建置目錄，報告保留完整
HTML 校驗碼，避免把重複字型大量存入 repo。沒有登入或更動線上 DSW。

## 改了什麼，沒有改什麼

原本 Q11 在資料描述後，將「資料處理階段／相關論文」與「發布／保存安排」
分置兩個 `dataset-policy`，即使都是短句也會斷成兩段。
現在由同一個容器承接連續的模板固定段落，沿用既有 PDF CSS 與 Word Lua
的合併規則。沒有新增全域刪換行或壓縮作者文字的處理。

例如「此資料集包含中間處理資料。」與「此資料集將不公開發布。」現在
可以接在同一段。以下邊界仍保留：

- 使用者資料描述中的兩個原始段落，不合併、不摘要。
- 自訂不發布原因中的原文段落與清單，不改寫。
- 未填提示獨立顯示；不把缺答推成否定或肯定。
- 各資料集、儲存庫聯絡內容、計畫層級冷儲存安排，仍各自歸屬原位置。

英文與中文的所有句子、標點、欄位值、事實順序、正式十五題標題均未變。
716 個翻譯單位完全沿用，空白 0；仍從改過的英文經既有翻譯管線產生中文，
沒有直接修改生成後的中文 Jinja。這輪也沒有宣稱已重寫或改善全部中文語氣。

## 測量與檢查

- 英文 102 項單元測試及 TDK verify、中文 79 項單元測試通過。
- 重跑六類雙語探針：格式 76、共享 52、保存 122、回答狀態 110、管道 26、
  聯絡引用 30 組。保存探針另檢查同 122 組輸出的容器結構，並完成 776 次
  已審閱固定句比對。這些不是額外的實際 DSW 文件。
- translation／structure audit 均為空；33 個 Jinja 的靜態 binding 稽核
  無未定義 UUID 名稱或不存在 entity。既有 fixture、KM 與 UUID 綁定未修改。
- 每個版本／worker 各兩案例 × 二語言 × 三格式，共 48 份實際 HTML／PDF／DOCX，
  另有 16 份 LibreOffice Word 預覽；其中新版為 24 份實際產檔與 8 份預覽。
- 新版兩個 worker 的 context、preservation、sharing、polish、format、reading、
  quality 七類指定檢查均通過。原版 worker 仍各有 8 筆 Q1 表格阻擋，不可發布。
- 新舊版各 worker 比較 60 題，共 120 題：全文、事實、狀態、資料集歸屬、
  原文 HTML 與連結都不變，沒有將 Q11 整題排除。其他十四題 HTML 也須相同。
- 原生 Word 從第一題起逐段核對文字、樣式、keep 屬性。只允許新版固定敘述
  對應的完整相鄰舊段落合併，其餘段落與所有表格內容／段落樣式必須不變。
  每份新版剛好少兩段：兩個資料集各合併一次；不是少掉兩份回答。
- 完整案例 Q11 保留 5 個作者段落、18 個 fact 標記；漏填案例保留 3 個作者
  段落、16 個 fact 標記。既有 Q11 句號單獨成行、文字越界檢查均通過。
- 新版四組跨 worker 對照通過，套件及 fixture checksum 完全一致。

頁數只作觀察，不作唯一品質指標：

| 修補表格 worker | PDF 舊→新 | Word 預覽舊→新 |
| --- | --- | --- |
| 完整中文 | 7→7 | 8→7 |
| 漏填中文 | 7→7 | 7→7 |
| 完整英文 | 8→8 | 7→7 |
| 漏填英文 | 8→8 | 7→7 |

原版 worker 四組頁數均未變：英文 PDF 8／Word 7、中文 PDF 7／Word 7。
不同 renderer 的表格與段落位置會影響後續分頁，不能將 8→7 概括為所有成品。
沒有縮小字級或更動行距；來源 delta 確認英中生成 `src` 只有 Q11 和資料脈絡
partial 兩個檔案改變，CSS、Lua、Word reference 與其他來源逐位元相同。

人工查看修補版完整中文 PDF 第 5 頁的新舊對照、Word 預覽第 5 頁的新舊對照
及新版第 6 頁、漏填中文 PDF 第 6 頁、完整英文 PDF 第 6 頁。
抽查頁面未見文字重疊或裁切；原文分段、清單與獨立缺答仍可辨識。
長論文網址仍插在連續敘述中，中文 PDF 第 5 頁還有偏短的尾行，這是待處理
問題，不以「沒有句號單獨成行」宣稱文風與排版已完成。

## 可重建版本與下一步

- 英中版本：0.3.12；工作分支：`feat/preservation-context-flow`，承接 0.3.11。
- 英文：`4aeeb2a9a35efe33d4b935f5b843716a74b3abdb`。
- 產檔中文 checkpoint：`e48e8aaa2576bc7bc257db4029c98ecc2eff37f3`。
- 工具：`25e339fbdfb1d20796471055790aad6a4226b6ed`，未修改。
- 官方基底仍為 1.30.1／`22d60aae4b63ee677477ac0c73097807284aaf9f`，沒有提高。
- 英文 ZIP：`9a898003b2ce92078dc9fe30135e863c4d01050b801b9f18863a392d5b7ad857`。
- 中文 ZIP：`478078bdd1857e65098819a82c706e32262f533271ed932477c94e3b9e9e3f4c`。
- 原版產檔：`outputs/build-o4q3lz7t`；修補版：`outputs/runtime-tables-zxq9wm21`。
- 舊版對照：`outputs/build-wp8awmsk`／`outputs/runtime-tables-yo2iscg4`。

導覽／封存提交與套件來源分開記錄；乾淨重建須產生相同 ZIP。封存工具拒絕
覆寫、過期報告、不同套件或 fixture 的比較，以及將原版表格失敗冒充通過。
升級時要一起審查 Q11 和此 partial，不能只看 Git 是否衝突。分支不是可安裝
版本：正式版本仍需固定 commit、不可覆寫套件及目標 renderer 驗收。

下一步優先實驗論文／長網址的呈現：保留原值與資料集對應，再比較獨立參考列
能否改善閱讀，不能直接截短或刪掉資訊。之後才對模板固定語句做更自然的
中文連接，不碰作者原文。冷儲存短清單密度、整份文件審閱、原版表格支援與
實際 Microsoft Word 分頁仍未完成。上輪聯絡引用與 60 段壓力案例本輪只重跑
離線探針，未重新產生其全部文件；本輪並非全案例回歸驗收。

未合併 main、未建立正式 tag／release、未部署。測試後已恢復原版 worker，
並停止四個本機容器，保留既有資料卷與歷次樣張。
