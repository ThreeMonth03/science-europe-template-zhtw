# 0.3.0：儲存／備份對應與共享段落閱讀實驗

2026-09-11。本機隔離、合成資料的實驗，不是正式 DMP、release 或線上部署。
保留官方 Science Europe 的六節十五題架構；英文仍衍生自 1.30.1，中文仍由
同一套英文 Jinja 經既有翻譯流程產生，沒有第二套中文條件邏輯或 LLM 改寫。
本文件另複製至 review 目錄，下列樣張連結以該處為準。

## 建議閱讀

- [兩個資料提供管道的中文 PDF](tables/storage-sharing-chinese.pdf)
- [同份可編輯 Word](tables/storage-sharing-chinese.docx)
- [Word 的 LibreOffice 預覽](tables/word-preview/storage-sharing-chinese.pdf)
- [刻意漏填部分選項的中文 PDF](tables/storage-sharing-partial-chinese.pdf)
- [相同內容的英文 PDF](tables/storage-sharing-english.pdf)
- [同一模板與回答、原版 worker 的中文 PDF](stock/storage-sharing-chinese.pdf)
- [沿用 0.2.2 回答的對照案例](tables/structured-chinese.pdf)

`tables/` 使用本機實驗 worker 才能正確處理自由回答中的 Markdown 表格；
不是只安裝模板就能在原版 worker 得到的效果。全部樣張都有已知限制，不可
當作已驗收的理想 DMP。完整 HTML（包含內嵌字型）與 ZIP 留在本機 build
目錄；此輪 Git 僅保留精簡 PDF／DOCX、問卷雜湊、報告及 Word 預覽，避免
每輪重複提交大量內嵌字型。既有 review 檔案沒有刪除或覆寫。

## 實際改了什麼

### Q5：補回問卷已有的答案，不捏造執行細節

已對照實際 compiled Common KM 2.7.0 的問題、說明與選項，補上共享工作
空間是否由專責人員維運，以及研究期間冷儲存封存的媒體、是否異地、是否
變動、頻繁備份需求、人為錯誤復原安排。兄弟欄位缺答不再一起遮掉已填資訊。

修正一個既有 UUID 綁定：`archivedDuringReNoAUuid` 原先雖指向存在的 UUID，
卻屬於下一題的選項。新增檢查不只驗證「UUID 存在」，也驗證「選項屬於
這一道題」。九個選定問題的 compiled 路徑與文字記在儲存對應稽核報告；
兩個語言 KM 各檢查七題中的十五個選項歸屬。

限制仍必須明說：

- 磁帶／磁碟、異地 Yes 都不是具名儲存地點。
- 「需要頻繁備份」不是已實施的每日／每週排程。
- 復原等待時間不是備份頻率；發布用儲存庫也不等於工作資料的儲存位置。
- 提示框表達的是「這些對應回答不足以建立這項細節」，不指控使用者漏填，
  也不宣稱其他自由回答中一定沒有相關說明。

因此 Q5 的實際地點與排程仍是部分對應，不是完整解決。本輪沒有新增 KM
問題；若要用具名服務、地點與排程收集這些細節，需要另外決定 KM 擴充。

### Q10–Q13：清除模板清單層級，保留真實內容

資料集名稱保留為小標題；提供管道及授權改成平坦區塊，不再套進多層清單。
使用者自由回答裡的清單／表格原樣處理，沒有刪掉或改寫。只有模板自有的
重複引言移除，固定識別碼政策句才沿用既有規則合成段落。

Q10 把取用對象、儲存庫、授權及日期分開判斷：前兩項缺答，已填的後兩項
仍顯示並附精確缺漏提示。Q13 即使缺少指派者細節，仍保留「將取得持續
識別碼」的肯定回答。發布日期、授權日期、軟體取得位置均採完整句或自足
標籤供中文翻譯，不依英文前後綴接出中文。

Word 的一般段後距由 6 pt 改為 4 pt，字級及 1.4 倍行距不變。這是呈現調整，
不是靠縮小字或刪減填答增加密度。

## 檢查方法與結果

- 乾淨、精確鎖定的英中 0.3.0 套件：665 個翻譯單位，空白 0；翻譯與結構
  audit 均為空陣列。英文 34 項、中文流程 15 項單元測試通過。
- 新舊英文及中文合成 fixtures 通過 compiled KM 路徑驗證；十五題靜態檢查
  未定義變數 0、不存在實體 0。不把這些數字視為全問卷完整性證明。
- 原版 worker：8 案例 × 2 語言 × HTML／PDF／DOCX，共 48 份生成成功。
  指定語意檢查通過，但自由回答表格留下 24 筆阻擋紀錄，程序回傳 2；
  這是兩類已知表格問題在六案例、兩語言重現，不是 24 個獨立根因。
- 新增 checker 驗證 structured、storage-sharing、storage-sharing-partial
  六個案例／語言配對：指定容量、檔名、工具、日期、限制條款與網址在三格式
  留存；Q10–Q13 在這些案例不再有模板巢狀清單或非法段落 block；英中十五題
  的 item／fact／status 標記一致。
- 與 0.2.2 的相同 structured 輸入比較，未修改的 Q1–Q4、Q6–Q9、Q14–Q15
  在中英各十題、共二十項文字檢查一致（忽略空白）。
- 原版 worker 的既有閱讀回歸檢查通過十個案例／語言配對；長文字在中英
  PDF／DOCX 仍保留預期八十次測試句。
- 實驗 worker：三個新閱讀案例 × 兩語言 × 三格式，共十八份生成成功；
  指定內容、原生 HTML 表格及可編輯 DOCX 表格檢查通過，無阻擋紀錄。
  新 checker 的六個案例／語言配對亦通過。
- 兩種 worker 使用相同英中 ZIP；六個案例／語言配對的 recipe、events、KM
  與套件雜湊相同，十五題 item／fact／status 標記一致。Q2–Q15 文字在忽略
  空白後一致；表格儲存格值都可對回原版文字。沒有宣稱 Q1 全文語意等價。

舊的 representative／retention-partial 不是本輪端到端案例，沒有把上一輪
八十八項答案保留結果冒稱本輪已重新執行。所有機器通過僅限宣告範圍；
`release_acceptance` 仍為 false。

## 實際閱讀觀察與未完成項目

原版 worker：沿用回答的中文 PDF 六頁、Word 的 LibreOffice 預覽七頁；
新增雙管道案例 PDF 七頁、Word 預覽八頁。頁數沒有因清單改平坦就必然減少，
也不應拿頁數當內容充足性指標。這不是 Microsoft Word 實測。

已人工看原版 worker 的 structured PDF 第五、六頁、雙管道 PDF 第四至
六頁及 Word 預覽第六、七頁：

- Q10 的公開管道、受限管道與各自授權日期能分清；Word 不再有三層縮排。
- Q5 補回封存答案，但原先 Q6 也敘述封存／備份，造成跨題重複。下一輪應
  決定每項資訊的主要歸屬、必要時交叉引用，不能單純刪掉重複字串。
- Q5 冷儲存段仍有「一個答案一行」的問卷口吻。「封存／典藏」、「我們／
  本計畫／專案」尚未統一；受限授權引言也仍較生硬。中文全文編修未完成。
- PDF 的 Q9 短清單仍跨頁，雙管道案例最後一頁只剩預算表；Word 的 Q11
  預算敘述仍接到次頁。應用完整案例調整分頁規則，而非整節禁止換頁或縮字。
- 資料集名稱在 Q10–Q13 重複是刻意保留身份；是否以共同摘要搭配交叉引用
  減少重複，要另做多資料集測試，不能只看此單資料集案例。
- 未驗證所有 KM 分支、其他版本、真實使用者專案或 Microsoft Word；
  合成案例也不是已完整編列的經費計畫。法律／倫理句仍需專門內容審閱。

另人工檢查實驗 worker 的雙管道 PDF 第三、五、六、七頁及 Word 預覽第三、
六頁：溯源表格正常；Q10 兩管道在 PDF 能在同頁讀完，Q11–Q13 層級清楚。
但 Word 的儲存庫清單引言仍留在頁底、清單在次頁，PDF 的 Q14 也有一句接到
次頁。兩案例頁數均與原版 worker 相同；表格修好不等於分頁問題一起解決。

## 來源與長期維護

- 英文套件來源：`11f990ceb4b6315120fc1682971b99eeccb1e89c`，0.3.0。
- 中文建置來源：`256e423520aff5423866ec38fcc3ced91695f3b9`，0.3.0。
- 工具：`25e339fbdfb1d20796471055790aad6a4226b6ed`。
- 官方 baseline 仍為 1.30.1／`22d60aae4b63ee677477ac0c73097807284aaf9f`。
- 兩個 repo 使用本輪短期工作分支 `feat/storage-sharing-readability`；同名
  只是工作標籤，英中真正配對依 `pipeline.yml` 的 commit lock 與 manifest。
  後續報告提交不會改變已建置套件的來源 checkpoint，沒有移動既有 tag。

英文維護有意客製的語意／HTML，中文維護翻譯及驗收；不把產生後的中文
Jinja 再開成一套分支邏輯。這輪 Q10 列入 upstream 升級的 critical overlap。
將來官方更新要審閱 UUID 所屬題目、分支行為、完整翻譯句與實際三格式，
不能只看 Git 是否無衝突；選擇性移植也不等於可以推進整體 baseline。

worker 是獨立版本軸：表格實驗鎖定原映像 digest 與來源雜湊，僅開啟既有
Python-Markdown 的 tables extension。正式導入仍須決定 upstream 修正或
自有 runtime 維護，不可包裝成模板升版已解決線上表格問題。

本輪沒有使用 keyring、線上專案或真實回答。實驗後 worker 已恢復原映像
`sha256:5e5c5e1e436feb49fc4cbcd62c2e0ab2785db2141b0fe40d2926906bcfeaebfc`，
四項本機服務均停回執行前狀態，containers／volumes 保留，線上 DSW 未變更。

## 重跑本輪檢查

先依 manifest checkout 英文、中文及工具來源，建立乾淨鎖定的候選建置。
以下 `BUILD`／`VARIANT` 為每次執行新建立的目錄，不覆寫本輪產物。

```sh
../dsw-document-template-tool/.venv/bin/python scripts/run_pilot.py \
  --build BUILD --english ../science-europe-template --tooling ../dsw-document-template-tool \
  --cases structured storage-sharing storage-sharing-partial empty negative partial populated stress
../dsw-document-template-tool/.venv/bin/python scripts/check_storage_sharing_outputs.py --build BUILD
../dsw-document-template-tool/.venv/bin/python scripts/check_readability.py --build BUILD
```

第一個命令在原版 worker 回傳 2 是本輪保留的已知表格失敗，不准忽略後發布。
依 `experiments/markdown-tables/README.md` 切換隔離 worker，執行
`scripts/prepare_runtime_variant.py --build BUILD`，再跑：

```sh
../dsw-document-template-tool/.venv/bin/python scripts/run_pilot.py \
  --build VARIANT --english ../science-europe-template --tooling ../dsw-document-template-tool \
  --cases structured storage-sharing storage-sharing-partial
../dsw-document-template-tool/.venv/bin/python scripts/check_storage_sharing_outputs.py --build VARIANT
../dsw-document-template-tool/.venv/bin/python scripts/compare_runtime_outputs.py \
  --baseline BUILD --variant VARIANT --cases structured storage-sharing storage-sharing-partial
```

完成後恢復原 worker 與服務狀態。`storage-sharing-report.json`、
`runtime-comparison.json` 都綁定檢查程式與檔案雜湊；本輪 build 目錄分別為
`outputs/build-5ukiwomx`、`outputs/runtime-tables-yuqe6ire`。報告以外仍需視覺
及內容審閱。`collect_storage_review.py` 只封存已核對的實驗證據，不發布套件。
