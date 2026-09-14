# 0.3.6：共享限制、保存敘述與日期審閱

2026-09-14。本文件另封存為 `reviews/2026-09-14-sharing-preservation/README.md`，
下列樣張連結以封存目錄為準。這是本機 DSW、合成回答的實驗，不是正式發布，
也不是全部 Science Europe 內容或 Microsoft Word 驗收。

## 先看文件

表格修補 worker 的同套件實驗樣張：

- 多管道共享與保存：[中文 PDF](tables/storage-sharing-chinese.pdf)、[Word](tables/storage-sharing-chinese.docx)。
- 自訂申請流程與付款安排：[中文 PDF](tables/sharing-custom-chinese.pdf)、[Word](tables/sharing-custom-chinese.docx)。
- 部分缺答與需核對事項：[中文 PDF](tables/sharing-missing-chinese.pdf)、[Word](tables/sharing-missing-chinese.docx)。
- 長篇限制回答：[中文 PDF](tables/narrative-long-chinese.pdf)、[Word](tables/narrative-long-chinese.docx)。
- 一般案例：[中文 PDF](tables/structured-chinese.pdf)、[Word](tables/structured-chinese.docx)、[英文 PDF](tables/structured-english.pdf)。

原版 worker 對照：

- [多管道中文 PDF](stock/storage-sharing-chinese.pdf)、[Word 預覽](stock/word-preview/storage-sharing-chinese.pdf)。
- [缺答中文 PDF](stock/sharing-missing-chinese.pdf)、[全空回答 PDF](stock/empty-chinese.pdf)。

## 這輪解決的問題

Q10 的授權日期與固定限制引言放在同一個閱讀段落。申請方式、是否公開取用
條件與詳細資訊連結，則以另一個固定敘述段落呈現。標準 CC0／CC BY 授權仍
承接上一輪的合段規則，不因新增包裝而退回零碎段落。

「其他申請流程」原本將 Markdown 回答插入固定句子，現在分為固定說明與
作者回答區塊，保留多段與清單。已選專用流程但未填具體內容時，保留選擇並
提示缺少細節；未選申請方式亦獨立提示。取用條件的公開決定，區分是、否及
未回答，不從空白推論為否。

Q11 的發布狀態、保存期間、資料不存在後的後設資料安排，合為一個固定敘述
段落；經費與時間／人力預算的固定句亦可合段。缺保存期限、需核對的預付費用
提示，以及自訂付款說明，仍是明確段落邊界。複雜儲存庫敘述與儲存庫清單
本輪沒有重寫，也沒有把長篇自由回答整塊鎖定在一頁。

中文修訂限本輪固定句：使用「欲再次使用資料者」、「本計畫專用的資料儲存庫」
等一致用語，簡化經費敘述；後設資料的說明不再多加英文沒有的「原始」限定。
詳細資訊連結改為可翻譯的完整句子，因此中文句尾使用句號，不再沿用英文句點。
這不是全篇中文術語校訂完成，作者填寫的詞句沒有被全域替換。

## 日期處理的界線

只對授權日期欄位中 `YYYY-MM-DD` 形狀的值標記不換行。HTML／PDF 使用局部
CSS；Word 只把該標記內的兩個連字號改為 U+2011 不換行連字號。原本的數字、
日期順序沒有改變。這是排版提示，不是檢查日期是否真實有效。

檔名 `Access-2027-12-31.csv`、`Budget-2027-12-31.csv` 與自由回答保持 ASCII
連字號。檢查器只將 HTML 明確標記日期的已知 Word 表示法對回原值，不抹掉
所有連字號。PDF／Word 預覽的日期檢查限定 Q10 範圍，避免封面上的同一日期
掩蓋正文斷行；測試也排除檔名被誤算為完整日期的情況。

日期可以整個移至下一行，但不應在年、月、日之間拆開。日期標籤與數值未必
同行，這不是「授權起始日期：」與日期整句不可換行的保證。

## 驗證結果

- 英文 69 項測試及 TDK verify 通過；中文 45 項測試通過。
- 660 個翻譯單位，空白 0，translation／structure audit 無錯誤。
- 新增 52 組 Q10／Q11 雙語離線檢查，另重跑格式／容量 76 組、蒐集方式 24 組、
  品質措施 512 組。這些是 reply adapter 檢查，不是 DSW 產檔次數。
- 兩個 native Pandoc AST 案例確認固定句合段、不換行日期、缺答隔離及自由回答
  段落。這項以已知 HTML 取代 fixture 的 Markdown，單獨測 Lua；真正的 Markdown
  仍由下列 DSW 端到端產檔驗證。
- 新增的 `sharing-custom`／`sharing-missing` 及舊 fixtures 通過本機編譯英中
  Common KM 2.7.0 路徑檢查。30 個 Jinja 檔案的靜態 binding audit 未發現未定義
  變數或不存在的實體；此數字不是內容覆蓋率。
- 原版 worker：7 案例 × 2 語言 × HTML／PDF／DOCX，共 42 份產檔。所選語意
  檢查通過，仍保留 24 筆既知表格阻擋，整體 acceptance 為 false。
- 原版 14 組案例／語言的 sharing、polish、format、reading、quality 檢查通過。
  與 0.3.5 相同五個案例的 150 個題目比較通過；只允許程式明列的 Q10／Q11
  中文固定句修訂，其他題目與自由回答不可變更。新兩個案例沒有舊版同名輸出，
  不列入這個比較數字。
- 表格修補 worker：6 案例 × 2 語言 × 3 格式，共 36 份產檔，所選語意與
  檔案檢查通過。12 組案例／語言的上述五種閱讀檢查通過；與 0.3.5 相同
  四個案例的 120 個題目比較通過。新兩個案例仍不計入歷史比較。
- 兩種 worker 使用逐位元相同的英中 ZIP；跨 runtime 的 12 組案例／語言
  比較通過。檢查範圍內的 Q2–Q15 文字及 fact markers 保持一致，Q1 表格
  儲存格內容保留。這不是逐像素相同或所有 KM 路徑都已覆蓋。
- 兩種 worker 各產生 7 份 LibreOffice Word 預覽：六個非空中文案例及一般
  英文案例。PDF 和這些預覽均通過頁面邊界檢查；存在授權日期的 Q10 範圍
  另通過日期不拆行檢查。沒有用其他頁面的相同日期替代正文檢查。

`sharing-report.json` 對實際 DOCX paragraph 檢查固定句合段、缺答／作者段落
隔離、日期表示法及原有檔名。兩個語言的所有十五題 fact markers 相互對應。
`narrative-long` 的 80 個延伸限制段落逐段保留，沒有合成一個巨大段落。
其他閱讀檢查器本輪只做輸出驗證，不使用它們舊迭代專用的 `--prior` 比較。

中文頁數如下，Word 欄指 LibreOffice 預覽，不是 Microsoft Word 實測：

| 案例 | 原版 PDF | 原版 Word 預覽 | 表格修補 PDF | 表格修補 Word 預覽 |
| --- | ---: | ---: | ---: | ---: |
| 一般案例 | 6 | 6 | 6 | 7 |
| 多管道共享與保存 | 6 | 7 | 6 | 7 |
| 部分共享缺答 | 6 | 7 | 6 | 7 |
| 80 段長回答 | 9 | 10 | 9 | 10 |
| 自訂流程與付款 | 7 | 8 | 7 | 8 |
| 本輪新增缺答組合 | 7 | 8 | 7 | 8 |

原版全空中文 PDF 為 4 頁，沒有為此案例產生 Word 預覽。一般案例的表格修補
Word 比原版多一頁；表格恢復結構後會影響分頁，不能以頁數較少當作品質合格。

## 人工觀察與仍待處理事項

已檢視原版多管道案例 PDF 第 5 頁、Word 預覽第 5–6 頁，自訂流程 PDF 第 5 頁
與 Word 第 6 頁、缺答案例 PDF 第 5 頁。多管道案例的保存期間與經費安排已
較連續，日期未在年月日之間拆開，缺答和需核對事項仍清楚區分。

表格修補版另檢視多管道 PDF 第 5 頁與 Word 預覽第 5–6 頁、自訂流程 Word
第 6 頁、缺答 PDF 第 5 頁、一般案例 PDF 第 3 頁的表格，以及長回答 PDF
第 6–8 頁。長回答仍逐段跨頁，結尾接回申請與保存說明；不是將 80 段併成
一段來減少頁數。這是列明頁面的人工抽查，並非全部頁面的美感評分。

尚未完成的部分：

1. Word 仍可能把申請流程或共享細節接至下一頁；保留長回答可分頁，不代表
   頁間銜接已最佳化。部分 Q13 區塊也仍跨頁。
2. 缺答案例會有數個提示框，視覺上仍較重；不能為了減少提示而隱藏未填欄位。
3. 複雜儲存庫說明、Q13 以及其他題目的稱謂／句型還未完成全文校訂。
4. Q11 變得好讀，不等於已充分回答「如何選擇保存哪些資料」。repo 的十五題
   requiredTopics 對照仍未完成逐欄內容審閱；下一步應盤點回答去向與 SE 主題
   缺口，分清模板漏用、尚未填答與尚未確認的 KM 映射，不能只繼續調段距。
5. 原版 worker 的 Markdown 表格問題仍在。修補 worker 仍是隔離實驗，需要
   另行確認維護責任與部署／回退方案；本輪未部署。
6. LibreOffice 預覽不是 Microsoft Word 實測。仍需目標 Word 環境與去識別真實
   專案驗收，不能以合成案例取代最終使用者閱讀測試。

## 版本、來源與回退

英中皆在短期 `feat/sharing-preservation`，套件版本 0.3.6；邏輯只維護於客製
英文，繁中仍由翻譯樹與既有工具產生，沒有 JSON／LLM runtime workaround。
官方基底仍為 1.30.1／`22d60aae4b63ee677477ac0c73097807284aaf9f`。
Q10、Q11、macro、PDF CSS、Word Lua 均在 upstream 升級審閱範圍內，升級須
重新檢查缺答、作者段落、日期與雙語成品，不能只看 Git 是否衝突。

英文來源：`431ad56aeaa42c3752f0fe6e851276790504f2b1`。
中文實際產檔 checkpoint：`2e99a84ab9e2da26b1ffdfb2998126d4c0252c52`。
工具仍鎖定：`25e339fbdfb1d20796471055790aad6a4226b6ed`。

英文 ZIP：`e29829e94cae37822acec9a394603014a0f3837458958490ee546bbdc6aa63a9`。
中文 ZIP：`e0cda54a4866a6a5fbec4931648dcbf66a24ff8cf065b54770bec58d95a9ad4b`。

加入檢查器後，中文 `303303640676675fd443d3dc4a17719fca5992f1` 的乾淨重建
`outputs/build-23fr0dn8`，兩個 ZIP 與實際產檔套件逐位元相同；證據保留於
`rebuild-manifest.json`。原版產檔為 `outputs/build-gmqwp0tm`，表格對照為
`outputs/runtime-tables-fb0pt6pz`。報告綁定各自套件與產物 hash，不挪用其他版本
的成功狀態；舊版審閱樣張不覆寫。

英文 [CI 34805255239](https://github.com/ThreeMonth03/science-europe-template/actions/runs/34805255239)
與中文來源鎖定 [CI 34805343296](https://github.com/ThreeMonth03/science-europe-template-zhtw/actions/runs/34805343296)
通過。CI 已加入新增雙語分支檢查，但沒有宣稱包含 Microsoft Word 視覺驗收。
工具 MinIO 修復分支仍是前輪已驗證、待確認後合併的狀態；本輪未修改工具或
觸發 master 發布流程。未合併主線、未建立 tag／release、未操作線上 keyring
或 project。本機 worker 已回復原版映像，四個 pilot 容器已停止，測試資料卷
保留，未刪除其他環境資料。
