# 0.3.4 格式與容量審閱（2026-09-14）

本文件同時作為 `reviews/2026-09-14-format-volume/README.md` 的封存內容；
以下樣張連結以該封存目錄為基準。這是實驗結果，不是正式發布或完整 DMP 驗收。

## 先看成品

表格修補 worker 的同套件實驗（仍非 production）：

- 一般案例：[中文 PDF](tables/structured-chinese.pdf)、[可編輯 Word](tables/structured-chinese.docx)。
- 自由回答與微小容量：[中文 PDF](tables/format-rich-chinese.pdf)、[Word](tables/format-rich-chinese.docx)。
- 部分缺答及零值：[中文 PDF](tables/format-partial-chinese.pdf)、[Word](tables/format-partial-chinese.docx)。
- 一般英文對照：[PDF](tables/structured-english.pdf)、[Word](tables/structured-english.docx)。

原版 worker 的對照：

- [一般中文 PDF](stock/structured-chinese.pdf)、[Word](stock/structured-chinese.docx)。
- [自由回答 PDF](stock/format-rich-chinese.pdf)、[Word](stock/format-rich-chinese.docx)。
- [部分缺答 PDF](stock/format-partial-chinese.pdf)、[Word](stock/format-partial-chinese.docx)。
- [全空回答 PDF](stock/empty-chinese.pdf)、[Word](stock/empty-chinese.docx)。

## 本輪改了什麼

Q2 每個格式的固定說明排成一個閱讀段落，不再以「格式名稱的外層項目符號」
另接零碎段落。採用現有 PDF CSS 與 Word Lua 合段規則，沒有修改全域排版或 worker。
自由回答仍保留原本 Markdown 段落與清單；取消 `capitalize` 與尾端強加句號，
因此 `JSON`、`CSV`、`MyInstrument v1.2`、`station_YYYYMMDD.csv` 不會被改寫。

已選「非標準化格式」或「不適合長期封存」時，即使理由／轉換計畫漏填，
已知決定仍會輸出。明確不規劃轉換與尚未回答分開呈現。缺答合在另一個提示段落，
不混成已經承諾的措施。

檔案數與平均大小各自保留；案例包括只填 `12` 個檔案、只填 `0.25 GB`、
檔案數 `0`、平均大小 `0 GB`。直接填寫的總量 `120 GB` 仍輸出。
不再用 `int × float` 並四捨五入至兩位來猜總量；兩個 `0.0001 GB` 的檔案
不應被寫成 `0.0 GB`。這是取消不可靠的衍生數字，並非移除使用者填寫的欄位。
模板本身不負責驗證所有不合法數字輸入，亦不會把它們默默改成零。

## 驗證證據

- 英文 61 項測試及 TDK verify 通過；中文 34 項測試通過。
- 新增 76 組格式／容量雙語離線 probe；另重跑 24 組蒐集方式及 512 組品質措施 probe。
  這些是本機回覆 adapter 的分支檢查，不是 612 次 DSW 產檔。
- 共 655 翻譯單位，空白翻譯 0，翻譯／結構 audit 無錯誤。
- 新 fixture 通過本機 DSW 編譯的英中 Common KM 2.7.0 路徑檢查；30 個 Jinja
  檔案的靜態 binding audit 未發現未定義變數或不存在的實體。此檢查不等同題目內容完整率。
- 原版 worker：5 案例 × 2 語言 × HTML/PDF/DOCX = 30 份產檔成功。
  語意檢查通過，但 3 個含表格案例仍有 12 項既知表格阻擋，整體 acceptance 為 false。
- 表格修補 worker：3 案例 × 2 語言 × 3 格式 = 18 份產檔成功，所選語意／表格檢查通過。
  兩種 worker 使用逐位元相同的英中 ZIP；6 組案例語言比較確認相同輸入、15 題標記、
  Q2–Q15 文字與 Q1 表格儲存格內容保留。不是 Q1 全部散文的逐字等價證明。
- 和 0.3.3 相同輸入的比對：原版 90、表格版 30 個題目比較通過。
  只排除 Q2 明確識別的格式區塊，不排除整題 Q2；蒐集方式及其餘 14 題不得改變。
  新 `format-rich`／`format-partial` 沒有 0.3.3 同名輸出，不列入這個比較數。
- Q2 每個格式的固定敘述在 DOCX 中確為單一段落；理由的兩段及兩個清單項目仍獨立。
  PDF／DOCX 的已知文字、數字、缺答標記有對應，所有本輪 PDF 與 8 份 LibreOffice
  Word 預覽的文字座標均未超出頁面。這不代表每頁都完成人工審美驗收。
- 先前修正的短溯源表格，在本輪所有表格案例的 PDF 中仍同頁；有 Word 預覽的
  案例也同頁。一般英中案例的兩列在 PDF 與 Word 預覽皆為第 3 頁。
  本輪沒有重跑 48 列長表案例；其先前證據仍保留於 0.3.3 封存。

Q2 格式區塊檢查及受控比較見 `format-report.json`；`reading-report.json`
與 `quality-report.json` 本輪只做輸出檢查，沒有使用其舊版本專用的 `--prior` 比較。

## 頁數及人工觀察

| 中文案例 | 原版 PDF／Word 預覽 | 表格版 PDF／Word 預覽 |
|---|---|---|
| 一般案例 | 6／7 | 6／7 |
| 自由回答／微小容量 | 6／7 | 6／7 |
| 部分缺答／零值 | 6／7 | 6／8 |

已人工檢視部分 Q2 頁面、英文缺答案例，以及表格版一般中文 PDF／Word 第 3 頁。
固定敘述已較連續，並未用刪減回答換取較少頁數；缺答案例的 Word 在加入真表格後
仍多出一頁，不能只用「頁數變少」當成功標準。

保留以下待修項目，不把它們視為已驗收：

1. 多項缺答時，中文「尚待補充」重複過多，整塊提示仍顯得笨重。
2. PDF 的數字與 `GB` 偶爾分行，宜以局部的不換行單位處理，並同步驗證 Word。
3. Q10 等區塊仍有短行偏多及整份語氣不一致的空間；本輪沒有擴大改寫所有題目。
4. 原版 worker 的 Markdown 表格尚未修復；表格版仍是隔離實驗，不是上線方案。
5. LibreOffice 預覽不等同實際 Microsoft Word；仍需目標 Word 環境驗收。

本輪還排除了 parsing 假警報：預設 `pdftotext` 會把行尾 `long-` 接下一行 `term`
擷取成 `longterm`，但實際 PDF 保有連字號。檢查器改用 `-layout` 並補測試，
沒有抹掉所有連字號或大小寫來放寬比較。

## 版本、CI 與回復

英中工作分支均為 `feat/format-volume-reading`，承接 0.3.3 的 CI 修正。
英文來源 `33021b691cabfd53ce4c979b952c1c36e79e7058`；中文實際產檔 checkpoint
`6d52e278e927bed493dace047ffa11b152309895`；工具仍鎖定
`25e339fbdfb1d20796471055790aad6a4226b6ed`。後續檢查器／封存文件提交不是另一次模板改寫。
官方基底仍是 `1.30.1 / 22d60aae4b63ee677477ac0c73097807284aaf9f`。
Q2 在 upstream 的 critical 重疊清單內；未來升級須審閱語意及這些反例，不能只看 Git 衝突。

英文 ZIP：`bdd35e614d8393c4205eb7649e7e8cb429278dedae9fd3256d12387b59cc632d`。
中文 ZIP：`eeb7fdbc0d81b442e4fa32b605fd9f89ce9ead48e24dff8eb4dbb3415e6e88a4`。

本機原版建置為 `outputs/build-n64y5gea`，表格實驗為 `outputs/runtime-tables-jzcfk0v1`。
未覆寫任何舊樣張、未合併主線、未建立 tag／release、未 stage 或部署到線上 DSW。
本機 worker 已恢復原版映像並停止整個 pilot；未使用線上憑證或改動線上 project。

CI 的 bs4 缺漏已修復並在 GitHub 重跑通過，中文 CI 現在先用獨立 venv 檢查英文。
工具 repo 的 master 每日排程另有 MinIO 拉取失敗，本輪沒有宣稱修復它；
詳見 repo 的 `docs/ci-repair-2026-09-14.md`。
