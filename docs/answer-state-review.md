# 0.3.9：缺答與否定回答不得變成錯誤承諾

2026-09-14。本文件另封存為 `reviews/2026-09-14-answer-states/README.md`；
下列樣張連結以封存目錄為準。這是本機 DSW、合成回答的有限實驗，不是正式
發布、完整 Science Europe 驗收或 Microsoft Word 驗收。

## 先看樣張

- 三個專用儲存庫，分別回答能維運／不能維運／留白：
  [中文 Word](tables/support-mixed-chinese.docx)、[Word 預覽](tables/word-preview/support-mixed-chinese.pdf)、
  [DSW PDF](tables/support-mixed-chinese.pdf)、[英文 Word](tables/support-mixed-english.docx)。
- 既有保存案例：[中文 Word](tables/preservation-complete-chinese.docx)、
  [Word 預覽](tables/word-preview/preservation-complete-chinese.pdf)、[DSW PDF](tables/preservation-complete-chinese.pdf)。
- 空白問卷的 Q5：[中文 Word](stock/empty-chinese.docx)、
  [Word 預覽](stock/word-preview/empty-chinese.pdf)、[DSW PDF](stock/empty-chinese.pdf)。

`tables/` 使用先前隔離的表格修補 worker；`stock/` 使用原版 worker。
兩者套件 ZIP 完全相同。修補 worker 並未部署線上，亦未通過部署／回退責任驗收。

## 修正內容與中文語氣

Q5 原先無論有沒有回答，都聲稱「上述對應回答已說明儲存安排與備份需求」。
現在統一改成：「本模板目前對應的欄位不足以確認以下執行細節：」。
採中性引言，是因為即使只回答一部分，也不能推論儲存安排和備份需求都已交代。
下方地點與排程的 `partial`／`unmapped` 狀態不變；這是模板欄位對應的限制，
不是憑空新增兩個使用者漏填欄位。

Q11 的專用儲存庫現在分別輸出：

| 問卷回答 | 中文輸出 | 語意標記 |
| --- | --- | --- |
| 是 | 我們能夠長期維運此資料儲存庫。 | complete |
| 否 | 我們無法長期維運此資料儲存庫。 | explicit-no |
| 未填 | 尚未說明能否長期維運此資料儲存庫。 | missing |

肯定句沿用已審閱譯文；否定不改寫成「尚未」，留白也不等於否定。三者皆不
代表已有具體期限、維護計畫或經費來源。依據是公開 Common KM 2.7.0 中
專用儲存庫的長期支援問題；英文與中文使用相同問題路徑及 Yes／No UUID。
沒有新增或遷移 KM，亦沒有把 Science Europe 問題標題換成自行編造的問題。

支援狀態隸屬於個別資料提供管道，僅在「將發布」且選「專用儲存庫」時顯示。
父題未答、改成不發布或其他儲存庫時，不會讀出殘留子答案。既有下載／搜尋／
進階處理服務回答獨立保留；新句子放在原清單段落，不逐句新增段落。

英文維護分支邏輯，中文由既有翻譯樹生成。709 → 711 個翻譯單位；此次
精確遷移造成 Q11 部分單位路徑更名，但原有譯文不因此重譯。空白翻譯 0，
translation／structure audit 均為空錯誤清單。没有執行期 LLM 或 JSON workaround。

## 驗證與界線

- 英文 86 項單元測試及 TDK verify、中文 62 項單元測試通過。
- 新增 110 組雙語分支檢查，包括 Q5 九種工作空間／封存組合，以及 Q11
  父題、儲存庫種類、肯定／否定／缺答／未知值與多管道檢查。這是 adapter
  檢查，不混算為實際 DSW 產檔。
- 保存 122 組／776 次固定句比對、共享 52 組、格式 76 組雙語離線檢查通過。
- 新增 `support-mixed` 合成案例，三個專用儲存庫使用不同支援狀態及服務層級；
  既有 fixture 未改。本機編譯英中 KM 的全部 fixture 路徑檢查無錯誤；
  33 個 Jinja 的靜態 UUID 檢查無未定義 binding 或不存在 entity。
- 原版：保存、空白、混合支援三案例 × 二語言 × 三格式，18 份實際產檔。
  指定語意檢查通過，仍有 8 筆原版 Markdown 表格阻擋，整體 acceptance false。
- 修補版：保存、混合支援二案例 × 二語言 × 三格式，12 份實際產檔；指定
  檔案及語意檢查通過，仍是 release acceptance false 的隔離 runtime 實驗。
- 全部十組案例／語言，均有 Word 預覽，並通過 preservation、sharing、polish、
  format、reading、quality、answer-state 七種指定成品檢查。
- 支援狀態逐一比對實際 fixture 與所屬資料集／管道；Q5 引言和 Q11 狀態句
  在 DSW PDF、原生 DOCX 及 Word 預覽皆保留。每個儲存庫仍是一個 Word 清單
  段落；Q11 區間未檢出純標點行。預覽檢查同一文字區塊內行與行不重疊，
  不代表所有跨區塊碰撞、字形或整體美感皆已驗收。
- 與 0.3.8 同案例、同 fixture、同 runtime 比較：原版 60 題、修補版 30 題，
  共 90 題。HTML 結構、文字及標記僅允許確切的 Q5 引言替換、Q11 支援句
  與管道範圍標記；作者原文 HTML 保留。新混合案例没有歷史同案例，不列入比較。
  這不是聲稱改文案後 PDF 全文、Word 分頁或所有段落都逐位元相同。
- 相同 ZIP 的兩個共同案例／二語言，共四組跨 worker 比較通過。
- `content-source-delta.json` 對照英中套件 `src` 全部檔案，只有 Q5、Q11、
  UUID 檔改變；PDF CSS、生成的 Word reference、Lua 皆不變。

修補版中文保存案例：DSW PDF 7 頁、Word 預覽 8 頁；混合案例兩者均 8 頁。
原版空白案例：DSW PDF 4 頁、Word 預覽 3 頁。新混合案例新增第三個資料
提供管道的缺答是刻意測試，不拿它與較少管道的歷史案例做減頁比較。

人工查看：原版空白中文 Word 第 2 頁、混合中文 Word 第 6 頁及 DSW PDF
第 6 頁；修補版混合中文 Word 第 6 頁、DSW PDF 第 5 頁。三種狀態可讀，
但仍有短尾行、同一資料集的儲存庫清單跨頁等問題，未宣稱完全解決排版。

## 下一步仍需處理

1. Q11 多個專用儲存庫都叫「本計畫專用的資料儲存庫」，閱讀時仍要靠順序
   對照 Q10 管道。應評估跨題一致的管道標籤，並處理短清單跨頁銜接，避免
   為了少翻頁而把長回答鎖成巨大區塊。
2. 原版 Markdown 表格問題、正式 worker 的部署與回退責任仍未驗收。
3. 保存選擇、具名保存地點、維護安排與經費的一致性仍需逐項核對。新增
   Yes／No 輸出不是完整 Science Europe 覆蓋，也不保證使用者所有回答互不矛盾。
4. 目標 Microsoft Word、字型替代及去識別真實專案仍待驗收。合成範例不是
   真實專案；本輪沒有讀取線上專案或 keyring。

## 版本與可重建性

英中在短期 `fix/answer-state-claims`，套件版本 0.3.9。英文來源
`4c4f487b4067ae089d347298595db09dd3583053`，實際產檔中文 checkpoint
`d0349ad0ab6538693be97d9b87b57212f5c7a831`；工具仍為
`25e339fbdfb1d20796471055790aad6a4226b6ed`。官方基底仍為 1.30.1。

英文 ZIP：`bd5482c90b847d4a4529551bf6e4365446fa3a0e8f8a67a77533b379f2a314f0`。
中文 ZIP：`28281fa99bc93ded0f5f3e9134940ff0bb67acf08113047c830d80f9e6698d27`。

原版 `outputs/build-kvd9nrd9`、修補版 `outputs/runtime-tables-6u5g5r6m`。
封存檢查器提交 `e73b2ba66d85316a60f6928e98e0019c1cd8bef1` 的乾淨重建
`outputs/build-jn_6iu8q`，兩個 ZIP 與實際產檔逐位元相同。
封存器核對來源、檢查器、套件、fixture 與產物 hash，保留未通過的表格門檻，
採 25 MB 大小上限，不複製巨大內嵌字型 HTML、不覆寫舊審閱。

英文 [CI 34813181370](https://github.com/ThreeMonth03/science-europe-template/actions/runs/34813181370)
及中文產檔來源 [CI 34813410251](https://github.com/ThreeMonth03/science-europe-template-zhtw/actions/runs/34813410251)
通過；封存提交另走分支 CI。未合併主線、未建 tag／release、未部署線上 DSW。
本機 worker 已恢復原版映像，四個 pilot 容器已停止，資料卷保留。

這組回歸案例也屬於未來 upstream 升級的驗證門檻。升級在獨立 upgrade 分支
審查英文差異，再更新中文的精確 commit lock、遷移翻譯並重產雙語成品。
Git 無衝突不代表語意或排版相容；本輪不改既定主線／發布分支政策。
