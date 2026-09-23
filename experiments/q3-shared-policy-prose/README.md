# 第 3 題固定政策段落共用接句原型

正式版本維持 0.3.50，不修改 `pipeline.yml`。本輪從仍為 0.3.50 的來源
另開短期 `feat/q3-shared-policy-prose` 分支，保留上一輪未採用方案的證據。
`lock.json` 鎖定英文原型完整 commit；不是另一份手工維護的中文 Jinja。

英文 recipe 只在 Q3 擷取 metadata-policy 片段、加一份純結構 helper。
只有整段恰好是 2–3 個純文字固定段落時才組成一段；資料字典的
`data-fact-id` / `data-status` 改放 span，文字、狀態及順序均保留。
中文句號接漢字時不另外加空格，英文或混合邊界仍保留一個空格。
HTML/PDF/Word 因此共用同一份明確的接句結果。

只要含使用者原文、漏填提示、複雜標記／實體字元、不認得的屬性、重複字典
事實或不完整句子，整個片段原樣回退。原有缺漏處理和提交版題目不變。
CSS、Lua、Word 樣式、字型和 775 份翻譯檔都必須逐位元不變。

```sh
python experiments/q3-shared-policy-prose/build_prototype.py \
  --english ../science-europe-template \
  --tooling ../dsw-document-template-tool \
  --baseline outputs/build-aphphgpw \
  --output outputs/q3-shared-prose-prototype-01
```

使用既有工具 venv；輸出目錄必須不存在。建置沿用鎖定的
expand/export/merge/sync/audit/TDK 流程，檢查實際套件只有已核准來源差異。
封裝後再用獨立 DOM oracle 跑中英文、漏填、正反回答、失效父層、原文標記、
兩個 profile 與 autoescape 的答案矩陣。不得以空白正規化隱藏原文差異。

原型套件有獨立 ID，尚非正式升版。另須測封裝 helper 經 PDF / Pandoc 的
中英邊界，以及缺漏／長原文／私人專案的離線完整 HTML、PDF、Word 與
LibreOffice 預覽；後者不等同 Microsoft Word 驗收。本輪不推送、不部署。
