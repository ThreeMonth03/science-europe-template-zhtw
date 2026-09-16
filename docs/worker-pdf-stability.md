# 0.3.25 worker exit 139：隔離診斷，尚未證明根因

本輪沒有修改英中模板、731 個譯文、套件版本或線上 DSW。英文仍鎖定
`574890c3f927007a3879116a9363d243675ac13c`；中文工作分支另開
`fix/worker-pdf-stability`。這是執行引擎的診斷，不是 0.3.26 成品驗收。

## 已知與未知

上輪本機 worker 完成 41 個輸出後 exit 139，`OOMKilled=false`；同一映像
重啟後完成最後一份 DOCX。留存的狀態不足以判斷是在 PDF 字型回收、下個
工作或其他階段出錯；舊容器完整 stack trace 沒有保存。不能把 exit 139
直接歸因於模板，也不能因重新渲染成功就宣稱已修好。

現用 worker 的 WeasyPrint 68.1 原始碼包含兩個上游已修正的字型 ownership
問題：[HarfBuzz face 的生命週期](https://github.com/Kozea/WeasyPrint/pull/2799)
與 [Fontconfig 的 double unref](https://github.com/Kozea/WeasyPrint/issues/2843)。
它們是合理的待驗證方向，不是已證明的本機當機原因。另一個 generic
`@font-face` 名稱問題不符合我們使用自訂 `Pilot CJK` family 的條件。

因此只做兩個有來源 hash 保護的最小修補，不直接升級到包含其他排版改動的
新版 WeasyPrint。實驗映像保留原本 Markdown tables 修補；原 stock 與
tables-only 映像不被覆蓋。完整修補範圍及上游 commits 見
[實驗說明](../experiments/worker-pdf-stability/README.md)。

## 實際結果

| 測試 | 原版／tables-only | 字型修補實驗 |
| --- | --- | --- |
| 中文多筆預算，自然 GC | 12 次，未當機 | 未做此組 |
| 中文多筆預算，每次強制 GC | 12 次，未當機 | 未做此組 |
| 七案例 × 英中 × 2 輪，每次強制 GC | 28 份 PDF，未當機 | 28 份 PDF，未當機 |
| 主動釋放 Pango owners 後再 subset | 10 次，未當機 | 10 次，未當機 |

合計 80 次 PDF 轉換、20 次專項字型測試，**沒有重現歷史當機**。不能據此
估算改善率，也不能宣稱修補版比原版可靠。

混合案例為全空白、明確否定、部分漏填、完整個資移轉、長預算缺幣別、混合
預算缺口及多筆預算。28 組前後對照、共 188 對頁面的文字／標點／座標、
頁面尺寸、URL annotations、字型清單及逐頁 96 dpi PNG 完全一致。
這個結果支持「目前所測案例沒有版面回歸」，不代表整體 DMP 內容合格。

重要限制：這些輸入是上輪的**HTML 格式輸出**，由真實 DSW `WeasyPrintStep`
轉 PDF，並不是擷取的原生 PDF 入口 HTML，也沒有經過完整原生工作佇列。
例如本輪 partial 中文為 5 頁，上輪原生 0.3.25 為 4 頁；原因是 HTML 匯出
沒有 PDF 專用 class，不能把診斷樣張當成新的正式成品或排版倒退。
Word 本輪沒有重產，也沒有新增 Microsoft Word 驗收。

第一輪兩個 stock 探針的 Fontconfig cache 不可寫警告保留；後續兩版都使用
相同的 `/tmp/cache`，stderr 皆為空。初輪工具快照與後輪工具快照分開保留，
不能把不同 cache 條件當作同一對照實驗。

## 可追溯與維護方式

[封存證據](../reviews/2026-09-16-worker-pdf-stability/) 保存六組原始報告、stdout／
stderr、PDF 樣張、逐頁比對、輸入壓縮檔、上輪 incident 紀錄及工具快照。
`checksums.json` 涵蓋封存證據；合成 HTML／字型解壓後可用
`provenance.json` 的雜湊核對。沒有帳密、keyring 或私有 runtime 設定。

`prepare_runtime_variant.py` 現在同時核對 worker Markdown、WeasyPrint fonts
與 ffi 原始碼，會拒絕把字型修補映像標成「只改 Markdown tables」。這是為了
避免不同 runtime 共用同一驗收標籤；不是把新映像偷偷放入現有流程。
本機四個 pilot 服務保持停止，docworker 仍指向 stock digest。

長期將四層分開：官方 DT 基底、客製英文／中文套件、翻譯工具、執行引擎。
這次只動引擎實驗及驗證工具，不增加英中模板版本或永久語言分支。
未來 worker 上游更新時，先核對依賴／來源，已包含的修補應刪除；hash 不符
必須停下來審閱，不能機械套補丁。新版引擎另跑原生成品矩陣，不能因模板
ZIP 一樣就沿用舊的 PDF 驗收。這個 backport 也不是 68.1 的安全支援承諾。

## 下一步

1. 在採用字型修補前，建立明確命名的 runtime variant，開啟 faulthandler，
   用相同 ZIP 跑完整原生 HTML／PDF／DOCX 佇列及較長回放。若再失敗，
   先保留 traceback、當前工作、映像及來源 hash，再恢復，不覆蓋事故證據。
2. 不等待偶發當機的無限重現才處理閱讀品質。Word 短預算缺答折行仍是下一個
   模板切片；另開模板修改，與這個引擎實驗分開比較，避免混淆原因。
3. 維持正式發布門檻：未完成真實代表案例、Science Europe 內容及實際
   Microsoft Word 驗收前，不將實驗結果稱為可正式發布。
