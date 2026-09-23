# 中文標點診斷：兩個假設被排除，正式版仍為 0.3.50

本輪是診斷與反例驗證，**不是排版修正的正式整合或發布**。
正式英文來源仍鎖定 `a2f97d9312b4ce811b92f5943944997638cc67b8`；中文
`pipeline.yml`、775 份翻譯、字型、CSS、Word 資產和原有版本號都不變。
未推送、未部署，未使用帳密或 DSW API，也沒有本輪私人專案重播。

## 結論

| 假設 | 實際檢查 | 決定 |
| --- | --- | --- |
| Q3 固定句子清單仍以英文空格連接 | 實際中文 ZIP 已是 `join("")`；既有工具的 `output_polish.py` 處理過了。改英文 Jinja 不會改善成品。 | 不整合這個 recipe。 |
| 直接把 Q13 的 CSS / Lua 去空格例外擴到 Q3 即可 | 固定中文案例可移除插入空格；但下一句以 `W3C PROV` 開頭時，CSS 會去空格，Word 邊界檢查則保留。 | 拒絕這個不一致的簡化修法。 |
| `）。` 看起來鬆散表示文字裡有空格 | 合成樣本是 U+FF09 緊接 U+3002；字型兩個字元的 advance 都是 1000 units（1 em）。 | 把字型設計與文字空白分開處理。 |
| 加 `chws` 就能處理相鄰標點 | 實際字型沒有這項 feature；固定 worker 的 7 組樣本，文字、寬度、高度都與 normal 相同。 | 不加無效設定。 |

`halt` / `palt` 確實改變部分標點與混合文字的寬度，但本輪沒有選用它們，
也沒有換字型。可直接比較 [合成標點樣本 PDF](font-lab/samples.pdf)：
normal、chws、halt、palt 各一頁；這不是專案文件，不含私人資料。
人工查看了 normal / halt / palt 三頁；chws 的無效結果另由逐樣本文字和幾何檢查確認。

## 驗證方式與範圍

1. 先保留第一輪「至少應有改善」檢查失敗的紀錄，不把成功產檔當成改善。
2. 後續以兩次乾淨的 EN → ZH expand/export/merge/sync/TDK 建置重現：
   每語 6,378 組實際封裝後的答案比較相同（5,982 組 Q3、396 組完整文件）；
   中文舊套件已正確接句。
   每語矩陣包含缺漏、未知值、失效父層下的殘留答案、兩種輸出模式及預設回退、
   autoescape 開關、使用者空格／標點／連結，以及既有完整文件 fixtures。
3. 775 份翻譯檔逐位元不變；原型除單一 Q3 source、獨立識別碼及衍生 UUID 外，
   不允許格式步驟、CSS、字型、Word 資產或其他內容變動。套件標記為
   `rejected-no-benefit`，不是可交付新版。
4. 另以 6 組合成案例測量 CSS / Pandoc 的段落邊界。Word 比較 AST 與含樣式的
   逐字序列，僅允許指定邊界的一個新增空格消失；其他空格、標點、樣式變更
   都有反例測試。混合語言案例的不一致是預期捕捉到的缺陷，不是驗收通過。

字型檢查與段落邊界檢查使用固定 worker
`sha256:6d3cbcab3294e760a4d92e27bec72d4fb23a0adb2cc1734d981478688741ab11`
（WeasyPrint 68.1 / Pandoc 3.8.3），在無網路容器內執行。
所有本輪測試數量、來源 commit、兩次套件雜湊與失敗紀錄摘要見 `summary.json`。
本機測試不等同 GitHub Actions；合成 Pandoc Word 檢查不等同 Microsoft Word
或 LibreOffice 整份文件的視覺驗收。本輪沒有重跑先前 54 項完整整合 workflow。

## 下一步：共用接句決策，不再讓兩個輸出各猜一次

下一個小改動應從固定政策段落的共同來源處決定邊界：哪些固定中文敘述可
接續、哪些英文開頭需保留空格、哪些使用者段落或漏填提示必須維持結構。
兩個 renderer 使用同一份決策，仍走既有 EN → ZH pipeline。
先用本輪反例卡住回歸，再跑缺漏／正反回答／長原文的中英文 PDF + Word
實際套件與私人離線全文比較，才能考慮配對升版。

版本管理上，這兩個未採用方案只留在短期 `feat/cjk-punctuation-probe`
分支和封存證據，不加入正式 source 或翻譯維護負擔。後續可從乾淨 0.3.50
另開實作分支；只整合通過驗證的最小變更，中文再鎖完整英文 commit。

字型與排版背景參考：[W3C 中文排版需求草案](https://www.w3.org/TR/2026/DNOTE-clreq-20260901/)
討論全形標點保留字寬與依情境調整的不同作法（不是一律應壓縮的規定）；
Microsoft 說明 [chws](https://learn.microsoft.com/en-us/typography/opentype/spec/features_ae#tag-chws)
與 [halt](https://learn.microsoft.com/en-us/typography/opentype/spec/features_fj#tag-halt)
的情境式／非情境式差別。本輪結論以鎖定字型與 renderer 的實測為準。
