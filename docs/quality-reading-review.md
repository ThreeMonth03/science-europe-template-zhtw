# 0.3.2：品質管控段落與句號

2026-09-14。本機隔離環境的合成資料實驗；尚未發布或部署至線上 DSW。
英文仍衍生自官方 Science Europe 1.30.1，六節十五題維持不變。
以下連結以本文件複製到的 review 目錄為準。

## 樣張

- [中文 PDF：原有回答、修改後段落](tables/structured-chinese.pdf)
- [同份 Word](tables/structured-chinese.docx)
- [Word 的 LibreOffice 預覽](tables/word-preview/structured-chinese.pdf)
- [七項措施、第二資料集及長文反例](tables/quality-rich-chinese.pdf)
- [部分缺答](tables/quality-partial-chinese.pdf)
- [原版 worker 的對照 PDF](stock/structured-chinese.pdf)
- [只填封存時，Q8／Q14 顯示待補](stock/archive-only-chinese.pdf)

`tables/` 使用前輪的獨立 Markdown 表格實驗 worker。修模板本身不會解決
原版 worker 不支援自由回答 Markdown 表格的問題；兩組使用完全相同套件。
樣張不是已完成、可直接照抄的正式 DMP。

## 問題與修改

使用者指出的 Q4 在原本 HTML 就是「外層資料集清單 → 一句引言 → 內層
措施清單」。中文「資料輸入檢核。」的翻譯單位又帶句號，其他措施卻沒有。
這兩個問題不是 PDF parsing 才產生。

進一步以 0.3.1 expanded source 重跑抽取，確認普通項目的 source unit 是
`calibrating measurements`，斜體項目卻是整個
`<li><em>Data Entry</em> validation</li>`。工具保留混合 inline markup，
接著 `extract_sentence_text` 把 `</li>` 當作句界補上 `.`，因此翻譯介面
實際顯示 `Data Entry validation.`，中文也帶入句號。這是 HTML → 翻譯
單位的解析／編修交互問題，不能只歸因於中文譯者。現版本的純文字措施
避開該路徑；工具的通用抽取規則未修改，其他題目仍須另查同類情況。

現在該段呈現為：

> 沿岸水溫觀測資料：品質管控措施包括校正量測結果、資料輸入檢核。

- 固定措施用短語，完整句的句號由外層管理；中文措施之間使用頓號。
- Q4 每個資料集是一個段落，不再用資料集／引言／措施的巢狀清單。
  Q1 同一段內容與 Q4 共用英文 `src/quality-control.html.j2`，避免兩份
  條件判斷日後修到不一致。這次仍保留兩題中的品質內容，沒有隱藏重複資訊。
- 沿用既有翻譯樹與已支援的 `join(", ")` 中文在地化。曾試驗一般連接片段，
  確認工具會略過僅含連接詞／符號的片段後，改用現成能力；最終工具 commit
  完全未改，沒有另一套中文 Jinja、runtime LLM 或全文件標點取代。
- 自行填寫的其他品質措施獨立以 Markdown 呈現，保留段落、清單、版本號
  及小數點。只有其他措施有內容時，不再同時宣稱「方法尚未提供」。
  勾選其他但漏填細節、品質管控是否採用未填、明確選 No，分別處理。
- Q8／Q14 沒有可呈現內容時補上個別提示，避免只有題目。提示說的是
  「本文件尚未呈現」，不武斷認定使用者沒有填問卷，也不推論法律結論。

這次沒有縮小字級、改全域段距、修改 PDF CSS／Word Lua 或改用硬性分頁。
固定短措施是真正的 HTML／Word 段落，而不只是隱藏清單符號的視覺效果。

## 驗證紀錄

建置來源：英文 `85943cbae84afe97baff74f48d0fb8f47d55aa00`；中文
`75624df7a82980c653743cec86cf31b78e92abd6`；工具
`25e339fbdfb1d20796471055790aad6a4226b6ed`。中英版號均為 0.3.2。
官方 baseline 仍為 `22d60aae4b63ee677477ac0c73097807284aaf9f`／1.30.1。

英文 49 項、中文流程 26 項單元測試通過；641 個翻譯單位，空白 0，
翻譯與結構稽核均無違規。局部 Jinja probe 額外驗證 128 種已選／未選
措施組合 × Q1／Q4 × 中英，共 512 次；這不是 512 份實際 DSW 文件。
所有 fixture 路徑經 compiled 中英 Common KM 2.7.0 驗證可到達。
靜態 binding audit 改為涵蓋全部 30 個 src Jinja 檔，包含共用 helper，
未定義引用與不存在實體均為 0；靜態存在不等於完整答案涵蓋率。

原版 worker 共九案例 × 兩語言 × 三格式，54 份全部生成成功，指定語意
檢查通過。仍有 24 筆已知表格阻擋紀錄（六個含表格案例 × 兩語言 ×
HTML 表格／Word 可編輯表格兩類），`pilot-report.passed` 為 false，
runner 回傳 2，沒有當成可發布結果。

新的 quality checker 通過 18 個案例／語言配對。與 0.3.1 的七個相同
輸入案例比較，驗證 recipe／events／KM 雜湊相同，再通過 196 項控制比較：
Q2–Q15 除 Q4 外文字不變，Q8／Q14 只允許預先宣告的空輸出提示；Q1
僅排除已知的儀器品質尾段，其餘內容不變。Q4 則直接核對預期措施、順序、
完整句與 Word 段落數，並非無條件忽略所有 Q1／Q4 差異。舊 storage
checker 的六個配對與 narrative checker 的十個配對亦通過；沒有套用
其舊版逐題比較規則，因為那套規則不包含本輪 Q1／Q4 的合理改動。

表格實驗 worker 使用相同 ZIP，對 structured、quality-rich、quality-partial
三案例產生 18 份文件；指定語意及表格檢查通過。quality checker 六個
配對通過，並與同 worker 的 0.3.1 structured 比較通過 28 項控制檢查。
兩種 worker 的六個案例／語言配對，套件、recipe、events、KM 雜湊相同，
十五題 fact markers 一致，Q2–Q15 文字忽略空白後一致，Q1 表格儲存格
內容保留。這不是 Q1 全文等價證明，也不是完整版面驗收。

長文案例在 Q1／Q4 各保留二十個獨立段落，三格式皆可抽取四十次測試句，
Word 也實際保留四十個段落；並核對另外兩段正文、兩個清單項目及原始
版本號／小數。部分缺答案例的三種提示在三格式都存在，不會變成明確 No。
Q8／Q14 在 empty／archive-only 中均有可見提示，不再只剩題目。

## 視覺審閱與尚未通過的版面項目

兩種 worker 的中文 structured 都是 PDF 六頁、LibreOffice Word 預覽七頁；
quality-rich 為八／九頁，quality-partial 為六／七頁。原版 archive-only
為四／四頁。所有被 quality checker 檢查的 PDF，及七份 Word 預覽，
文字框均在紙張邊界內；這不能證明沒有重疊、留白適當或整體好讀。

已人工看過原版 structured PDF 第三頁、Word 預覽第三頁；rich PDF
第四頁、Word 第五頁；partial PDF 第三頁；archive-only PDF 第二至四頁。
另看表格實驗組 structured PDF 第三頁、Word 第三／四頁，以及 rich
PDF 第四頁、Word 第五頁。短措施沒有巢狀清單，七項措施能連續排文，
自由回答保留清單與段落，長內容可跨頁；不是強制整題同頁。

**這版整體視覺驗收仍不通過。** 除原版 worker 的既知表格問題外，
表格實驗組 structured 的小型溯源表格出現分頁退步：0.3.1 的兩個資料列
都在第三頁，0.3.2 的「處理紀錄」在第二頁、「來源校驗碼」在第三頁，
並重複表頭。改短前文會移動後文分頁，僅檢查文字／儲存格保留抓不到
這件事。下一輪須加入有界限的短表格同頁規則及分頁回歸，不應全面禁止
長表格跨頁。此處清楚保留問題樣張，沒有挑頁隱藏或稱已完成排版。

## 範圍與下一步

本輪只完成已列出的段落與缺答修正，不能宣稱全文標點／語氣與所有分支
都已驗收。Q2／Q3 等仍有較碎的固定敘述；後續應逐題整理成合理的閱讀
單位，不應全域刪換行或合併使用者段落。

Q8／Q14 現在保證空輸出有提示，但只填一個法律面向、只有部分參與人員
有可映射角色時，仍未逐項指出所有不足。Science Europe 題目存在不代表
答案充分。Q1／Q4 重複內容、所有再利用資料的品質管控對應、全文中文
編修及 Microsoft Word 實際分頁，仍是後續工作。新增的第二資料集反例也
顯示 Q2 在缺少蒐集者／設備細節時，仍可能只列資料集名稱，須另補提示。

中英 repo 使用短期 `feat/quality-reading` 分支，版本對應靠 commit lock，
不是另開永久的 0.3.2 branch。英文 Q4 與共用 helper 已列為 upstream
critical overlap；升級要核對來源回答、提示及雙語輸出，不只是解 Git 衝突。
沒有變更官方 baseline、合併主線、建立 release tag 或覆寫既有樣張。

報告／測試程式可以在套件建置後提交；套件來源以上述 checkpoint 為準，
檢查程式另以報告 SHA-256 識別。本機完整 HTML／ZIP 留在 outputs；review
封存精簡 PDF／DOCX、LibreOffice 預覽、來源指紋與驗證報告。

## 重跑及環境狀態

本機原版建置：`outputs/build-i8o2vf6b`；表格實驗組：
`outputs/runtime-tables-klu9hu6b`。兩組都是同一對 ZIP：

- 英文 SHA-256：`1586bcd282634d0776e2bc629c8f176fc3fa2dfd3556faccf2769568f0718ef1`
- 中文 SHA-256：`97269459d2a4517512254f20cee259e69f308c4859586cfbbfae2897811955a1`

```sh
../dsw-document-template-tool/.venv/bin/python scripts/probe_quality_translation.py --build BUILD --english ../science-europe-template
../dsw-document-template-tool/.venv/bin/python scripts/check_quality_outputs.py --build BUILD --prior PRIOR_031 --cases structured storage-sharing storage-sharing-partial archive-only narrative-long quality-rich quality-partial empty negative
../dsw-document-template-tool/.venv/bin/python scripts/check_storage_sharing_outputs.py --build BUILD
../dsw-document-template-tool/.venv/bin/python scripts/check_narrative_outputs.py --build BUILD
```

表格實驗組的 quality checker 僅使用 `structured quality-rich quality-partial`，
prior 指向同 worker 的 0.3.1；兩種 worker 比較亦使用這三案例。
樣張封存命令（既有目的目錄不覆寫）：

```sh
../dsw-document-template-tool/.venv/bin/python scripts/collect_quality_review.py \
  --baseline outputs/build-i8o2vf6b --variant outputs/runtime-tables-klu9hu6b \
  --destination reviews/2026-09-14-quality-reading \
  --review-document docs/quality-reading-review.md
```

已將 docworker 恢復為原版 4.30，映像
`sha256:5e5c5e1e436feb49fc4cbcd62c2e0ab2785db2141b0fe40d2926906bcfeaebfc`，
本機 postgres、minio、server、docworker 四項服務均停回原狀，containers／
volumes 保留。本輪沒有使用 keyring、讀寫真實專案或部署線上服務。
