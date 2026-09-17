# Science Europe 客製繁體中文模板

這個 repo 翻譯 `ThreeMonth03/science-europe-template` 的客製英文模板。
原有 `depositar/science-europe-template-zh_Hant` 仍對應官方英文來源。

目前 0.3.35：[Q5 Word 固定說明合段實驗](docs/q5-word-join.md)。
只在英文共用 Word 邏輯中合併兩個合格的固定說明段，以換行分隔；
HTML／PDF、744 個翻譯檔及樣式不變。結構檢查與原生成品驗收分開，仍非正式版。

前版 0.3.34：[Q5 短回答與限制說明連頁](docs/storage-context-pagination.md)。
針對前版三個跨頁反例，只調整有界區塊的 PDF／Word 分頁，保留 744 個翻譯檔。
[前後樣張與失敗證據](reviews/2026-09-17-storage-context-pagination/README.md)：
120 份原生輸出及 40 份 Word 預覽完成比較，全文保留、頁數不變，四處跨頁改善；
但部分漏填的中文 Word 仍有一處分離，原生版面檢查仍失敗，不可正式發布。

後續 [Word 匯入／重排診斷](docs/word-import-layout.md)：重新指定政策段設定
只能暫時恢復同頁，另存重開仍失敗；第二引擎讓十份中文案例各多一頁，未採用。
本輪只加診斷工具與證據，英文來源、譯文及 0.3.34 套件版號均不變。
已加入 [Q1–Q5 縮減反例](reviews/2026-09-17-word-layout-reduction/README.md)：
中文縮為四頁仍重現跨頁，英文縮為三頁仍正常；保留節點 XML 與前文座標均核對相同。
另更正 `reformat()` 並非完整重排的說明；目前仍沒有可交付的分頁修正。

前版 0.3.33：[Q3 資料字典與後設資料追問](docs/metadata-followups.md)。
補回資料字典是／否，分別呈現公開政策的缺答；保留已填原因與原有樣式。
原有 735 組譯文全保留、新增 9 組。
[前後樣張與未解反例](reviews/2026-09-17-metadata-followups/README.md)：
96 份原生輸出、32 份 Word 預覽通過限定內容檢查、頁數不增加；
該版新發現 3 個中文 Q5 跨頁反例；0.3.34 修好其中 2 個，另 1 個仍未解。

前版 0.3.32：[Q3 儲存容量漏填實驗](docs/storage-capacity-gaps.md)。
選了填寫總容量但留空時顯示待補提示，已填 0、數值及其他回答保留。
只有英文 Q3 邏輯變更，中文循既有流程產生；不改共用 PDF／Word 樣式。
[前後 PDF／Word 樣張與限制](reviews/2026-09-17-storage-capacity-gaps/README.md)：
前後共 72 份原生輸出及 24 份 Word 預覽通過限定檢查，各案例頁數不增加。

前版 0.3.31：[Q2 格式與資料量閱讀實驗](docs/format-reading.md)。
完整答案合併為較自然的句子，部分缺答仍獨立呈現；不改自填文字或版型。
中英文鎖定同一英文來源，翻譯改文與原生 PDF／Word 驗收分開記錄。
[中英文 PDF／Word 前後樣張](reviews/2026-09-17-format-reading/README.md)：
前後各 30 個原生輸出、共 20 份 Word 預覽通過限定比較，全部頁數不增加；
仍不是全篇或 Microsoft Word 正式驗收。

前版 0.3.30：[Q11 中英文缺答框與跨頁對照](reviews/2026-09-17-archive-gap-panels/README.md)。
相鄰的兩項固定缺答共用外框，文字、字級、已填回答不變；英文長篇的一組
跨頁提示恢復同頁。八組中英共 48 個原生輸出及 16 份 Word 預覽核對通過，
Word 正文及版面不變。732 個翻譯檔沿用，不另維護中文 Jinja。
仍為實驗版，不代表整份 DMP 或 Microsoft Word 已驗收。
前版：[Q11 固定勾選內容成段閱讀](reviews/2026-09-16-archive-basis-reading/README.md)。
後續修正：[CI 淺層歷史導致的套件時間差異](docs/ci-package-history-2026-09-17.md)。

目前已由 Q1／Q5／Q15 切片擴充到十五題的合成輸出案例，另修正 Q3／Q12 的
部分漏出與錯誤否定分支；尚未宣稱全部 15 題完成內容驗收。
這是衍生客製模板，不代表 Science Europe 認可；目前不得當作已驗收正式版發布。
先看 [實驗結論](docs/pilot-results.md) 及 [PDF／Word 樣張](reviews/2026-09-11/README.md)。
下一輪 0.2.0 的內容與維護邊界見 [中文閱讀品質修改](docs/readability-review.md)。
前輪文件在 [0.2.0 中文 PDF／Word 樣張](reviews/2026-09-11-readability/README.md)。
0.2.1 實驗與原版英文對照見 [回答保留審閱](reviews/2026-09-11-answer-retention/README.md)。
0.2.2 的 HTML／worker 表格分層修正見 [結構與表格審閱](reviews/2026-09-11-structure-tables/README.md)。
0.3.0 樣張及已知問題見 [儲存與共享閱讀審閱](reviews/2026-09-11-storage-sharing/README.md)。
0.3.1 樣張見 [敘述與分頁審閱](reviews/2026-09-11-narrative-pagination/README.md)。
0.3.3 樣張見 [閱讀單位與短表格審閱](reviews/2026-09-14-reading-units/README.md)。
0.3.4 樣張見 [格式與容量審閱](reviews/2026-09-14-format-volume/README.md)。
0.3.5 樣張見 [缺答提示、數字單位與共享段落審閱](reviews/2026-09-14-reading-polish/README.md)。
0.3.6 樣張見 [共享限制、保存敘述與日期審閱](reviews/2026-09-14-sharing-preservation/README.md)。
0.3.7 樣張見 [保存回答覆蓋審閱](reviews/2026-09-14-preservation-coverage/README.md)。
0.3.8 樣張見 [Word 間距與保存政策對照](reviews/2026-09-14-word-rhythm/README.md)。
0.3.9 樣張見 [缺答與否定回答審閱](reviews/2026-09-14-answer-states/README.md)。
0.3.10 樣張見 [儲存庫管道對照與短清單分頁](reviews/2026-09-14-repository-reading/README.md)。
0.3.11 樣張見 [儲存庫聯繫回答歸屬與跨題引用](reviews/2026-09-14-repository-contact/README.md)。
0.3.12 樣張見 [Q11 資料脈絡與保存敘述連讀](reviews/2026-09-14-preservation-context/README.md)。
0.3.13 樣張見 [論文參考列與長網址完整性](reviews/2026-09-15-paper-reference/README.md)。
0.3.14 樣張見 [Q13 閱讀單位與整份分頁](reviews/2026-09-15-identifier-reading/README.md)。
0.3.15 樣張見 [識別碼追問、缺答分組與跨頁修正](reviews/2026-09-15-identifier-followups/README.md)。
0.3.16 樣張見 [短預算的 Word 連頁對照](reviews/2026-09-15-budget-pagination/README.md)：
短篇資源說明與預算表改為同頁，中文仍為 8 頁；長表格與整份留白尚未完成驗收。
0.3.17 樣張見 [長預算的全寬用途與續頁歸屬](reviews/2026-09-15-long-budget-reading/README.md)：
長篇 Word 保留完整回答，續頁帶出名稱／金額／經費來源；原生 PDF 與中文措辭未改。
0.3.18 樣張見 [長預算的分頁與留白](reviews/2026-09-15-budget-spacing/README.md)：
原生長 PDF 英文 13 → 11 頁、中文 12 → 10 頁，預算標題不再孤立；
英文 Word 10 → 9 頁。只改英文共用樣式，短／多筆控制組不變；
新增固定 worker 引擎的 CSS 探針。PDF 用途欄寬、續頁歸屬及整份閱讀品質仍待驗收。
0.3.19 樣張見 [PDF 長篇用途全寬與續頁歸屬](reviews/2026-09-15-pdf-budget-reading/README.md)：
中文長篇 PDF 10 → 9 頁、英文 11 → 10 頁；續頁保留資源名稱、金額與經費來源。
Word、HTML 和短／多筆控制組不變；原有 720 組譯文保留，只新增兩個幣別分支複本。
中英尾頁仍有留白，下一步回到整份中文閱讀與接近真實篇幅的案例。
0.3.20 見 [中英文漏填、續頁與 Q7 轉換修正](reviews/2026-09-15-missing-info-reading/README.md)：
修正 Q7 部分漏答提示、長 PDF 漏預算資訊時的續頁歸屬，以及空白中文 Q15 孤立提示。
初輪 22 份 PDF 抓到 Q7 中文段落未閉合，修正後另重產中英 Q7 與兩組控制組，
增加 6 份 PDF。初輪失敗紀錄與最後通過結果分開保存；未重產案例有明確的
套件／分支差異證明，不混稱全部使用最後 ZIP。短欄提示密度與整體留白仍待改善。
0.3.21 的 [個資追問與缺答修正](docs/personal-data-followups.md) 進一步處理 Q7
的漏填／明確否定、自由回答區塊，並移除 Q9 超出填答內容的固定推論；
版型和短預算欄寬未改，原生樣張驗證與既有發布門檻分開看待。
已完成 [8 組中英文 PDF／Word 原生對照](reviews/2026-09-15-personal-data-followups/README.md)：
每種格式各 16 份，缺答與內容保留檢查通過。但中文完整 Word 的 Q8 資料集名稱
與授權說明在第 4／5 頁分離，已保留失敗檢查；整份文件仍未驗收、未發布。
0.3.22 見 [Q8 Word 名稱與授權說明連頁對照](reviews/2026-09-15-q8-word-labels/README.md)：
修正上述中文反例，以及長篇中文、多筆英文的同類分頁問題。六組中英文案例
各產出 12 份 PDF／DOCX；15 題 HTML、PDF 正文與頁數不變，Word 只改合格
名稱的連頁樣式，731 個翻譯檔完全相同。初輪曾遇到 AST 通過、DOCX 卻忽略
樣式的失敗，已保存證據並補上實際 DOCX 探針。英文 Q9 的既有跨頁、空白中文
尾頁留白與短預算提示仍待改善；沒有宣稱全篇或 Microsoft Word 已驗收。
CI 失敗原因及隔離依賴修正見 [CI 修正紀錄](docs/ci-repair-2026-09-14.md)。
0.3.23 見 [Q9 名稱、倫理說明與整份 Word 分頁對照](reviews/2026-09-16-q9-word-labels/README.md)：
Q9 短名稱與說明連頁，兩句固定說明合成同一段；沒有改寫或合併作者自由回答。
保留「局部修好、英文卻增為 8 頁」的未採用版，最後完整英文保持 7 頁、中文
保持 8 頁，並以部分漏填、多筆及長回答檢查全篇不增頁。PDF 正文和 731 個
譯文檔不變；空白中文 PDF 尾頁及短預算提示仍未完成理想版面驗收。
0.3.24 見 [空白 Q15 資訊框與 PDF 前後對照](reviews/2026-09-16-empty-pdf-reading/README.md)：
只將四項固定缺答共用一個框，空白中文 PDF 4 → 3 頁，文字、字級與段落保留；
英文空白仍為 4 頁。五組中英原生控制共 30 個輸出，部分漏填、否定與長預算
沒有套用此規則，所有 Word 本文與頁數不變。初版中文字型探針／CI 的失敗
與修正另存紀錄；短預算折行及英文尾頁留白仍待改善。
這批樣張仍包含已知失敗，不可作為已驗收的理想 DMP。
0.3.25 見 [短預算缺答的原生前後對照](reviews/2026-09-16-short-budget-reading/README.md)：
partial 中文 PDF 5 → 4 頁，缺幣別提示中文 2 → 1 行、英文 4 → 2 行，
字級與答案保留。七組中英共 42 個原生輸出與 14 份 Word 預覽核對通過；
Word 不變，但其短預算提示折行仍待修。初版 autoescape 失敗與修正版重測
分開保存；另有本機 worker exit 139 後同映像恢復紀錄，根因仍待查，不算
正式發布驗收。731 個翻譯檔不變，不另維護中文 Jinja。
後續 [worker 字型穩定性診斷](docs/worker-pdf-stability.md) 沒有重現 exit 139：
80 次隔離 PDF 轉換、20 次字型探針均完成；最小修補前後 28 組 PDF 的
文字座標、連結及頁面影像一致。僅為獨立 runtime 實驗，未換用原生 worker，
不宣稱根因已解決，也不替代原生成品與 Word 驗收；模板仍為 0.3.25。
中文 Jinja 由既有 `dsw-document-template-tool` 的翻譯樹產生；主要分支邏輯
維護在英文 repo。翻譯來源是 `translation/**/translation.md`。

0.3.26 的 [Word 短預算欄寬實驗](docs/word-short-budget.md) 沿用共用短表格
判斷，只加 Word 專用標記並調整合規表格欄寬；回答、字級與 731 個翻譯檔
不變。原生 partial 的中文 Word 缺幣別提示 2 → 1 行、英文 3 → 2 行，
仍各四頁；七組中英共 42 個輸出及 14 份預覽核對通過。見
[前後樣張](reviews/2026-09-16-word-short-budget/README.md)。引擎仍為 tables-only，
與字型修補實驗分開；中文混合缺答的稀疏尾頁及 Word 實機仍待驗收。

後續 [Word 尾頁分頁診斷](docs/word-budget-tail.md) 完成 24 份中英對照：
解除連頁會產生孤立標題或拆開同一筆資源，整題連頁則將留白移至前頁。
三種改法均未採用，模板仍為 0.3.26；反例納入回歸檢查，下一步改看
整份固定敘述的閱讀密度，而非擴大局部分頁規則。

0.3.27 的 [識別碼敘述精簡](docs/identifier-concise-prose.md) 移除已知指派者
前重複的肯定句，同時保留指派、指派者與解析保證三項事實。中文混合缺答
的兩段說明在原生 PDF／Word 各由兩行變一行；八組中英 48 個原生輸出與
16 份預覽檢查通過，所有案例不增頁。731 組譯文配對不變；漏填者仍顯示
已知資訊與缺答提示。見 [前後樣張](reviews/2026-09-16-identifier-concise/README.md)。

0.3.28 的 [中文識別碼句間空格](docs/identifier-cjk-spacing.md) 只移除 PDF／Word
在 Q13 固定句之間額外插入的西文空格。八組中英 48 個原生輸出及 16 份
預覽通過；英文與三組中文缺答／否定對照的文字座標也不變。731 個翻譯檔
完全保留，沒有改字級或行距；其他句間空白及稀疏尾頁仍待處理。見
[前後樣張](reviews/2026-09-16-identifier-spacing/README.md)。

`pipeline.yml` 分開記錄英文來源版本與中文輸出版本。開發預覽允許明確標記的
未提交修改；正式建置要求來源與工具為乾淨且符合 lock 的 commit。

先 checkout `pipeline.yml` 中的英文與工具 commit，並在工具的 `.venv` 執行
`pip install -e '.[dev]' -r ../science-europe-template-zhtw/requirements-dev.txt`。
正式候選建置不加 `--preview`；候選建置成功不代表成品驗收通過。

```sh
../dsw-document-template-tool/.venv/bin/python scripts/build.py \
  --english ../science-europe-template \
  --tooling ../dsw-document-template-tool --preview
```

第一次建立或英文修改後加上 `--refresh`，會重新抽取並精確遷移現有翻譯。
初次匯入舊官方中文樹可指定 `--seed-tree PATH`。沒有精確對應的單位保留空白，
需由譯者編修。空白翻譯的預覽可能顯示英文，不能作為已完成的中文版本發布。

每次建置建立新的 `outputs/build-*` 目錄，保存英中套件、展開來源、翻譯檢查
與 manifest，不覆寫前次結果。正式版本須另通過成品驗收與不可覆寫的發布步驟。

字型：PDF 包含 Noto Sans TC；Word 的東亞字型使用 Noto Sans CJK TC，
開啟端字型替代可能影響分頁，需在實際使用的 Word 環境確認。

成品測試限隔離的本機 DSW（預設 `localhost:13300`），使用合成回答與公開
測試帳號，不讀取線上 keyring、不修改線上 project。先在英文 repo 產生並驗證
`fixtures/pilot`，再執行：

```sh
../dsw-document-template-tool/.venv/bin/python scripts/run_pilot.py \
  --build outputs/build-REPLACE_ME --english ../science-europe-template \
  --tooling ../dsw-document-template-tool
```

已知 Markdown 表格失敗會令此命令回傳 2，並留下 `pilot-report.json`；不可
將它忽略後發布。CI 僅涵蓋建置與單元測試，沒有假裝完成 Word／視覺驗收。
下一步與版本政策見 [版本管理](docs/version-management.md)。

原始英文源碼及本 repo 的程式碼採 Apache-2.0；保留上游貢獻者及授權。
初始翻譯精確沿用自 `depositar/science-europe-template-zh_Hant` 的已審閱樹，
來源 commit 記於 `pipeline.yml`。Science Europe 指南內容依原出版物署名，
Noto 字型依隨附 OFL 授權。本 repo 不維護第二套獨立中文分支邏輯。
