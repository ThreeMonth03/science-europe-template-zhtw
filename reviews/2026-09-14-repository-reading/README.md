# 0.3.10：儲存庫管道對照與短清單分頁

2026-09-14。本文件另封存為 `reviews/2026-09-14-repository-reading/README.md`；
下列樣張連結以封存目錄為準。這是合成回答、本機 DSW 的有限驗證，不是正式
發布、完整 Science Europe 覆蓋或 Microsoft Word 驗收。

## 樣張

- 三管道及不同維運狀態：[中文 PDF](tables/support-mixed-chinese.pdf)、
  [Word](tables/support-mixed-chinese.docx)、[Word 預覽](tables/word-preview/support-mixed-chinese.pdf)、
  [英文 Word](tables/support-mixed-english.docx)。
- 中間管道缺答：[中文 PDF](tables/repository-gap-chinese.pdf)、
  [Word](tables/repository-gap-chinese.docx)、[Word 預覽](tables/word-preview/repository-gap-chinese.pdf)。
- 60 段自訂說明：[中文 Word](tables/repository-long-chinese.docx)、
  [Word 預覽](tables/word-preview/repository-long-chinese.pdf)。這是壓力測試，不是理想 DMP 範文。
- 空白問卷：[Word 預覽](stock/word-preview/empty-chinese.pdf)。

`tables/` 使用先前隔離的表格修補 worker；`stock/` 使用原版 worker。
兩者使用完全相同的模板 ZIP。修補 worker 未部署線上，部署與回退責任仍待驗收。

## 本輪修正

Q11 多個儲存庫現在使用行內的「資料提供管道 1／2／3」標籤，對應 Q10、Q13
原始清單順序。單一管道不加多餘編號；中間管道未選儲存庫時，仍保留該列與
原編號，顯示「尚未說明此管道將使用哪個資料儲存庫」。不支援的已選類型則
標示需核對，不冒充未填。父題改成不發布時，不會讀出殘留子答案。

引言改為「各資料提供管道的保存位置」，不再預設每個管道都已說明位置。
既有長期維運的肯定／否定／缺答及服務層級保留，不把否定改寫成「尚未」，
也不從肯定答案推導出具體維護期限或經費來源。

短清單同頁規則只適用於最多三項、清單正文不超過 900 個正規化字元、僅含
行內結構的區塊；自訂聯繫說明、段落、表格等不會得到此提示。這是內容邊界，
不是任何字型／頁面尺寸都適用的高度保證。PDF 保留引言與短清單同頁，沒有
把整個資料集或 Q11 鎖成不可分頁區塊。

Word 另以實際 Pandoc AST 與 Unicode 字元數核對邊界，使用兩個專屬樣式。
各短項目內部不拆行跨頁；非最後一項與下一項相連，最後一項明確停止連鎖。
長清單會移除 Q11 外層清單可能繼承的一般短清單連鎖，原作者分段保持獨立。
既有字級、行距、其他段落樣式及原始 reference.docx 二進位檔未修改。

## 中英強調格式的實際修正

初版 `outputs/build-arcsndvz`／`outputs/runtime-tables-kyd_rlsg` 的文字與編號
雖正確，中文管道標籤卻失去英文的粗體。人工檢視才發現此差異；原有結構
稽核把 `strong` 視為裝飾標記，因此稽核通過不等於強調格式一致。
該初版已記錄拒收，不列入本輪通過樣張。

在此翻譯單位直接補 `<strong>` 的試驗又未通過結構檢查，未採用，也沒有
放寬稽核。最終改由英文維護的共用 CSS 與 Word Lua 對 `repository-label`
套用粗體，翻譯只處理文字與數字位置。新增檢查核對生成樣式規則及原生 DOCX
粗體文字 run，並人工查看中文 PDF／Word，確認標籤沒有再失去強調。
工具仍鎖定既有版本，沒有修改轉換工具或使用 LLM 摘要／JSON workaround。

## 驗證範圍

- 英文 92 項測試與 TDK verify、中文 67 項測試通過。
- 714 個翻譯單位，空白 0，translation／structure audit 無錯誤。
- 新增 26 組雙語管道／缺答／分頁提示檢查；另通過回答狀態 110 組、保存
  122 組／776 次固定句比對、共享 52 組、格式 76 組離線檢查。這些不混算為
  實際 DSW 產檔。
- 英中全部 fixture 通過本機編譯 KM 的路徑驗證；33 個 Jinja 的靜態 binding
  檢查無未定義變數或不存在 entity。沒有新增 KM 題目。
- 本輪封存的原版輸出：四案例 × 二語言 × 三格式，24 份 HTML／PDF／DOCX。
  指定語意檢查通過，仍有 12 筆既知 Markdown 表格阻擋，整體 acceptance false。
- 本輪封存的修補版輸出：三案例 × 二語言 × 三格式，18 份產檔；指定檔案與
  語意檢查通過。仍為 release acceptance false 的隔離 runtime 實驗。
- 全部十四組案例／語言有 Word 預覽，通過 preservation、sharing、polish、
  format、reading、quality、repository 七類指定成品檢查。支援與缺答案例的
  Q11 短清單在 DSW PDF、Word 預覽各自同頁；原生 DOCX 的段落與粗體規則符合預期。
- 長回答在 Q11 保留 60 個原始段落及大小寫敏感檔名，每個檔名在 Q11 出現
  一次；Q10 仍輸出同一答案，因此每個檔名在整份文件共出現兩次。沒有合併作者段落，
  亦沒有把 60 段綁成一個長鏈。原版中文 Q11 長回答跨 PDF／Word 第 7–9 頁。
- 與 0.3.9 同案例、同 fixture、同 runtime 的比較：原版 60 題、修補版 30 題，
  共 90 題；HTML 僅允許預期的 Q11 引言、標籤、容器修改。作者原文保留，
  原生 Word 的 Q11 以外段落／樣式與全部表格儲存格文字不變。新增的缺答／
  長回答案例沒有歷史同案例，不列入這項比較。
- 相同 ZIP 的三個共同案例／二語言，共六組跨 worker 對照通過。
- `repository-source-delta.json` 核對英中套件全部 `src` 檔案，只有 Q11、
  layout.css、Word Lua、生成的 reference 改變。reference ZIP 只有 styles.xml
  改變；移除兩個新增專屬樣式後，其餘樣式與前版相同。

人工查看修正後原版中文三管道 PDF／Word 第 6 頁、缺答 Word 第 6 頁、長回答
Word 第 8 頁及英文三管道 Word 第 5 頁；另查看修補版中文三管道 PDF／Word
第 6 頁、缺答 Word 第 6 頁、長回答 Word 第 8 頁。短清單的標籤粗體與缺答列
可辨識；長回答沒有文字重疊或裁切，但這些刻意重複的測試段落不是理想文風。
指定檢查包含頁面邊界、Q11 純標點行及同一預覽文字區塊內的重疊檢查，不能
擴大解讀成每一頁的美感、所有跨區塊碰撞或目標 Microsoft Word 皆已驗收。

## 版本與仍待處理事項

英中短期分支均為 `feat/repository-reading`，版本 0.3.10。英文來源
`709e9e2569b9427954467994cbfc1b5de3b5eed5`，中文產檔 checkpoint
`9c00fbe8890fa0fdd73751dde9103a465f8b1d6d`；工具仍為
`25e339fbdfb1d20796471055790aad6a4226b6ed`，官方基底仍為 1.30.1。
英文邏輯、共用排版與中文文字分開管理；升級仍須核對這些管道與分頁情境，
不能只以 Git 無衝突判定相容。

英文 ZIP：`57a449e2a182768617863abdd99db1897b82a973c1caf0964fdfcdcd3368a172`。
中文 ZIP：`8b6b8cca6dae644a3210a3941a8a131851b669ae8a45888de101f3cb5ddb7ee5`。
原版 `outputs/build-_w4x4q7f`，修補版 `outputs/runtime-tables-nxzkr_qn`。
乾淨重建 `outputs/build-8ujqah2s` 的套件與實際產檔逐位元相同。
封存器核對來源、檢查器、fixture、報告與產物 hash，保留已知失敗，採 25 MB
上限，不複製巨大內嵌字型 HTML、不覆寫舊審閱。

英文 [CI 34816312146](https://github.com/ThreeMonth03/science-europe-template/actions/runs/34816312146)
及中文產檔來源 [CI 34816435508](https://github.com/ThreeMonth03/science-europe-template-zhtw/actions/runs/34816435508)
通過；最終封存提交另走分支 CI。未合併主線、未建立 tag／release、未部署
線上 DSW，亦未讀取線上專案或 keyring。

產檔後已將本機 worker 還原為原版映像（SHA-256
`5e5c5e1e436feb49fc4cbcd62c2e0ab2785db2141b0fe40d2926906bcfeaebfc`），
並停止本機四個實驗容器；未刪除容器、資料卷、原始樣張或舊封存。

下一輪優先釐清 Q10／Q11 的內容歸屬，處理同一自訂說明重複輸出的負擔：
完整說明應有明確位置，其他題目可引用，而不是無依據刪文或自動摘要。
短清單移到下一頁所留下的空間、具名儲存庫資訊、原版表格缺陷、維運安排
與費用一致性仍有待改善；還需目標 Microsoft Word、字型替代與去識別真實
專案驗收。這輪不宣稱整份 DMP 已經完整或理想。
