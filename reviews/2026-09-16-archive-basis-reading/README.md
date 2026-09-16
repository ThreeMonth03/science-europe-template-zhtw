# 0.3.29：延長保存期限的考量因素，中英文成段閱讀

原本的導言與三個短條列改為：

> 延長保存期限的考量因素：典藏資料的實際使用情況、典藏資料的預期使用情況、可用預算。

英文使用同樣結構、英文逗號與一個句號。只合併模板固定的勾選標籤，
沒有改寫或合併使用者的自由回答，也沒有把考量因素當成已經核准延長的結論。
每個選項保留 fact ID；缺答仍有待補提示，無法辨識的選項另標示需核對。

## 看成品

- 中文 PDF 第 6 頁：[前版](../2026-09-16-identifier-spacing/after/native/personal-transfer-complete-chinese.pdf) → [新版](after/native/personal-transfer-complete-chinese.pdf)。四行導言／短條列變成一行，Q12 的開頭可往前排。
- 中文 Word：[預覽第 7 頁](after/word-preview/personal-transfer-complete-chinese.pdf)、[DOCX](after/native/personal-transfer-complete-chinese.docx)。仍為可編輯文字，不是圖片。
- 英文：[PDF 第 7 頁](after/native/personal-transfer-complete-english.pdf)、[Word 預覽第 6 頁](after/word-preview/personal-transfer-complete-english.pdf)、[DOCX](after/native/personal-transfer-complete-english.docx)。三項合併後為兩行。
- 部分漏填：[中文 PDF 第 6 頁](after/native/preservation-partial-chinese.pdf)、[英文 PDF](after/native/preservation-partial-english.pdf)。保留五項典藏細節待補提示及已填回答。
- 完全空白：[中文 PDF](after/native/empty-chinese.pdf)、[英文 PDF](after/native/empty-english.pdf)。保留 15 題與缺答提示，不產生空白答案區。
- 單選一項：[英文前版 9 頁](before-extra/native/archive-basis-single-english.pdf) → [新版 8 頁](after/native/archive-basis-single-english.pdf)。這只是該案例的結果，不保證所有問卷都減一頁。

## 核對結果

八組中英共 48 個原生 HTML／PDF／DOCX，另有 16 份 LibreOffice 預覽，
全部完成所選檢查。為取得相同輸入的前版，另補產四組中英基準，共 24 個
原生輸出和 8 份預覽；其餘基準沿用 [0.3.28](../2026-09-16-identifier-spacing/README.md)。

| 案例 | EN PDF 前→後 | ZH PDF 前→後 | EN／ZH Word 頁數（前後相同） |
|---|---:|---:|---:|
| 三項全選 | 9→9 | 8→8 | 7／8 |
| 只選預算 | 9→8 | 8→8 | 7／8 |
| 實際＋預期使用 | 9→9 | 8→8 | 7／8 |
| 保存細節漏填 | 8→8 | 7→7 | 7／7 |
| 自訂保存期限、不可延長 | 8→8 | 7→7 | 7／8 |
| 空白 | 4→4 | 3→3 | 3／3 |
| 明確否定 | 4→4 | 3→3 | 3／3 |
| 長預算、漏幣別 | 10→10 | 9→9 | 9／10 |

HTML 全部十五題以獨立的允許差異轉換比較，不只搜尋關鍵字。Word 除
固定段落替換外，僅接受被移除清單之後的編號位移，以及緊接段落由
FirstParagraph 轉為 BodyText；已驗證兩者字型與段落屬性相同。其餘正文
XML、表格、連結、字型及樣式不變，2370 個 Word 預覽正文段落保留。
未受影響的八組語言／案例，PDF 與 Word 預覽的文字座標也完全相同。

PDF 比對保留標點及大小寫、允許折行空白。僅移除有幾何位置證明的生成
條列符號，以及經完整長預算內容核對的「續頁重複表頭與資料身分」。
中文長預算續頁從第 13／50 段改為第 16／53 段開始，60 段用途文字與
續頁資源名稱、金額、漏幣別提示及經費來源都保留，不是內容被刪掉。

另有 548 組中英分支檢查：所有勾選組合、反序／重複、未知／不合法輸入、
父題否定或漏填、有作者自由段落，並在 autoescape 開關兩種模式測試。
未知選項僅用離線測試，不偽裝成有效 KM 新選項。原生測試採已核對 KM
路徑的合成資料，沒有讀取線上使用者問卷。

## 翻譯與版本

只改 `src/post-project-archive.html.j2`，CSS、Lua、字型和 Word reference
都與 0.3.28 相同。原 731 組來源／譯文保留 727 組，四組舊句型換成五組
新單位，共 732 組，全部已填。其餘題目的翻譯檔連 metadata 都相同。
既有翻譯工具先處理每個 span 的中文，再用頓號串接；沒有第二套中文 Jinja。

兩 repo 均在短期 `fix/archive-basis-reading`，中文鎖英文完整 commit
`159f5964e27355d9ea00dbd6ce190e9f5ac9462d`。來源仍基於官方 1.30.1，
未 merge main、未 tag、未正式 release。候選與乾淨重建的兩個 ZIP 完全相同。

## 失敗紀錄與環境

第一個 HTML 因本機配額不足失敗：需 15.97 MB、僅餘 12.01 MB。確認零引用
及 ZIP 備份後，清掉本輪兩個前版暫存模板才重跑。最終兩個新版暫存模板
也已依相同條件清理；所有 ZIP 備份、樣張及 volumes 保留。

初版比對程式對 Word 相鄰樣式、中文標點 run、DOM 容器及重複表頭的假設
不完整，失敗報告與逐步診斷保存在 `diagnostics-checker/`，沒有改 ZIP 來
掩蓋問題。最終 `after/archive-basis-report.json` 才是 16 組通過的完整報告。

第一輪中文 CI 在舊 Q7 漏填檢查失敗，因它仍把全樹當成 731 組；
[失敗 run](https://github.com/ThreeMonth03/science-europe-template-zhtw/actions/runs/35065911900)
保留可查。修正後先驗證歷史差異，再僅接受本次明列的 Q11 差異；沒有移除
檢查或放任未審閱譯文。英文單元／TDK 檢查通過；CI 不取代原生視覺驗收。

worker 沿用 tables-only，沒有加入字型修補實驗。觀察期間沒有 container
restart，不能因此宣稱歷史 exit 139 根因已解決。已恢復 stock worker 並停止
四個本機服務，沒有使用 production DSW、keyring 或真實資料。

## 未完成的事

目視看過中英文 Q11 PDF／Word，以及部分漏填和空白尾頁。其他固定句之間
仍有空白、部分提示框仍零碎，英文空白文件尾頁仍很稀疏；這輪沒有宣稱
整份閱讀品質已理想。保存依據是否充分、所有 Science Europe 項目以及
Microsoft Word 實機都仍需驗收。下一步優先處理 Q11 相鄰缺答框的閱讀分組，
保留每項缺答身分和已填政策，不縮字或合併作者原文來壓頁數。

完整原生 HTML 留本機，這裡保存題目內容摘錄及原檔 hash／sidecar。
`checksums.json` 覆蓋本目錄所有其他檔案；不要將這組實驗視為正式發布。
