# 混合長／短預算試驗

以鎖定英文來源的 `budget-many` 與 `budget-long` 公開合成資料為基礎，
新增五種情境，每種都有英文／繁體中文。這些是測試資料，不是真實專案。

- `mixed-long-last`：八筆短列，後接一筆 60 段用途的長列。
- `mixed-long-first`、`mixed-long-middle`：只改同一組資料的排列。
- `mixed-small-groups`：長列兩邊各三筆短列，保留原來的小表連頁規則。
- `mixed-gaps`：短列缺幣別／經費來源／用途／支援項目，長列也缺幣別；
  保留明確填入的 0 與 900，不以空值或推論取代。

原生匯出本輪涵蓋 `mixed-long-last`、`mixed-gaps`，各兩種語言與兩種輸出模式，
共 24 份 HTML／PDF／DOCX。其餘排列與列數上限另有結構測試，沒有宣稱全部
都做過原生排版驗收。完整結果見 [混合預算檢查](../../reviews/2026-09-18-mixed-budget/README.md)。

重建資料至新目錄：

```sh
../dsw-document-template-tool/.venv/bin/python scripts/generate_mixed_budget_fixtures.py \
  --english ../science-europe-template --output outputs/mixed-budget-fixtures-new
```

KM 是鎖定英文 checkout 內公開模型的副本，不重複提交；`provenance.json`
保留模型與來源雜湊。產生器不覆寫既有目錄，也不修改英文 repo。
原生測試器可用 `--fixtures outputs/mixed-budget-fixtures-new` 指定這批資料。

`rehearse_mixed_budget.py` 先重建既有 PDF 路徑，再只在混合預算的普通表格分組
試加既有短列連頁屬性；不變動長列、內容、CSS、字型或 Word。
**離線 A/B PDF 不是新版模板的 DSW 原生輸出。**
