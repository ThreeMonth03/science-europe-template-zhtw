# 0.3.21：個人資料追問與缺答呈現

英中使用短期分支 `fix/personal-data-followups`，承接 0.3.20；不是新增永久維護線。
英文來源以 `pipeline.yml` 的完整 commit 為準，官方基底與工具版本皆不變。

這輪先修內容正確性，沒有改 PDF CSS、Word Lua／reference 或 Q15：

- Q7：法律依據漏填、選「其他」但未指定、可識別程度、其他保護措施、是否
  跨境傳輸、傳輸保護措施，分別提示缺答；僅在對應父分支被選擇時顯示。
- 已選跨境傳輸「是」，即使措施漏填也保留傳輸意向；明確「否」則如實寫出，
  不當成缺答，亦不讀取失效 Yes 分支的舊回答。
- 自由回答的原段落、清單、強調與連結放在獨立 `answer-detail`，不把 Markdown
  產出的區塊塞進 `<p>`。中文保持自然的引導語，不用缺答提示代填措施。
- 實際編譯 KM 的 GDPR「Explore」只用來展開題組，Q9 不再推論為已完成探討。
  「公共利益」僅呈現填報的法律依據，不自行加上公共利益高於隱私的判斷。
  「其他法律依據」漏填時用完整句指向 Q7，不留下半句與冒號。

翻譯共 731 單位：0.3.20 的 723 組中完整沿用 718 組，移除／替換 5 組，新增
13 組。精確句對差異記在 [translation delta](personal-data-translation-delta.json)，
任何其他措辭、標點或數量差異都會讓檢查失敗。舊 0.3.20 的 +1 翻譯證明仍以
原 commit 核對；不回寫歷史樣張或把新版修改冒充舊版輸出。

合成案例含四組新追問狀態，加上原有 personal-data-partial、empty、negative、
preservation-complete。中英使用同一組回答結構，先通過各自 server-compiled KM
路徑驗證，再由同一候選套件產生 HTML、PDF、DOCX，Word 另用 LibreOffice 預覽。
失效子分支僅用 adapter 測試，不作為合法問卷的原生案例。

缺答提示是「尚未提供這項資訊」，不是新增必填法規，也不證明法律或 Science
Europe 全面合規。其他同意程序、DPIA 等追問尚未完整盤點；短預算提示折行、
整份文件留白、正式 Word 環境與 stock worker 的 Markdown 表格仍待處理。
不得僅憑建置／單元測試通過就發布為正式版。
