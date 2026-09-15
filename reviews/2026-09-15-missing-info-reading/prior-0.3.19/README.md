# 0.3.19 中英文漏填 PDF 檢查

2026-09-15。結論：**可產檔，但漏填情境的內容提示與排版驗收未通過。**
本輪是檢查，不修改模板、翻譯或版本，不提交／推送新變更，不部署線上服務。

## 範圍與結果

9 種合成情境 × 中英文，共新產 18 份原生 PDF、18 份原生 HTML。PDF 共 133 頁；
自動核對所有文件的六節、十五題，共 270 個題目位置與非空回答區塊。
156 個已輸出的缺答提示及 560 個 answer-detail 段落均通過文字保留檢查。
六份長篇缺答 PDF 的 60 段編號用途都完整保留，每段各自位在唯一一頁。
但「原本就沒有輸出的缺答提示」不會被這種保留檢查找到，所以另加可達追問案例。

使用精確的 0.3.19 ZIP、隔離 DSW 4.30、WeasyPrint 68.1 與先前的 Markdown
表格修補 worker；不代表原版 worker 的發布驗收，也沒有使用私人專案／keyring。
此次沒有重新測 Word。每種情境、每個語言都有關鍵頁影像抽樣，並非人工逐頁
看完全部 133 頁；頁面越界、缺答文字保留與題目位置則涵蓋全部 PDF。

| 情境 | 英文 PDF | 中文 PDF | 主要觀察 |
| --- | --- | --- | --- |
| 整份全空白 | [4 頁](native/empty-english.pdf) | [4 頁](native/empty-chinese.pdf) | 中文第 4 頁僅有一條缺答提示 |
| 明確回答不需要 | [4 頁](native/negative-english.pdf) | [3 頁](native/negative-chinese.pdf) | 本次所選否定與未填狀態有區分 |
| 部分填答 | [5 頁](native/partial-english.pdf) | [5 頁](native/partial-chinese.pdf) | 5000、0 TWD 與幣別缺答保留；尾頁仍有留白 |
| 保存安排部分漏填 | [8 頁](native/preservation-partial-english.pdf) | [7 頁](native/preservation-partial-chinese.pdf) | 已填政策與七個指定缺口皆保留 |
| 多筆預算混合漏填 | [8 頁](native/budget-mixed-gaps-english.pdf) | [7 頁](native/budget-mixed-gaps-chinese.pdf) | 未填名稱、用途、金額、幣別、支援項目及經費來源可見；提示欄擁擠 |
| 長用途、漏金額 | [11 頁](native/budget-long-no-amount-english.pdf) | [10 頁](native/budget-long-no-amount-chinese.pdf) | 續頁無原資源身分與完整缺答脈絡 |
| 長用途、漏幣別 | [11 頁](native/budget-long-no-currency-english.pdf) | [10 頁](native/budget-long-no-currency-chinese.pdf) | 同上；5000 仍保留 |
| 長用途、漏經費來源 | [11 頁](native/budget-long-no-funding-english.pdf) | [10 頁](native/budget-long-no-funding-chinese.pdf) | 同上；第一頁提示未帶到續頁 |
| Q7 有法律依據、漏保護措施 | [8 頁](native/personal-data-partial-english.pdf) | [7 頁](native/personal-data-partial-chinese.pdf) | 兩語言第 4 頁皆未提示未答追問 |

## 需要修正的問題

### 1. 部分填答會讓未答追問沒有提示（中英皆有）

Q7 選擇蒐集個人資料、Explore，僅填法律依據為公共利益，不填保護措施。
DSW 編譯後的 KM 證實 `cpersGdprSafeguardsQUuid` 是此路徑下可達且未回答的問題。
但中英文 PDF 第 4 頁均只有法律依據小標與一句已填敘述，直接進入 Q8。

原英文 Q7 第 98 行只在整個 `answerContent` 為空時產生通用缺答提示。一旦有
任何內容，就不會再提示其他未答項目。這不是翻譯或 PDF parsing 造成的漏字，
而是英文來源的缺答判斷粒度不足。這項檢查不判定個案是否合法或回答是否足夠。

修正方向：按當前可達欄位顯示已填／待補資訊，不只按整題是否有文字判斷。
不能對父題沒有啟用的追問亂標缺答，也不能替使用者補寫保護措施。
證據：[中文頁面](q7-zh-4.png)、[英文頁面](q7-en-4.png)、[KM 可達性](extra-fixture-validation.json)。

### 2. 長篇用途遇到漏填即退回窄表格（中英皆有）

分別刪除第一筆資源的金額、幣別或經費來源，其餘 60 段用途與第二筆零元
資源保持不變。三種情境、兩種語言都退出 0.3.19 的全寬／重複資源表頭排法。
英文用途在第 8–11 頁，中文第 7–10 頁；後續頁只剩欄名，沒有該筆名稱與
完整的金額／經費資訊或缺答提示。用途擠在 57% 欄寬，測試段落各折成兩行。

原英文 `src/budget-reading.html.j2` 第 17–21 行對表頭片段採保守白名單，
未接受 `.data-gap` 等缺答標記，因此安全回退成原表格。這避免了改壞內容，
卻沒有達成「漏填也好讀」的目標。前輪完整填答的中文 9 頁／英文 10 頁
不能作為這些缺答情境通過的證據。

修正方向：為有限、模板自有的缺答資訊設計安全表頭，保留可用數值及提示，
續頁仍能辨識資源；不直接放寬所有 HTML，也不刪字或自動填補金額。
證據：[中文續頁](long-funding-zh-08.png)、[英文續頁](long-currency-en-09.png)。

### 3. 中文全空白文件的短缺答群組被拆頁

Q15 的四條提示被拆成第 3 頁三條、第 4 頁一條；最後一頁只剩「資料管理
及落實 FAIR 原則所編列的經費與時間」尚待補充，沒有題目與其他脈絡。
同情境英文四條提示在同頁。這是排版缺陷，不是資訊遺失。

修正方向：僅對可容納的短缺答群組與題目做連頁控制；不能讓所有 Q15 或
任意長回答都整塊不分頁，否則會重現長表格大片留白。
證據：[中文第 3 頁](empty-zh-3.png)、[中文第 4 頁](empty-zh-4.png)。

### 4. 短表格缺答提示的閱讀節奏仍需改善

英文 `Information not provided` 在 17% 預算欄折成三行，再接幣別或金額說明；
中文「幣別尚未提供。」也被拆到最後一行只剩「供。」。不是 parsing 漏字，
但視覺上像又多出數個短段落，提示比已填金額更搶眼。
可評估模板自有的短標籤、提示層級與儲存格配置，並讓中英文各自自然表達；
不得用一般字串替換去改作者回答。見 [英文](mixed-en-8.png)、[中文](mixed-zh-7.png)。

## 下輪驗收順序

1. 先修 Q7 部分填答的缺答可見性，建立欄位狀態／可達性測試；再逐題擴大。
2. 修短缺答群組孤頁與長預算缺答表頭，重跑此次中英文矩陣與完整填答控制組。
3. 檢查英文與中文固定用語及提示密度，不強求相同頁數或把減頁當成成功。
4. 真正修改仍在英文來源維護共用條件與呈現；中文沿用既有翻譯樹，精確鎖定
   英文 commit，再重新驗證 PDF／Word。這輪不新增分支、升版或聲稱已修好。

## 重現與界線

完整結果見 [機器報告](missing-info-report.json)。`all_renders_succeeded=true`，
但 `all_selected_content_checks_passed=false`、`all_selected_reading_checks_passed=false`。
這些缺陷是本次新增情境揭露的，不表示前一輪所選完整案例的報告被覆寫。

固定英文 `62338c59135d6067f492116964d58e31928a5d5a`，中文
`39a3a42da718d29b59513153b8a2b15c8f53701c`，工具
`25e339fbdfb1d20796471055790aad6a4226b6ed`；英中 ZIP hashes 見報告。
候選來源 `outputs/build-wnfydtta`，本輪 native `outputs/runtime-tables-pgueiskk`。
所有測試回答在 fixtures；大 HTML 留在 native 目錄，報告保存各檔 hash。

`audit.py` 建立／驗證八種情境，`extra_case.py` 增加 Q7 反例，`check.py` 產生
檢查報告，`collect.py` 核對後保存 native PDF 與 checksum。重跑要使用新目錄
與新的 runtime variant，不覆寫既有成品。只對自己建立的合成驗證專案做清理；
既有資料卷保留。本機 worker 已還原，四個測試服務已停止。

灰／黃提示是否易懂、所有十五題的全部條件分支、真實研究計畫與 Microsoft
Word 仍需後續驗收；本輪沒有對整份法規遵循或 Science Europe 實質內容背書。
