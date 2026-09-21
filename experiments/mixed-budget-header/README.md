# 原生 PDF 輸入診斷與未升版試作

本實驗只供隔離的 `science-europe-pilot`、公開合成資料使用。
**不是新版模板，不修改正式站，不取用 keyring。**

## 原因與改動分開驗證

`capture.py` 包住已鎖定的 DSW `WeasyPrintStep.execute_follow`，原樣傳入同一份
document/context，記錄真正的 PDF-entry HTML、輸出 PDF、選項，以及長列
`all_groups_layout` 的表頭保留／省略路徑。不改 CSS、HTML、選項或引擎程式。
它只接受具有 60 個各出現一次的公開 `MIX-LONG-09-PARA` 標記之混合案例；
來源檔雜湊不符合即拒絕啟動。這個辨識是測試保護，不是通用匿名化工具。

原生中文檢核格式 UUID 會觸發工具既有的 CJK fallback／typography；HTML 格式
與中文提交格式不會觸發同一層。以前由 HTML 匯出重建的離線輸入因此不等價。
新重播先驗證 captured HTML 的全部 PDF 文字座標及字型與原生完全相同。

`prototype.py` 僅從精確鎖定的 0.3.42 套件產生另存的本機試作，修改兩個檔案：

1. `budget-reading.html.j2`：普通混合分組套用既有 4–32 列短列 helper；
   長列 tbody 設置 `break-inside: avoid`，測試目前引擎的保留表頭分支。
   長列仍跨頁，沒有把整份長回答或整張表鎖在單頁。
2. `layout.css`：只在 PDF 長資源表中，讓最後的用途片段與其後支援項目接續。

套件逐檔反向投影必須還原所有原欄位；題目、譯文、使用者文字、Word、字型
與格式 UUID 都不重寫。ZIP 只是試作，manifest 標為 `runtime-experiment`；
原始 repo、來源鎖與版本維持 0.3.42。不能拿它直接發布或覆寫既有版本。
若通過下一輪控制組，才把修正回收到英文來源、升版、走中文既有建置流程。

## 重建與清理

原生前後對照及限制見 [驗收紀錄](../../reviews/2026-09-21-native-mixed-header/README.md)。
`compose.capture.yml` 只可與指定 pilot 的 base Compose 搭配，且只用
`up -d --no-deps docworker` 重建 worker；不能套到其他 stack 或正式站。
兩個 `SE_HEADER_CAPTURE_*` 環境變數指定此 observer 與新的、只含合成資料的目錄。
資料庫／儲存服務用原容器 `docker start`；worker-only interpolation 的非秘密
placeholder 用法與 [tables 實驗](../markdown-tables/README.md) 相同。

`run_missing_info.py` 的兩個混合案例與兩模式共產生 24 份原生檔案。
Word 預覽須等原生批次完成後才啟動；不要與尚未產生最後兩份 DOCX 的批次競速。
`check_native_mixed_header.py` 比較原生輸入的精確允許差異、每列內容、頁面邊界、
續頁識別、尾句，以及 Word 正文／樣式／字型／連結／全部預覽頁的文字座標。
LibreOffice 的 PDF CreationDate 不屬於頁面座標；不以此誤判 Word 變動。

清理工具先確認自己的暫存模板沒有 project/document 引用並有 ZIP 備份；
`finish.py` 再移除 observer、還原 stock worker，最後只停止四個指定 pilot 服務。
本輪清理四個暫存模板，未移除 volume、其他模板或其他 stacks。

## 不重複存入大型字型

封存 HTML 把嵌入字型換成 SHA256 引用；它們不能直接當成瀏覽器預覽。
使用 `scripts/restore_captured_pdf_input.py --input … --font … --output …` 還原。
字型使用鎖定工具的 `resources/fonts/NotoSansTC-Variable.ttf`；必須通過整份
原始 HTML 雜湊，不只比較 DOM 或文字。`replay.py` 使用鎖定的 DSW conversion
step、無網路、唯讀 probe/source mount；試驗輸出只寫到指定目錄。

本輪的分組、tbody 與尾句策略只做限定原生驗證；尚未做全空、純長列、純多列、
更多混合順序、Microsoft Word 實機或任意真實專案的完整驗收。

## 後續基本控制組

`scripts/prepare_header_controls.py` 從鎖定 EN 測資複製全空、部分填答、八筆短列及
缺幣別長回答；另由 `budget-long` 僅移除尾端短資源，建立真正單筆的
`budget-single-long`。原來的 `budget-long` 有兩筆資源，不能冒充純長列測試。
所有資料仍由 `run_missing_info.py` 先核對本機 DSW 編譯後的 KM graph。

這批不使用只接受 MIX 標記的 observer：用 tables-only override 啟動 worker，
`prototype.py --without-capture` 明確記錄沒有擷取 PDF-entry HTML。
`check_header_controls.py` 直接比較原生 PDF、原生 Word 及新產生的 LibreOffice
預覽；不把 HTML 匯出重建成「原生」PDF，也不變更既有 observer 的安全範圍。
兩語言 × 兩模式 × 五案例，每個套件產生 60 個原生檔案、20 個 Word 預覽。

基準與試作必須依序執行，完成基準後先核對 ZIP 備份及零引用，再清除該兩個
暫存模板，避免本機配額累積。`finish.py --without-capture` 會核對 tables-only
映像、兩批四個模板清理收據，再還原 stock worker 並停止指定 pilot。

控制檢查不等於完整提交驗收：全空提交模式目前仍有系統提示。長列前／中、
三列分組及 32／33 列邊界的原生組合也須另外檢查，不能以本批代替。
