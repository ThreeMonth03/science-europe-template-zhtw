# 0.3.11：儲存庫聯繫回答歸屬與跨題引用

2026-09-14。本文件另封存於 `reviews/2026-09-14-repository-contact/README.md`；
下列樣張連結以封存目錄為準。所有回答均為合成測試資料，不是正式發布、
完整 Science Europe 覆蓋或目標 Microsoft Word 驗收。

## 先看樣張

- 段落／清單／表格／缺答：[中文 PDF](tables/contact-mixed-chinese.pdf)、
  [Word](tables/contact-mixed-chinese.docx)、[Word 預覽](tables/word-preview/contact-mixed-chinese.pdf)。
  中文 Word 第 5 頁是 Q10 引用，第 6 頁是 Q11 完整回答。
- 60 段長回答：[中文 PDF](tables/repository-long-chinese.pdf)、
  [Word](tables/repository-long-chinese.docx)、[Word 預覽](tables/word-preview/repository-long-chinese.pdf)。
  這是保留與跨頁壓力測試，重複句子不是理想文風。
- 英文對照：[PDF](tables/contact-mixed-english.pdf)、[Word](tables/contact-mixed-english.docx)。
- 原版 worker 對照：[中文 PDF](stock/contact-mixed-chinese.pdf)、[Word](stock/contact-mixed-chinese.docx)。

`tables/` 使用既有隔離表格修補 worker；`stock/` 使用原版 worker。兩者套件
ZIP 完全相同。原版仍無法正常解析 Markdown 表格，不能把修補版樣張當作
正式環境已解決表格問題。

## 內容歸屬與中文語意

這輪只處理「其他儲存庫聯繫安排」自由回答。Q11 保留原文全文，Q10 保留
儲存庫名稱、共享與授權條件，改以可點擊引用指向 Q11 同一資料集／管道。
其他固定聯繫狀態沒有在本輪全面去重，也沒有按相同文字合併不同欄位。

原英文把 Other 推論成「不直接聯繫儲存庫」，中文也出現相同過度推論。
現在使用中性引言「儲存庫聯繫的其他安排」；選了 Other 卻沒有內容時，
保留引用目標並明示「尚待補充」，不宣稱安排已經完成。

引用使用當份文件的資料集／管道位置組合，不依賴名稱唯一、不跳過中間缺答，
也不寫死頁碼。這不是跨問卷修改後仍不變的永久 ID。若未來題號或題目順序
改變，需同步審查引用文字、目標與原生輸出。父題改答後，殘留子答案不應外洩。

新案例刻意使用同名資料集，另在兩個不同欄位填入 `Same-contact-2027.csv`。
這兩份回答各保留一次；同一欄位不再於 Q10／Q11 各複製一次。作者段落、
清單、大小寫敏感檔名及表格內容保留，未使用 LLM 摘要或 JSON workaround。

## 分頁與檢查方法的修正

第一個原型 `outputs/build-2h_jpucq`／`outputs/runtime-tables-yl43muwx` 會讓
Q11 管道標籤留在上一頁。第二個原型 `outputs/runtime-tables-qb0jiexo` 雖加上
外層引言標記，Pandoc 卻將其解析為 Plain，原生 Word 仍使用 Compact 樣式。
這些原型已記錄拒收，沒有納入本輪通過樣張。

最終在 Other 分支將管道標籤與儲存庫名稱明確包成引言段落，沿用既有
`answer-lead`／`Pilot Lead` 規則。標籤、引言與回答開頭相連，長回答仍可
跨頁。沒有修改 CSS、Lua、reference.docx、字級或行距。

混合內容也揭露舊檢查把巢狀清單視為一段連續文字，會因 PDF 的項目符號
誤報漏文。現改為逐段核對，Word 文字依原生 XML 順序包含表格儲存格；
另比較聯繫表格的完整列／欄內容，不能只找到一個檔名就算通過。
跨 worker 對照只允許指定 Q11 聯繫表格的 pipe 語法轉換，逐格驗證內容，
其餘 Q11 文字仍須相同。

## 驗證範圍

- 英文 97 項測試與 TDK verify、中文 74 項測試通過。
- 716 個翻譯單位、空白 0；translation／structure audit 無錯誤。
- 新增 30 組雙語引用／缺答／殘留答案檢查，並重跑管道 26 組、回答狀態
  110 組、保存 122 組／776 次固定句比對、共享 52 組、格式 76 組。
  這些離線檢查不混算為實際 DSW 產檔。
- 新 fixture 通過英中編譯 KM 路徑驗證；33 個 Jinja 的靜態 binding 稽核
  無未定義 UUID 名稱或不存在 entity。沒有新增 KM 題目、改官方題目或提高官方基底。
- 最終原版及修補版各三案例 × 二語言 × 三格式，各 18 份 HTML／PDF／DOCX；
  十二組案例／語言另有 Word 預覽。指定 preservation、sharing、polish、format、
  reading、quality、contact 七類檢查通過；不代表整份文件已完成視覺驗收。
- 原版報告保留 12 筆既知 Q1 表格阻擋，Q11 新增的測試表格亦維持未解析狀態。
  修補版須有真正的 HTML／DOCX 表格且儲存格相符；兩種 runtime 均未取得正式發布驗收。
- Q10 引用與 Q11 目標一對一；PDF 目的地及實際連結頁面相符，原生 Word
  超連結與書籤配對。未把 LibreOffice 的預覽當作 Microsoft Word 實機驗收。
- 60 段長回答在 HTML／PDF／Word 均完整保留一次，仍正常跨頁。與 0.3.10
  同 fixture、同修補 worker 比較，英文 PDF 15→12 頁、Word 預覽 13→11 頁；
  中文 PDF 11→10 頁、Word 預覽 12→10 頁。頁數減少來自移除重複全文，不是縮小字體。
- 與前版共同案例比較，原版 60 題、修補版 60 題，共 120 題。檢查以 Q11
  保留原文重建前版的兩份全文，再核對完整問卷結構，不將整題排除比對。
  Q10／Q11 以外的原生 Word 段落／樣式及所有既有表格儲存格亦須不變。
  新 `contact-mixed` 案例沒有歷史同案例，不列入這項比較。
- 相同 ZIP 的六組跨 worker 對照保留 fixture／套件／成品校驗碼。生成後的
  英中 `src` 只有 Q10、Q11 改變，其他檔案與前版逐位元相同。

人工查看修補版中文混合 PDF 第 6 頁、Word 預覽第 5–6 頁、長回答 Word
第 7 頁，以及英文混合 PDF 第 7 頁。標籤與缺答提示可辨識、表格可讀，
抽查頁面未見文字重疊或裁切；原有短句密度、尾行與跨題整體閱讀仍待整理。
另查看原版中文混合 PDF／Word 第 6 頁；標籤與回答仍可讀，但表格清楚呈現
為 pipe 文字，保留為已知失敗對照，不視為排版完成。

## 版本與界線

兩個 repo 的工作分支均為 `feat/repository-contact-reference`，版本 0.3.11。
英文來源 `8c089c126475b60943439ef18d63ea66b0384a23`，中文產檔 checkpoint
`fa0c67b75f33122ae85c79b42167e4f982c49c7d`；工具仍鎖定
`25e339fbdfb1d20796471055790aad6a4226b6ed`，官方基底仍為 1.30.1。
原版 `outputs/build-l55zuw_y`，修補版 `outputs/runtime-tables-h37yni2h`，
乾淨重建 `outputs/build-7w8yg8h0` 的 ZIP 與實際產檔所用套件逐位元相同。

英文 ZIP：`f5d1ec91d387dea8e94f1418e89cf4206391d093bb38d9de2c2009aee53fb820`。
中文 ZIP：`567fd0875f4ba47d5fb47891c694c0a79dec3fb5c3f208a418fc91b9d67c5f1e`。
封存器核對來源、檢查器、fixture、報告及成品 hash，保留已知失敗，不覆寫舊封存。

英文 [CI 34819929502](https://github.com/ThreeMonth03/science-europe-template/actions/runs/34819929502)
與中文來源 [CI 34819978587](https://github.com/ThreeMonth03/science-europe-template-zhtw/actions/runs/34819978587)
通過，最終封存提交另走分支 CI。未合併主線、建立 tag／release 或部署線上 DSW，
沒有讀取 keyring 或線上專案。

產檔後本機 worker 已還原為原版映像（SHA-256
`5e5c5e1e436feb49fc4cbcd62c2e0ab2785db2141b0fe40d2926906bcfeaebfc`），
四個實驗容器均已停止；未刪除容器、資料卷、原型產物或舊封存。

下一輪優先整理 Q11 資料集脈絡與保存政策的短句密度。原版 worker 表格缺陷、
完整 Science Europe 回答覆蓋、實際 Microsoft Word／字型替代，以及去識別
真實專案仍需驗收。本輪不是整份 DMP 已經理想的結論。
