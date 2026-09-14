# 0.3.7：補回保存回答，不替使用者編造保存政策

2026-09-14。本文件另封存於 `reviews/2026-09-14-preservation-coverage/README.md`，
下列樣張連結以封存目錄為準。本輪使用本機 DSW 與合成回答，不是正式發布，
也不是全部 Science Europe 主題或 Microsoft Word 驗收。

## 先看文件

表格修補 worker 的同套件對照樣張：

- 完整保存安排：[中文 PDF](tables/preservation-complete-chinese.pdf)、[Word](tables/preservation-complete-chinese.docx)、[Word 預覽](tables/word-preview/preservation-complete-chinese.pdf)。
- 部分缺答：[中文 PDF](tables/preservation-partial-chinese.pdf)、[Word](tables/preservation-partial-chinese.docx)。
- 自訂期限與不續存：[中文 PDF](tables/preservation-custom-chinese.pdf)、[Word](tables/preservation-custom-chinese.docx)。
- 明確不採用冷儲存：[中文 PDF](tables/preservation-no-cold-chinese.pdf)、[Word](tables/preservation-no-cold-chinese.docx)。
- 舊的一般案例：[中文 PDF](tables/structured-chinese.pdf)、[英文 PDF](tables/structured-english.pdf)。

原版 worker 仍有已知 Markdown 表格缺陷，保留作為對照：

- 完整安排：[中文 PDF](stock/preservation-complete-chinese.pdf)、[Word](stock/preservation-complete-chinese.docx)。
- [部分缺答 PDF](stock/preservation-partial-chinese.pdf)、[全空回答 PDF](stock/empty-chinese.pdf)。

## 這輪補回什麼

本機編譯的英中 Common KM 2.7.0 各有 592 個可到達的問題 ID；這只是盤點
大小，不是模板覆蓋率的分母，也不表示每題都應塞進 DMP。這輪針對保存相關
問題確認了 16 個原先沒有任何 Jinja 靜態引用的欄位，逐一接回 Q11。

| 回答群組 | 數量 | 輸出位置與語意界線 |
| --- | ---: | --- |
| 產生資料集的描述、處理階段、相關論文 | 3 | 各資料集；論文僅在對應階段啟用 |
| 不公開發布的理由、自訂理由 | 2 | 各資料集；不公開不等於銷毀或不保存 |
| 計畫結束後的冷儲存及後續安排 | 11 | 計畫層級，只出現一次，不套用到每個資料集 |

冷儲存安排涵蓋費用負擔者、最低保存期限、自訂年數／其他安排、是否可延長、
無法延長的原因、決定延長的人員、各項續存依據、過時格式的處理及媒體移轉。
選了「是」但漏填後續項目時，已填資訊保留，缺少的細節另行提示。選「否」
與未回答分開處理，亦不從遺留的子題回答反推父題選擇。

四個新增案例均有兩個資料集。第二個不公開發布，仍明確保存十五年；計畫的
冷儲存期限則另列。這能檢查是否錯把發布、保存與計畫層級安排混在一起。
自訂期限、資料描述與不發布理由保留作者的多段文字和清單，不嵌入固定句子，
也不以 LLM 改寫。`Selection-2027-12-31.csv` 的原有字元不變。

## 為什麼仍有「保存選擇需核對」

Science Europe 的 SE-5b 指引要求說明保存／銷毀的決定、選擇依據、保存內容、
未來用途，以及儲存庫安排等。只有保存年限或儲存庫名稱並不足以完整回答。
來源為 [Science Europe 2021 Extended Edition，研究者指引及評估準則](https://www.scienceeurope.org/media/4brkxxe5/se_rdm_practical_guide_extended_final.pdf)
（印刷頁 24–25，CC BY 4.0）。

這輪恢復的「續存依據」回答的是已典藏資料何時延長保存，不等於最初如何
選擇哪些資料集／版本要保留或銷毀。因此 Q11 有內容時保留需核對提示；這是
模板尚未建立完整內容對照的提醒，不是假裝使用者漏答了一個已確定存在的題目。
全空回答仍維持既有缺答輸出。

盤點中兩個容易誤用的題目沒有拿來湊答案：工作空間下的原始資料備存選擇
不是通用的逐資料集保存政策；「其他研究產出」的選擇題，其指引明確區分於
資料集。已存在 Q13 的量測資料再次使用資訊亦保留原位置，不靠名稱猜測關聯。
目前未證實通用保存選擇政策的完整 KM 映射，不能宣稱本輪已滿足全部 SE-5b。

## 排版與中文

沿用既有固定敘述合段與自由回答邊界，不改 PDF CSS、Word reference 或 Lua。
初次候選 `outputs/build-4ticjo7u` 的經費段落接在冷儲存標題之後，視覺上容易
被誤認為冷儲存的經費。本輪已退回英文修正：資料儲存庫／發布準備經費在前，
計畫冷儲存在後，有內容才顯示經費小標題。初次候選未作為本次接受封存的樣張。

中文新增固定句經逐句審閱；例如「本計畫結束後不採用冷儲存；這項回答並不
排除其他保存方式」，保留否定的真正範圍。對不發布理由中的再次使用價值，
以「依問卷填答」表明這是填答者的判斷。未全域替換作者回答或其他題目用語。

實際 PDF 與 Word 預覽新增 Q11 範圍的文字座標檢查，拒絕只有句號等標點的
獨立文字行。這是所選案例的有限檢查，不等於全篇中文禁則排版驗收；正文以
「力。」等極短尾行收尾、Word 較疏的行距，以及部分 Q13 分頁仍待改善。

表格檢查也修正了全文搜尋的誤判：資料描述中正常出現的「處理紀錄」，不能
被算成溯源表格跨頁。現在以 Q1／Q2 題目邊界定位，保留實際頁碼。測試確認
區外文字不會補救遺失的表格儲存格，真正跨頁仍被辨識。另以舊的中英 48 列
長表格產物唯讀回歸檢查通過，沒有重寫其報告或樣張。

## 驗證結果與範圍

- 英文 80 項測試、TDK verify 通過；中文 54 項測試通過。
- 709 個翻譯單位，空白 0，translation／structure audit 無錯誤。
- 保存新增 122 組離線分支／語言檢查、715 次固定句精確比對；另重跑共享 52、
  格式／容量 76、蒐集方式 24、品質措施 512 組。這些不是 DSW 產檔次數。
- 新舊 fixtures 均通過編譯英中 KM 路徑檢查，包含多選選項的成員資格。
  最終英文來源的 33 個 Jinja 靜態 binding audit 未發現未定義變數或不存在
  的實體；這不表示所有可選題目的輸出已覆蓋。
- 原版：六案例 × 二語言 × HTML／PDF／DOCX，共 36 份產檔；所選語意檢查
  通過，仍有 20 筆既知表格阻擋，整體 acceptance 為 false。
- 表格修補版：五個非空案例 × 二語言 × 三格式，共 30 份產檔，所選語意與
  檔案檢查通過。修補 worker 仍為隔離實驗，release acceptance 為 false。
- 原版 12、修補版 10 組案例／語言，均通過 preservation、sharing、polish、
  format、reading、quality 六種輸出檢查。原生 DOCX 段落、作者回答、缺答隔離、
  數字單位與所選 PDF／Word 預覽頁面邊界均包含在內。
- 與 0.3.6 比較，原版一般／空白案例有 60 個題目比較，修補版一般案例有
  30 個；只容許新增的 Q11 保存選擇提示，其餘題目文字、fact markers 和
  作者區塊保持一致。四個新增案例沒有舊版同名產物，不列入歷史比較數字。
- 兩種 worker 使用相同英中 ZIP；10 組跨 runtime 比較通過，檢查範圍內
  Q2–Q15 文字與 fact markers 一致，Q1 表格儲存格内容保留。這不是逐像素相同。
- 兩種 worker 各有六份 LibreOffice Word 預覽：五個非空中文案例及一般英文。
  Microsoft Word 尚未實測，沒有將預覽冒充目標 Word 環境驗收。

本輪兩種 worker 的中文頁數相同：

| 案例 | PDF | Word 預覽 |
| --- | ---: | ---: |
| 完整保存安排 | 7 | 9 |
| 部分缺答 | 7 | 8 |
| 自訂期限 | 7 | 9 |
| 不採用冷儲存 | 7 | 8 |
| 一般案例 | 6 | 7 |

原版空白 PDF 為四頁，未產生其 Word 預覽。頁數增加不是品質指標，本輪的
重點是確認相關已填內容不再遺漏，且沒有混淆不同回答的適用範圍。

人工抽查：原版完整 PDF 第 6 頁、Word 第 7 頁，缺答 PDF 第 6 頁，自訂期限
PDF 第 6 頁／Word 第 7 頁、不採用冷儲存 PDF 第 6 頁；修補版完整 PDF
第 6 頁／Word 第 7 頁、缺答及不採用冷儲存 PDF 第 6 頁、自訂期限 Word
第 7 頁、一般 PDF 第 3 頁的表格。這不是所有頁面的美感評分。

## 版本、重建與下一步

英文與中文皆為 0.3.7，使用短期 `feat/preservation-coverage`。可執行邏輯
仍只維護於英文 repo，中文由既有翻譯樹生成；本輪沒有 KM／JSON／LLM runtime
變更。官方基底仍為 1.30.1／`22d60aae4b63ee677477ac0c73097807284aaf9f`。
新增三個小型 Jinja partial、Q11 與 UUID 定義已列入 upstream 升級必審範圍。
未來升級以 commit lock、欄位契約、分支案例和英中成品比對控制，不能把 Git
沒有文字衝突當成輸出相容，也不為每次中文措辭建立永久分支。

英文來源：`320c4ff3e56548593c5de917f417f1e37a0fcf5a`。
中文實際產檔 checkpoint：`eb41ec0bdf0235eb6d63ca42acda3fd251a20032`。
工具保持：`25e339fbdfb1d20796471055790aad6a4226b6ed`。

英文 ZIP：`2eaabcdd715e9ec808cae066d496d651018acf63a517b0308794aa58bf0f2144`。
中文 ZIP：`e7b3afffb6886a6a82851684cab2a8e96cc135448267f4ff3476ce45e4cb506a`。

原版 `outputs/build-q1sbl2nj`，修補對照 `outputs/runtime-tables-_hotg4jb`；
另一乾淨重建 `outputs/build-1k343ony` 的 ZIP 逐位元相同。封存的報告綁定
實際套件、產物和檢查器 hash；`rebuild-manifest.json` 保留重建來源，
`checksums.json` 保留封存檔案校驗碼。封存前檢查 25 MB 上限，舊審閱不覆寫。

英文來源 [CI 34808291224](https://github.com/ThreeMonth03/science-europe-template/actions/runs/34808291224)
及中文來源鎖定 [CI 34808411123](https://github.com/ThreeMonth03/science-europe-template-zhtw/actions/runs/34808411123)
通過；後續檢查器／審閱提交另走分支 CI。CI 不包含目標 Microsoft Word 視覺驗收。
工具 MinIO 修復分支仍待合併，本輪未更動工具或觸發 master 發布。
未合併主線、未建 tag／release、未部署或操作線上 keyring／project。本機 worker
已回復原版映像，四個 pilot 容器已停止，資料卷保留。

下一步先做剩餘 SE 主題的逐欄回答去向審閱，尤其保存選擇、保存地點與永續性，
區分模板漏用、使用者未填與 KM 尚無適當問題。需要新增台灣版問題時另設計
KM 對照，不從不相干欄位拼湊答案。版面方面另處理 Word 行距／跨頁與缺答
提示的密度；修補 worker 的部署責任、回退及去識別真實案例仍須另行驗收。
