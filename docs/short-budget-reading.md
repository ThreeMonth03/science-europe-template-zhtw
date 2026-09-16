# 0.3.25 短預算缺答閱讀實驗

英文負責 `budget-reading.html.j2` 的有界限判斷與共用 CSS；中文只更新
`pipeline.yml` 的英文 commit。731 個翻譯檔不變，不另維護中文 Jinja。
兩個 repo 的短期工作分支皆為 `fix/short-budget-reading`，不是永久相容線。

## 驗證順序

1. 凍結 HTML 試算不同欄寬，保留使英文表格更高的未採用方案。
2. 短表格 class 僅在 PDF 入口產生；42 組原樣保留與邊界案例，中英各自
   跑一般與 autoescape 模式。使用者標題仍跳脫，不對整份回答套用 safe。
3. Source scope 對照已保存的 0.3.24：只有 helper 新增區塊與 CSS 改動，
   Q15 題目／回答邏輯、其餘 prepared src 和所有譯文不變。
4. 七組同輸入的中英原生 HTML/PDF/DOCX 與 LibreOffice 預覽，再核對
   15 題、缺答、0 金額、長回答、Word 本文／樣式／連結與分頁。
5. 最後保存原生前後對照、失敗版、來源／套件 hash、清理與 runtime 復原
   紀錄，重新建置確認相同 ZIP。建置／CI 通過不等同視覺或 Word 實機驗收。

第一版原生輸出抓到「固定 table 標籤被 autoescape 印成文字」；拒收版保留，
修正版另完整重產，不混用相同 0.3.25 版號但不同 hash 的證據。

對照與限制見 [原生審閱紀錄](../reviews/2026-09-16-short-budget-reading/README.md)。
英文稀疏尾頁、Microsoft Word 實機與 stock worker 表格相容性仍未宣告解決。
Word 短預算提示的窄欄折行也仍保留，是下一步的格式改善項目。
修正版原生重測中，worker 在第 41 份完成後 exit 139（非 OOM）；同映像
重啟後最後一份 Word 完成。故障與復原記錄保留，沒有宣稱根因已修好。
未合併 main、建立 tag、發布或操作線上 DSW。
