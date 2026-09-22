# 完整問卷分支漏輸出修補原型

這不是正式新版：`pipeline.yml`、既有 767 筆翻譯及 `0.3.45` 套件均未變更。
兩個 repo 使用短期分支 `fix/full-km-followups-prototype`，不新增長期中文
邏輯分支。英文維護邏輯，中文維護翻譯；內部檢核／提交預覽仍共用邏輯。

這次接回三種既有填答：檔案命名規則、**本計畫建立**之參考資料發布時程、
維護方式，分別呈現在 Q3、Q10、Q11。不是把「再次使用的參考資料」與
「本計畫建立的參考資料」合併，也不會把同一答案套到每筆資料集。

- 父選項未啟用、KM 篩掉題目或題目結構改變：不印舊答案，也不當成漏填。
- 已啟用但文字漏填：只在內部檢核版提醒；提交預覽不留空標籤。
- 填答原文保留 Markdown、連結、大小寫、數字及標點；不交給 LLM 改寫。
- 翻譯沿用原有轉換流程：保留 767 筆，增加 6 筆，其中既有相同標籤可自動沿用。
- 補回內容後發現 Q10 識別碼型別與值可能跨頁，故另加一條限縮範圍的 CSS。
  字型、Word 資產與轉換步驟均未變更。

## 重現（本機，僅公開／虛構資料）

先 checkout 兩個 repo 的上述實驗分支，並安裝 `pipeline.yml` 所鎖定的工具。
`--baseline` 必須是原本通過檢查的乾淨 `0.3.45` build；程式會驗證其套件與
prepared source，不接受任意舊 ZIP。`--output` 必須不存在。

```bash
../dsw-document-template-tool/.venv/bin/python experiments/full-km-followups/followup_build.py \
  --english ../science-europe-template \
  --tooling ../dsw-document-template-tool \
  --baseline outputs/build-bd4a7v4e \
  --output outputs/full-km-followups-reproduction
```

新套件使用獨立的 `science-europe-followups-prototype[-zhtw]` ID，版本欄位
`0.3.46` 只屬於實驗 ID，不代表正式模板已升級。不要上傳為正式模板。
build manifest 記錄實驗 checkout、鎖定來源、工具、翻譯差異與 ZIP 雜湊。

`identifier_native.py` 使用 worker 內的 WeasyPrint，以虛構 ARK 在頁邊界
重現並驗證「型別／識別碼分頁」；也檢查使用者自寫清單未受 CSS 影響。
請在固定 worker image 與 `--network none` 下執行。這不等同 Microsoft Word
驗收，也不能代替整份文件的人工校閱。

本次結果見 [原型驗證紀錄](../../docs/full-km-followup-prototype-review.md)。

## 下一個整合門檻

將驗證過的來源變更整合到英文，再透過正常 refresh 收入六筆中文翻譯、
更新英文 commit lock，新增嚴格的版本差異驗證層，保留所有舊 CI 基準。
乾淨 candidate 重建與實際 PDF／Word 檢查完成前，不替換現有版本。

真實專案答案、PDF、DOCX 和截圖一律留在 repo 外的私人測試目錄；
公開版本只保存程式、虛構資料與不含答案的測試摘要。
