# 0.3.38 雙模式原生實驗：內容切換通過，整篇版面未驗收

同一套英文邏輯、同一條中文轉換流程，已能提供「內部檢核／提交預覽」選項。
本輪只完成指定區塊的提示切換，**不是所有專案都可直接繳交的正式 DT**。
沒有發布 release、合併主線或修改正式 DSW。

## 樣張

| 語言 | 檢核 PDF | 提交預覽 PDF | 檢核 Word | 提交預覽 Word |
| --- | --- | --- | --- | --- |
| 中文 | [PDF](native/profile-partial-review-chinese.pdf) | [PDF](native/profile-partial-submission-chinese.pdf) | [DOCX](native/profile-partial-review-chinese.docx) | [DOCX](native/profile-partial-submission-chinese.docx) |
| 英文 | [PDF](native/profile-partial-review-english.pdf) | [PDF](native/profile-partial-submission-english.pdf) | [DOCX](native/profile-partial-review-english.docx) | [DOCX](native/profile-partial-submission-english.docx) |

[中文內部清單](internal-checklist-chinese.md)／[英文內部清單](internal-checklist-english.md)，不放入提交預覽文件。
Word 的 [預覽 PDF](word-preview/) 由 LibreOffice 25.2.3.2 產生，並非 Microsoft Word 驗收。
樣張中的「尚待補充：這是使用者填寫的方法說明……」是刻意放入的原始答案；提交預覽保留它才是正確行為。

## 已證明的範圍

- 一組中英合成問卷，各 115 個可達回答；以同一份回答產生兩種模式，共 12 份原生 HTML/PDF/DOCX、4 份 Word 預覽。
- 指定的 Q3、Q5 對應限制、Q11 檢視提醒與經費來源空列可略去；品質管控肯定事實仍存在。
- 檢核清單各有 10 個項目，包含品質管控在 Q1/Q4 各一次，以及缺答、模板對應限制及待檢視項目，不是 10 個不同的漏填欄位。
- 此樣張提交預覽沒有剩餘的系統 `.data-gap`；保留使用者答案、否定事實、限制、金額 5000/0 TWD、日期、連結與檔名。
- 比對完整正文的字詞、標點與順序；PDF 只另外處理經核對數量的自動清單符號和已驗證頁尾。Word styles/font table 相同，外部連結不變。
- 六大節、十五題保留；中英 native PDF 與 Word 預覽均為檢核 6 頁、提交 6 頁。
- 65 組合成案例、兩種 escaping、兩種語言的輸出投影檢查；英文檢核內容另比對 0.3.37。既有 Q2/Q3/Q5/Q11 門檻與 747 組翻譯保留。

詳細 [原生檢查報告](output-profiles-report.json)、[來源範圍檢查](provenance/output-profiles-scope.json)、[逐頁概覽](visual/)。
`selected_checks_passed` 僅指內容切換及列明的檢查，不代表排版全面通過。

## 沒有通過的版面與文字項目

[人工檢視紀錄](visual-review.json) 保留五個未解項目：

1. 中文提交 Word：Q11 題目與資料集名稱留在 p4 頁尾，答案從 p5 才開始（[p4 放大](visual/detail-submission-chinese-word-p4.png)、[p5 放大](visual/detail-submission-chinese-word-p5.png)）。
2. 中文提交 PDF：短預算表獨占 p6 上方，與 p5 的 Q15 說明分離。
3. 中文檢核 Word：Q5 說明在 p3，兩個限制項目在 p4；位置檢查為 `[3,3,3,4,4]`。
4. 英文檢核 PDF：Q1 共用政策標題／引言在 p2，正文在 p3。
5. 中文固定句仍有部分句號前空格；本輪沒有改寫原有譯文或做全篇中文潤飾。

以上說明「去掉提示」與「成品好讀」是兩個不同驗收門檻。下一輪優先修可重現的
短標題＋首段連頁、短預算尾頁，再擴大可切換提示的範圍。不能只靠頁數不增加判定完成。

## 可重現性與生命週期

原生套件來自乾淨鎖定建置 `build-0iw05v9s`，執行副本為 `runtime-tables-stkosfij`。
英文套件來源 `d1c84510e7875bc5fb36f68b101f9fd99f1ea1be`、中文建置來源 `e2a2358`；
後續英文 `3c4827a` 只補 CI 完整歷史擷取，不改模板。中文仍鎖定實際產檔來源 commit。
工具來源及套件雜湊見 [manifest](provenance/manifest.json)。
同一個 tables-only 隔離 worker 完成所有 12 次產檔，零重啟；未使用正式站帳密。
兩個本輪暫存模板在確認引用為 0、ZIP 備份有效後刪除；恢復 stock worker 並停止四個本機服務，未刪任何 volume。

完整 HTML 內嵌字型每份約 16 MB，保留在 runtime 目錄；repo 保存有原檔雜湊的
研究概要＋問答 HTML 擷取、原生 PDF/DOCX、回執、預覽、頁面文字及檢核清單。
`reproduce/` 保存本輪 checker/collector；本機 checker 開發過程的 v1–v4 失敗報告仍在 runtime 目錄，
其原因是清單符號抽取及頁尾／舊 bounding box 假設，未透過修改成品來使檢查通過。
