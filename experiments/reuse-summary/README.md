# 第 1 題再利用摘要原型

此實驗仍由自訂英文來源經既有工具產生中文，不直接維護另一份中文 Jinja。
正式 `pipeline.yml`、`translation/`、樣式與 Word 資產維持 0.3.46。

英文 repo 的 `experiments/reuse-summary/recipe.py` 鎖定
`1b0c82d9bee6984df7f11dc072ebf3c8f7726e08`。只把第 1 題非參考資料的使用範圍、
格式、穩定性與使用條件整理成每個資料集的一段摘要。自由填寫內容不改寫。

翻譯差異採多重集合精確檢查：原有 773 筆保留 763 筆，移除本區塊 10 筆，
加入 `translations.json` 的 12 筆，共 775 筆。工具會把標籤的來源句正規化，
因此 `Conditions of use.` 的對照鍵含句點，但中文標籤不加句號。

## 重建

使用已安裝固定工具 commit `25e339fbdfb1d20796471055790aad6a4226b6ed` 的環境：

```bash
python experiments/reuse-summary/build_prototype.py \
  --english ../science-europe-template \
  --tooling ../dsw-document-template-tool \
  --baseline outputs/build-37uoq1mg \
  --output outputs/reuse-summary-new-run
```

輸出目錄必須不存在。基準 ZIP 的 SHA-256、原始來源、翻譯樹與包內檔案都會驗證。
流程為英文 overlay → 展開 → 翻譯樹匯出／合併 → 指定翻譯 → 結構稽核 → TDK
verify/package → 實際包內中英分支檢查。字型、CSS 及 Word 資產必須與基準逐位元相同。
不需要 DSW 帳密、真實專案或遠端寫入。

本地原生 A/B 驗證與限制見
[`reviews/2026-09-22-reuse-summary-prototype`](../../reviews/2026-09-22-reuse-summary-prototype/README.md)。
私有專案回答、PDF、Word 及畫面不放進 repo。

## 分支與發布

中英文皆使用短期 `fix/reuse-summary-prototype` 分支；配對依據是來源 commit、
配方雜湊、翻譯差異和產物雜湊，不是同名分支。本原型使用獨立 template ID 和
0.3.47 測試版本，不代表正式模板已升級。review/submission 共用來源，不各開永久分支。
正式整合時先合入英文，再將中文 pipeline 指向明確英文 commit，重跑配對與原生回歸。

此處通過不代表整份文件都已適合繳交。空題標題、其他舊句型、整篇段落節奏，以及
Microsoft Word／DSW 伺服器端驗收仍須分別處理；不刪除 Science Europe 的要求。
