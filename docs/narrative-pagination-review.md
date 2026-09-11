# 0.3.1：敘述連貫性與分頁審閱

2026-09-11。合成回答的本機隔離實驗，尚非正式 DMP、已驗收 release 或線上
部署。保留 Science Europe 六節十五題；英文衍生來源仍為官方 1.30.1，中文
沿用既有翻譯樹產生，沒有另一套中文 Jinja 判斷或 LLM 重寫使用者回答。
下列連結以本文件複製到的 review 目錄為準。

## 樣張

- [中文 PDF：兩個資料提供管道](tables/storage-sharing-chinese.pdf)
- [同份 Word](tables/storage-sharing-chinese.docx)
- [Word 的 LibreOffice 預覽](tables/word-preview/storage-sharing-chinese.pdf)
- [原版 worker 的對照 PDF](stock/storage-sharing-chinese.pdf)
- [部分缺答仍保留其他資訊](tables/storage-sharing-partial-chinese.pdf)
- [只填封存，不假裝已回答安全措施](tables/archive-only-chinese.pdf)
- [八十段授權條件的長文反例](tables/narrative-long-chinese.pdf)
- [沿用相同回答的單管道案例](tables/structured-chinese.pdf)
- [雙管道英文 PDF](tables/storage-sharing-english.pdf)

`tables/` 使用先前的獨立 Markdown 表格實驗 worker；模板更新本身並未修好
原版 worker 的自由回答表格。正式採用仍需另決定 runtime 維護方式。樣張
含有未完成項目及問卷缺口，不是可直接照抄的理想 DMP。

## 本輪改動

1. **Q5 主責封存與備份，Q6 不重述。** Q5 將既有固定敘述整理成工作空間、
   封存位置及變動／復原等段落；沒有刪掉已映射的 facts，也沒有補寫未知
   地點或備份排程。缺答提示由獨立區塊隔開，不會混進已知安排的正文。
2. **交叉引用不是答案。** Q6 在封存 Yes 時連至 Q5，但不拿這個連結當成
   「安全措施已填」。只填封存的反例仍保留 Q6 待補提示。移除的舊 Q6 敘述
   還包含把「不需要頻繁備份」誤寫成「將低頻率備份」的問題；現在只呈現
   Q5 能由回答支持的需求判斷。
3. **中文及自由回答。** 修整三個 Q6 固定句的「計畫成員／本計畫」用語。
   Q10 的受限取用引言改成完整句，條件另由獨立 Markdown 區塊呈現；無條件
   內容時顯示待補，不把使用者段落拼進英文前後綴。
4. **針對 Word 真正辨識的結構修正。** 0.3.0 的日期／清單引言用 `<p>`
   屬性，實際 DOCX 卻是一般 Body Text。改為 `answer-lead` div，使其使用
   `Pilot Lead` 的 keep-with-next。不是只在 CSS 裡宣告同頁就算修好了。
5. **有界限的分頁。** Q9 的固定兩項資料屬性清單、短 Q14 職責說明，以及
   短資料提供管道，才要求盡量同頁。職責／管道上限為五百個呈現字元，
   Word 亦檢查長度與 block 類型；含已標記自由回答、清單或表格的管道不套用整段
   Word 段落鏈。長文仍可跨頁，字級、段距與行距沒有再縮小。

第一版實際 PDF 顯示：Q5 變短後，短 Q10 管道反而在日期之前跨頁。因此補做
短管道閱讀單位及前導句連結，再鎖定新的來源重跑。此輪交付不是第一版
`build-n1_k9b61`；該版保留作診斷，沒有覆寫它或假裝只是文字抽取差異。

## 驗證

- 英文四十二項、中文流程二十一項單元測試通過；663 個翻譯單位、空白 0，
  翻譯與結構稽核均無違規。新舊 fixtures 經實際 compiled 中英 KM 2.7.0
  驗證，可到達的路徑／選項檢查通過。十五題靜態引用無未定義或不存在實體。
- 最終原版 worker：八案例 × 兩語言 × 三格式，共四十八份生成成功；指定
  語意檢查通過。仍有二十筆已知表格阻擋紀錄（五案例 × 兩語言 × HTML 表格／
  DOCX 可編輯表格兩類），驗收報告 `passed: false`，重驗程序回傳 2。
- 原版 worker 的新敘述 checker 通過十個案例／語言配對；既有閱讀回歸
  另跑 empty、negative、stress，共六個配對。
- 表格實驗 worker：五案例 × 兩語言 × 三格式，共三十份生成成功，指定
  語意及表格檢查通過、無阻擋紀錄；新敘述 checker 的十個配對亦通過。
  與同 worker 的 0.3.0 比較另通過九十項逐題檢查。
- 四個含表格案例、八個案例／語言配對在兩種 worker 使用相同 ZIP、recipe、
  events 與 KM 雜湊。十五題 fact markers 一致，Q2–Q15 文字忽略空白後一致，
  Q1 表格儲存格值均留存。沒有宣稱 Q1 全文語意等價；archive-only 不在這項
  表格對照之內，而由兩組各自的缺答／內容檢查驗證。
- 檢查包含舊三案例的十五題逐題文字比較，只允許已宣告的 Q6／Q10 修訂，
  不把任意差異都當成排版；Q5 facts 在三格式留存，Word 合段不吞缺答提示。
  最終原版 worker 的三案例 × 兩語言 × 十五題，共九十項比較已通過。
- 新增 `archive-only` 與 `narrative-long`。後者在自由回答中追加八十段，
  檢查 HTML／PDF／DOCX 的次數，並檢查 Word 仍是八十個獨立段落。
- PDF 額外檢查文字框不超出紙張邊界。此檢查不能證明沒有重疊、行距適當
  或整份好讀；視覺審閱與目標 Microsoft Word 測試是另外的門檻。

`selected_checks_passed` 僅代表報告明列範圍，`release_acceptance` 仍為 false。
原版 worker 的已知表格失敗仍須列出；實驗組通過不能替代正式環境驗收。

新增 archive-only 起初被舊測試程式誤套「兩筆參考資料及預算已填」的斷言。
已新增此反例專用的缺答／交叉引用斷言與兩項單元測試，並對原渲染檔重跑
`--validate-only`。這是測試程式更新，沒有改動反例回答或已產生的套件。
產物 manifest 記錄建置來源，後續測試程式版本另由報告 SHA-256 綁定。

## 閱讀觀察與剩餘工作

原版 worker：structured 中文 PDF 六頁、Word 的 LibreOffice 預覽七頁；
雙管道 PDF 七頁、Word 預覽八頁，均與 0.3.0 相同。這輪沒有用頁數減少作為
驗收標準。長授權條件中文 PDF 九頁，八十段均留存且能正常跨頁。

已人工檢查原版 worker 的 structured PDF 第四、五頁，雙管道 PDF 第三至
六頁、Word 預覽第四與第六頁，以及長條件 PDF 第五、六頁：

- Q5 從多條短行變成工作空間、封存位置、變動／復原段落，Q6 不再重述
  封存／備份。實際 Word 同樣有合段，不只是 PDF 的 inline 視覺效果。
- 單管道案例的 Q10 已不在授權日期前拆頁。這也帶來前頁較多留白，是讓
  短閱讀單位完整的取捨；不是對每一節加入硬性換頁。
- Q11 清單引言使用實際 Word keep-with-next，已與其後清單銜接；後續兩段
  預算敘述仍可能接到下一頁。PDF 的 Q5 封存兩個段落也仍可能跨頁。
- Q9 的兩項固定資料屬性沒有再拆開；Q14 短職責說明保持完整。仍未逐一
  驗證其他資料集數量、長姓名與長機構名稱的實際排版。
- 長授權內容保留原有清單及八十個獨立段落，沒有縮字、合成一個超長段落
  或用整段禁止分頁造成溢出。

表格實驗組另看了雙管道 PDF 第三至六頁與 Word 預覽第六頁：溯源表格正常；
Q5 與提示框同在第四頁，Q10 的兩管道同在第五頁，Q11 儲存庫清單引言與
清單一起移至第六頁，短 Q14 職責說明亦完整。Word 第六頁的清單引言與
兩個儲存庫項目同頁，不再只把引言留在頁尾。這仍只是宣告案例的觀察。
表格實驗組的單／雙管道頁數也維持 PDF 六／七頁、Word 預覽七／八頁。
兩種 worker 的長條件 Word 預覽均為十一頁、仍可抽取八十段測試句；另抽看
實驗組第七頁確認正常連續排文。八份 Word 預覽的文字框亦未超出紙張邊界。

仍未宣稱下列事項已解決：

- 全問卷所有分支、所有使用者填答皆完整出現在文件；目前只是選定問題及
  合成案例的保留檢查。Science Europe 題目存在不等於內容已足夠。
  新 archive-only 反例仍顯示 Q8／Q14 缺答時只有題目、沒有個別待補文字，
  這是已知驗收缺口；本輪不宣稱十五題缺答處理都完成。
- Q5 的具名儲存地點與實際備份排程；目前對應回答不足以確立這些細節，
  不能當成使用者漏填，更不能讓模型猜。KM 擴充仍待另作決定。
- 全文中文編修、跨題資料集名稱重複、其他風險／法律／倫理分支的內容審閱。
  法律／倫理句仍是問卷選項的模板呈現，不是專門審查結論。
- Q10「其他聯絡安排／特殊取用流程」等繼承分支尚未全面加上自由回答區塊
  標記；本輪八十段反例只驗證受限授權條件欄位。不能把目前的有界分頁規則
  說成已保證所有自由回答分支都不會被視為短段落鏈，發布前需擴充反例。
- 真實 Microsoft Word 的分頁、使用者端字型替代，以及 Common KM 2.7.0
  以外的相容性。LibreOffice 預覽不得標成 Microsoft Word 實測。

## 版本及重跑

- 最終英文：`a9242f603ad66a4f089888b278f020e252a84ea0`，客製版 0.3.1。
- 最終中文建置來源：`e791238aa179cd80788146eb800a1d2bc05bedc6`，0.3.1。
- 工具：`25e339fbdfb1d20796471055790aad6a4226b6ed`，本輪沒有更動。
- 官方 baseline：`22d60aae4b63ee677477ac0c73097807284aaf9f`／1.30.1，未推進。
- 英中短期分支均為 `feat/narrative-pagination`，真正對應依 commit lock。
  報告／樣張的後續提交不會改變已建置套件的來源 checkpoint。沒有建立
  永久版號 branch、移動 tag、合併主線或發布 release。

Q6／Q14 已列入 upstream critical overlap；升級時要審閱資訊歸屬、缺答判斷、
完整翻譯句及實際版面，而不只處理 Git 衝突。Word Lua／reference style 與
PDF CSS 都屬自有呈現層。Worker 表格實驗是另一個已鎖定的版本軸。

重跑先 checkout manifest 的三個 commit、乾淨建置。原版 worker 的案例為
`structured storage-sharing storage-sharing-partial archive-only narrative-long empty negative stress`。
實驗 worker 使用前五案例；跨 worker 表格比較使用除 archive-only 外的四案例。

測試程式有建置後更新，尤其 archive-only 的專用斷言。重跑檢查請使用此
審閱提交中的 scripts／tests；manifest 的來源 checkpoint 用於重建套件，
檢查程式另以各報告的 SHA-256 核對，不使用較早且不認識反例的測試版本。

```sh
../dsw-document-template-tool/.venv/bin/python scripts/check_storage_sharing_outputs.py --build BUILD
../dsw-document-template-tool/.venv/bin/python scripts/check_narrative_outputs.py --build BUILD --prior PRIOR_030
../dsw-document-template-tool/.venv/bin/python scripts/check_readability.py --build BUILD --cases empty negative stress
```

實驗 worker 依 `experiments/markdown-tables/README.md` 切換，使用
`prepare_runtime_variant.py` 複製同一組套件，不能另改模板混入比較。新 checker
兩組皆執行；同 worker 的 0.3.0 比較分別使用原版／表格版 prior。所有報告
綁定檢查程式及產物雜湊，review 封存也核對附加報告。

本輪未使用 keyring、線上專案或真實回答。最終 worker 已恢復原版映像
`sha256:5e5c5e1e436feb49fc4cbcd62c2e0ab2785db2141b0fe40d2926906bcfeaebfc`。
本機 postgres、minio、server、docworker 四項服務均停回原狀，containers／
volumes 保留，沒有部署至線上 DSW。

本機最終建置目錄為 `outputs/build-zwavkfqc`，表格實驗組為
`outputs/runtime-tables-hbnw4rkw`。完整 HTML／ZIP 保留於本機；此 review 僅
封存較精簡的 PDF／DOCX、預覽、輸入指紋及檢查報告，附全檔案 checksums。

```sh
../dsw-document-template-tool/.venv/bin/python scripts/collect_storage_review.py \
  --baseline outputs/build-zwavkfqc --variant outputs/runtime-tables-hbnw4rkw \
  --destination reviews/2026-09-11-narrative-pagination \
  --review-document docs/narrative-pagination-review.md \
  --extra-cases archive-only narrative-long \
  --checked-report narrative-report.json scripts/check_narrative_outputs.py
```

封存程序不覆寫已存在的目錄，也不是發布套件或部署指令。
