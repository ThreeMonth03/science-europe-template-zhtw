# Q5 連頁實驗：0.3.33 → 0.3.34

結論是**部分改善，仍未通過原生版面驗收**。四處原有跨頁已改善，但部分漏填
的中文 Word 仍把回答與限制說明拆在第 3／4 頁；不能發布為已驗收成品。
本輪不改回答、譯文、字級或 Science Europe 對應，不用 LLM 補寫缺答。

## 先看實際差異

下列位置依序為「題目、工作區政策、限制引言、限制 1、限制 2」的頁碼。

| 案例／格式 | 0.3.33 | 0.3.34 | 判定 |
| --- | --- | --- | --- |
| 不公開、原因漏填／中文 PDF | 3,3,4,4,4 | 4,4,4,4,4 | 改善 |
| 不公開、原因漏填／中文 Word | 3,3,3,4,4 | 4,4,4,4,4 | 改善 |
| 已填不公開原因／中文 PDF | 3,3,4,4,4 | 4,4,4,4,4 | 改善 |
| 後設資料完整／英文 PDF | 3,3,4,4,4 | 4,4,4,4,4 | 改善 |
| 部分漏填／中文 Word | 3,3,4,4,4 | 3,3,4,4,4 | **仍失敗** |

原先三個已記錄反例修好兩個；另兩項改善是在本輪完整比對中確認。

- 中文改善：[原生 PDF](after/native/metadata-private-chinese.pdf)、[原生 DOCX](after/native/metadata-private-chinese.docx)、[Word 預覽](after/word-preview/metadata-private-chinese.pdf)。
- 英文改善：[原生 PDF](after/native/metadata-complete-english.pdf)、[原生 DOCX](after/native/metadata-complete-english.docx)。
- 尚未解決：[中文原生 DOCX](after/native/metadata-partial-chinese.docx)、[第 3 頁](visual/after-word-metadata-partial-chinese-page3.png)、[第 4 頁](visual/after-word-metadata-partial-chinese-page4.png)。

## 檢查範圍與結果

十個合成案例：`metadata-dictionary`、`metadata-dictionary-no`、`metadata-partial`、
`metadata-private`、`metadata-private-text`、`metadata-complete`、`empty`、`negative`、
`storage-sharing`、`budget-long`，各含英文與中文。前後合計 120 份原生輸出
（HTML／PDF／DOCX 各 40 份）及 40 份 LibreOffice Word 預覽。50 張實際頁面
截圖含跨頁前後，並非只選修好的頁面。

[原生比對報告](after/storage-context-report.json) 明確分開兩類結果：

- 20 組內容／範圍檢查通過。正文 HTML DOM 只容許 Q5 新標記；PDF 比對忽略
  空白的正文、標點及生成清單符號。DOCX 在 Q5 外完整 XML 保留，Q5 只容許
  指定三段的樣式名稱變更，最後條列與下一題不連住；字型／樣式定義未改。
- 所有原生 PDF 及 Word 預覽頁數與前版相同。不適用短區塊規則的長／複雜／
  封存案例維持原版面。空白與否定回答的 18 個正文頁另外通過像素相同檢查。
- 原生分頁檢查仍失敗：`selected_checks_passed=false`、`pagination_checks_passed=false`，
  檢查程式完成所有案例後以非零狀態結束。不是略過反例取得綠燈。
- [256 組中英文 Q5 比對](probes/storage-context-scope.json) 保留所有既有合成問卷
  回答（含 autoescape 開／關）；744 個翻譯檔逐檔 byte-identical。
  Q2、Q3、Q11 既有邏輯與樣式範圍檢查也保留。
- 固定引擎對準備好的英文／中文套件，各通過 38 組 PDF 與 29 組 Word AST／XML
  檢查。這些檢查沒有實際執行 Microsoft Word，也沒有證明 LibreOffice 的連頁效果。
- 英文 190、中文 201 項單元測試通過。舊 Q13 準備版雜湊檢查曾漏扣本輪 Q5
  區塊；現以精確的新增區塊雜湊組合，保留原歷史門檻，13 組引擎案例重測通過。

## Word 反例與下一步

DOCX 已有正確的 `PilotLead`／`PilotListLead` 連頁樣式，仍不足以讓這份中文
Word 預覽的政策與限制說明同頁。[四份診斷副本](diagnostic-not-native/report.json)
分別直接加連頁、政策段不拆行、兩個引言段不拆行、四段不拆行，均仍分在 3／4 頁。
這些不是 DSW 原生輸出，也未修改模板；不能據此直接判定 Microsoft Word 或
LibreOffice 的根因。下一步縮減該完整文件反例、觀察排版器實際接受的段落
屬性，再決定如何修改。先不套全篇換頁或新增全域樣式。

人工查看中英文實際頁面可確認上述改善／失敗。封存案例保留原跨頁能力；
英文既有制式句型、中文句間空格和全篇段落密度，本輪沒有改文，仍需另做
整篇閱讀審查。這不是 15 題完整性或 Science Europe 認可的正式驗收。

## 版本與可重現性

英文與中文均在短期 `fix/q5-context-pagination` 分支；中文仍由既有翻譯流程
生成，不新增獨立中文 Jinja。`pipeline.yml` 鎖定英文 commit
`8528898c28e44f91d1b5a912261e51061f8c36a9`，工具為
`25e339fbdfb1d20796471055790aad6a4226b6ed`。

實際原生輸出取自乾淨候選 `bf4ffae9d23742418be479be41e4b93a80bb1a35` 的英文
來源及中文 `f81e4a7e2b6f6135c032d98d1126664dc7dca449`。後續英文只修測試與說明；
中文只補驗證、版本鎖定及證據。清潔重建的兩個 ZIP 與實際產出所用 ZIP 相同：

| 0.3.34 ZIP | SHA256 |
| --- | --- |
| 英文 | `b9160cf57ae8fc71133f553c33750742c9c5f4f8bf708e460ef34f948af67327` |
| 中文 | `ef62084229f46009e1929c3fe8e4a6632694db5aafa8b0545708fd9d103ee704` |

`candidate-manifest.json`、`rebuild-manifest.json` 與逐份 fixture receipts 分開
保存，不混稱所有輸出來自最後一個 commit。0.3.33 的兩組基線使用同樣的兩個
舊 ZIP；主組 48 份，封存／長預算補組 12 份。所有 Word 預覽都核對原生 DOCX
及 PDF 預覽雜湊。`question-content/` 是從原生 HTML 擷取的正文 DOM，附原始
HTML SHA256；不存入龐大的內嵌字型 HTML，不把該擷取檔冒稱原生完整 HTML。

僅使用本機公開合成問卷。60 份新版輸出期間 tables-only worker 的映像、
啟動時間及重啟計數相同；測後恢復原 stock worker，四個容器已停止，未刪 volume。
兩批本輪測試各兩個無引用的暫存模板記錄已刪除，ZIP 備份保留可重建。
未用正式站憑證、未改正式 project、未合併分支、未加 tag 或發布。

`reproduce/` 保存本輪檢查程式，仍需上述兩個 repo、鎖定工具與其既有檢查依賴，
不是獨立可執行套件。所有本目錄檔案雜湊列於 `checksums.json`。
CI 僅是建置／引擎門檻，已知原生 Word 失敗也明列於 CI 摘要；即使 CI 綠燈，
本輪版面驗收仍是未通過。
