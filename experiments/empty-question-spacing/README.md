# 提交版空題間距原型

依使用者選擇：保留原題、緊縮空白，不把空題移到文末，也不新增漏填提示。
正式來源、翻譯樹與 pipeline 仍是 0.3.46。本原型疊在已封存的 Q1 摘要原型上，
只調整確定空白的題目，不改問題文字、答案或翻譯。

英文新增一個共用判斷器；HTML／PDF 套用局部間距，Word 只解除空題標題的
「與下段同頁」並調整段前距離。已填題目仍連著答案，原有字型、Word 樣式檔及
短表格處理器不變。零值、圖片、表格、自由文字、未知結構皆不視為空白。

```bash
python experiments/empty-question-spacing/build_prototype.py \
  --english ../science-europe-template \
  --tooling ../dsw-document-template-tool \
  --baseline outputs/reuse-summary-prototype-04 \
  --output outputs/empty-question-spacing-new-run
```

工具仍鎖定 `25e339fbdfb1d20796471055790aad6a4226b6ed`。先驗證舊原型 ZIP 與配方，
再套用英文更動、走既有翻譯流程。775 個翻譯配對必須全部相同；新配方雜湊按
英文／中文 repo 分開記錄，避免同名 README 混淆。只增加局部 CSS、三個共用輔助檔
及提交 Word 的處理步驟。檢核版處理步驟不改。

新產物使用 `science-europe-empty-question-prototype[-zhtw]` 的獨立 ID／測試版號
0.3.47，不代表正式版本已發布。短期分支為 `fix/empty-question-spacing`；版本配對
以 commit、配方、翻譯及 ZIP 雜湊為準，不依賴同名分支。
驗證紀錄見 [公開彙總](../../reviews/2026-09-22-empty-question-spacing/README.md)。
真實專案、答案、PDF、Word 及截圖只放在本機私有目錄。

通過後的整合方向：將 Q1 摘要與空題間距一次接回英文正式來源，中文再鎖定該
commit 重建，保留檢核／提交兩個格式。不要把實驗疊加機制變成長期正式架構。
空白文件仍不適合繳交；這次改善的是排版，不是替使用者完成回答。
