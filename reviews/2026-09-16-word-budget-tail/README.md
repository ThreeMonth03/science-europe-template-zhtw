# Word 尾頁留白：未採用的分頁實驗

結論：中文混合缺答案例確實有閱讀斷裂，但只改局部分頁規則，沒有解決
整體留白。這輪保留 0.3.26 模板，不把試算 DOCX 當成新版原生輸出。

## 先看中文第 7、8 頁

| 對照 | 結果 | 預覽 |
|---|---|---|
| 原版 | Q15 說明在第 7 頁，預算標題與三列資料在第 8 頁 | [PDF](trials/budget-mixed-gaps-chinese-baseline.pdf) |
| 取消預算標題連頁 | 標題留在第 7 頁，表格仍在第 8 頁，產生孤立標題 | [PDF](trials/budget-mixed-gaps-chinese-release-budget-heading.pdf) |
| 取消表內資源名稱連頁 | 第一筆名稱／用途在第 7 頁，支援項目移至第 8 頁，失去直接歸屬 | [PDF](trials/budget-mixed-gaps-chinese-release-table-labels.pdf) |
| 整題說明連頁 | Q15 說明和表格同在第 8 頁，但第 7 頁下半部更空 | [PDF](trials/budget-mixed-gaps-chinese-keep-overview.pdf) |

四份中文都是 8 頁；四份英文都是 7 頁。整題连頁是可討論的閱讀取捨，
不是節省一頁或整份留白已修復。這次不採用三種改法，也不擴大既有 Lua
短表格的列數、字數和段落上限。

## 檢查範圍

部分漏填、三筆混合缺答、完整填答各有中英兩份，乘以四種對照，共
24 份凍結 DOCX 複本及 LibreOffice PDF 預覽。六份 baseline 與上一輪
Word 預覽的逐頁文字座標完全相同，排除這次重開 LibreOffice 的基準漂移。
所有對照保留答案、漏填提示、0 TWD、字級、行距、欄寬、段落與表格結構；
只允許指定段落新增 direct `keepNext` 屬性。其餘 DOCX 套件項目逐位元相同，
正文段落亦核對可在預覽找到。沒有以降低字級或刪除文字減頁。

`trials/report.json` 記錄每份 hash、頁數、題目／表格／資源首尾的頁面位置。
同文段落可能有多個匹配頁，因此頁碼追蹤不是通用的唯一歸屬證明；上述
混合缺答拆列反例另經逐頁目視確認。`audit.json` 保存基準座標檢查與字型
實際替代檔案：此環境 Arial 使用 Liberation Sans，中文使用 Noto Sans CJK TC。
這不是 Microsoft Word 實機驗收，也沒有新跑原生 PDF 或 DSW worker。

初版工具把英文標題誤認為沒有連字號，選取檢查即停止、尚未產出試算文件；
失敗報告和工具在 `diagnostics/failed-first-trial/`。第二次 24 份試算完成，
但只追蹤資源名稱，未充分呈現跨頁拆列；其報告、工具、全部檔案 hash 保留在
`diagnostics/earlier-trials/`，完整複本仍在本機 outputs。最後加入用途欄末段
追蹤後另跑 24 份，不覆寫前兩次記錄。名稱追蹤不足不能當作內容未拆散的證據。

## 接下來的實驗邊界

先回到整份中英的閱讀密度，優先檢查 Q13 的固定識別碼敘述及 Q15 的
培訓／資源敘述：分清「模板自己的短句」與「使用者自由回答」。只有語意
本來屬於同一單位的固定句子才考慮合併；中文用完整句序及標點，英文也要
自然。不可把兩個不同儲存庫、不同資料集或缺答／否定狀態合併推論。

要採用新規則，仍須在英文來源實作、經既有翻譯樹產生中文，再驗證中英
空白／部分漏填／完整／長回答與多筆資料的原生 PDF、DOCX 和整份頁面。
這輪只增加診斷及回歸反例，未修改 Jinja、Lua、翻譯樹、版本鎖或套件版本，
沒有新增中文邏輯分支；也没有讀取 keyring、啟動 pilot 或操作線上 DSW。

重跑方式（需本機既有 0.3.26 原生輸出與 LibreOffice）：

```sh
../dsw-document-template-tool/.venv/bin/python scripts/rehearse_budget_tail.py \
  --prior outputs/runtime-tables-9e0w9xp1 \
  --output outputs/word-budget-tail-NEW
```

輸出目錄必須全新；既有證據不覆寫。`reproduce/` 保存工具及版本鎖，
`checksums.json` 覆蓋此審閱資料夾內所有其他檔案。
