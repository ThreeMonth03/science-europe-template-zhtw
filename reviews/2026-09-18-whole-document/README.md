# 0.3.37 中英整份 DMP 閱讀稽核

日期：2026-09-18。結論：**不能把「每題都有文字」當作「每题都交代完整」。下一個最小修正應先處理 Q6 的部分缺答提示，接著 Q8，再處理跨頁與段落節奏。** 本輪只保存稽核與工具，不改模板、譯文、英文 lock 或套件版號，不發布／合併，也未使用正式 DSW。

## 看了哪些成品

| 案例 | 真正代表的情境 | 英文 PDF / Word 頁數 | 中文 PDF / Word 頁數 |
| --- | --- | --- | --- |
| `metadata-complete` | Q3 指定追問有答，包括兩個明確 No；其他題目仍會漏填，**不是完整 DMP** | 6 / 6 | 6 / 6 |
| `metadata-partial` | 同一基礎案例，Q3 部分追問／容量缺漏 | 6 / 6 | 6 / 6 |
| `narrative-long` | 兩個提供管道，其中受限管道含刻意輸入的 80 段長文；分頁壓力測試，非自然敘事範例 | 9 / 8 | 9 / 9 |

Word 指原生 DOCX 經 **LibreOffice 25.2.3.2** 產生的預覽，並非 Microsoft Word。
合計 83 個實體頁面（含封面）；做逐頁概覽、文字核對及兩處問題的 115 dpi 近看，**不是逐字人工校對或正式驗收**。
詳見 [逐頁紀錄](page-ledger.md)、[輸出與輸入對照](inventory.json)、[窄範圍機器觀察](observations.json)。

- 前兩例沿用上一輪 **同一組 0.3.37 ZIP** 的 12 個原生輸出，不冒充本轮新生成。
- 本輪新生成 `narrative-long` 的 6 個原生輸出（兩語言 × HTML/PDF/DOCX）和兩份 Word 預覽。
- 保存六份 PDF、六份 DOCX、六份 Word 預覽、抽取的題目 HTML、固定 fixture、來源與引擎紀錄。原生完整 HTML 含內嵌資產，僅保留其 hash 及題目抽取內容。
- 12 份分頁文件都有 15 個題目標題；長文在四份 PDF／Word 預覽皆保留依序 [01]–[80]，各一次。六份 Word 預覽通過原生 DOCX 段落文字保留檢查。這些檢查**不證明 SE 符合性或所有已填答案都已映射**。
- 12 份文件的文字 bounding box 未超出紙張；六份 Word 預覽另查同一文字區塊內的行重疊。這不等於跨區塊全面無重疊保證。

## 優先問題與責任層

### WD-01 / P1：Q6 有安全措施，卻沒提醒存取控制漏填

三個案例、兩種語言都重現。`metadata-complete`：英文 PDF p4、Word p3；中文 PDF/Word p4。
本地編譯 KM 確認 `sharedWorkspaceQUuid = Yes`，其有效追問 `sharedAccessControlQUuid` 沒有回答；風險探索也已啟用，遺失／外洩／破壞追問沒有回答。
輸出卻只有不攜出資料、HTTPS、風險說明等敘述，沒有部分缺答提醒。

這是**输入未填 + 英文 Jinja 部分缺答提示不足**，不是翻譯漏句，也不是已填存取控制答案被丟掉。
[來源 Q6](source/06-access-security.html.j2) 只在整個 `answerContent` 空白時顯示兜底提示；有其他敘述就不觸發。不得因此推論所有安全細項都已交代。
對照 SE-3b：不能以 HTTPS 敘述代替「谁可以存取／如何控制」；備份交叉參照也不能代替此回答。

最小修正：只針對已啟用而漏填的存取控制追問新增 fact-level 提示，保留已有安全敘述。風險評估、事故復原與機構政策應另做欄位映射審查，不能這次順便假設全有對應。

驗收至少涵蓋：共享空間 Yes＋追問缺漏、每個有效存取控制選項、共享空間 No／父題未填、未知選項、整題空白、只有 Q5 交叉參照。No 不得被寫成 missing；未知選項不得當作已回答。中英 HTML/PDF/DOCX 與 Word 預覽必須都能辨認缺漏，且已填文字不減少。

### WD-02 / P1：Q8 的第三方授權蓋過新資料權利歸屬缺漏

三個案例、兩種語言都重現；前兩例的中英 PDF/Word 都在 p4。
`ownershipQUuid` 是可達的章節根問題，但 fixture 未填。Q8 仍列出兩筆既有資料的 CC BY 使用條件，整題不空白，所以不提醒新資料權利歸屬尚未交代。
[來源 Q8](source/08-copyright-ipr.html.j2) 的所有權分支沒有缺答分支，整題兜底無法處理此狀況。

責任層同 WD-01：**先修英文輸出邏輯，再沿現有管線產生中文**。對照 SE-4b：第三方資料再用限制與本計畫資料權利歸屬是不同議題。這裡不是提供任何法規結論，也不把模板輸出當法律審查。

驗收：權利歸屬未答＋再用授權已答；明確無權利人；PI／機構／協議；Other 有／無內容；無再用資料；未知值。不能把明確無權利人誤寫成未填，也不能刪掉第三方授權。獨立於 Q6 做一個小迭代。

### WD-03 / P2：英文 Word 有孤立章節標題

`metadata-complete` 英文 Word p3 最後一行是 Section 4，第一題 Q7 在 p4；其他 11 份分頁文件沒有這個「章節標題和首題分頁」觀察。
見 [p3 近看](visual/metadata-complete-english-word-orphan-p3.png)。這是**Word 分頁規則**，不是解析遺失。即使 Heading 樣式宣告 keep-with-next，也不能以樣式存在代替實際渲染確認。

後續先診斷章節標題與首題間的原生 Word 段落；有界限地讓標題連同第一個題目／答案開頭，而不是鎖住整章。驗收必須包含此例及短／長／空白對照，實際數出標題與首題頁碼，並確認沒有放大成整頁空白。

### WD-04 / P2：中文 PDF 的短預算表獨占尾頁

`metadata-complete` 中文 PDF：Q15 p5，預算標題和兩列獨占 p6；`narrative-long` 中文 PDF：Q15 p8，兩列獨占 p9。
見 [p6 近看](visual/metadata-complete-chinese-budget-tail-p6.png)。同例中文 Word 沒有同樣問題；`metadata-partial` 中文 PDF 的 Q15 與表格都在 p6。

這是**PDF 的整體分頁／保留區塊取捨**，不是丟字。先比較 bounded 的「短 Q15 文字＋短表格」安排與自然流排，不直接減字号、刪答案，也不要對不限長度的整題加強制 keep。
驗收比較整份文件：不要僅為減一頁而造成前頁大片留白；金額 5000、明確 0、TWD、兩筆用途與來源必須完整，長預算仍可正常跨頁。

### WD-05 / P2：模板敘事仍像表單拼接，中英文都需要整理

所有案例 p2 的 Q1 都可見：資料集→儀器→引導句→品質措施，加上每筆來源的版本小表，內容雖正確但節奏很碎；品質句還在 Q4 再出現。
共同管理方式先說「上述資料集」，接着反覆「此資料」；英文也從 all reference datasets 轉回 this dataset。
Q14 的英文 management and proficiency of data 本身不自然，不能只要求中文翻得更順。

責任分開：

- 英文 Jinja：模板自有的段落／共同敘述可在保持資料集範圍下重組；不要跨不同管道／授權合併，也不要刪使用者自由文字。Q1 的品質摘要和 Q4 可用簡短交叉參照設計，但需另驗證導覽與輸出目的，這次不直接刪除。
- 中文翻譯：在同一語意單位內用完整中文句子；例如共同管理段落可用「本計畫將保留上述資料集的副本，與研究結果一併提供。使用時須註明來源，無須轉換格式。」這只是提案，尚未改譯文。
- 標點：模板生成清單統一名詞列舉／完整句規則，不對整份成品做全域句號或逗號替換，避免破壞 URL、識別碼、數值與原始回答。
- 輸入品質：預算的「資料可尋性／寄存檔案」來自 fixture 的自由文字；80 段重複也是刻意輸入，不歸咎翻譯器，不在模板偷偷潤飾。

因此這次的結論不是「中文不通」；主要是模板自有的主詞、標籤、重複內容與跨頁脈絡讓連續閱讀費力。應做具體前後頁面對照，不靠全段重新翻譯解決。

## Science Europe 15 題的閱讀層對照

依專案固定的 [2021 Extended Edition](https://scienceeurope.org/media/4brkxxe5/se_rdm_practical_guide_extended_final.pdf)，不是宣稱已比對最新政策。下表是這三組輸出的觀察與不足，**不是符合性打分**；`pinned-requirements.json` 的舊 implementationStatus 也不拿來當現在的驗收結論。

| 題目 / SE ID | 這次看到的內容 | 尚不能據此主張 |
| --- | --- | --- |
| Q1 / 1a | 儀器、兩筆再用來源、用途、版本、溯源 | 所有 KM 方法／來源分支都被涵蓋；也不能把三筆不同階段資料自行合併 |
| Q2 / 1b | 格式 CSV UTF-8、120 GB、設備蒐集 | 其他資料型態或各資料集格式皆已完整說明 |
| Q3 / 2a | Dublin Core、檔名、字典／公開與擷取選擇，缺漏與明確 No 分開 | metadata-complete = 內容品質完善；標準名稱本身也不等於文件充分 |
| Q4 / 2b | 校正、輸入檢核 | 僅列方法即有可執行程序、責任人、標準與頻率 |
| Q5 / 3a | 工作空間、備份，長例另有磁帶／異地封存；地點和排程不足有提醒 | 需要頻繁備份 = 已有排程；備份安排 = 事故復原計畫全部完成 |
| Q6 / 3b | 攜出、HTTPS、風險說明；长例有 Q5 參照 | 存取控制、事故復原、風險與政策均完整；WD-01 |
| Q7 / 4a | 明確不蒐集個人資料 | 個資相關其他分支／法規已驗證；不從「沒填」推出「沒有個資」 |
| Q8 / 4b | 兩筆第三方資料再用條件 | 本計畫新資料權利歸屬已回答；WD-02 |
| Q9 / 4c | 問卷的倫理審查、個資／敏感資料與倫理法規選擇 | 無個資即可推論免倫理審查；本例否定是獨立輸入，不是該推論 |
| Q10 / 5a | 公開／受限管道、授權日期、受限自由文字和申請方式 | 授權起日必然等於實際發布日；80 段壓力例可代表一般寫作 |
| Q11 / 5b | 10 年、各管道存放地、維運缺漏與保存選擇提醒 | 發布決定已說明哪些版本必須保留或銷毀 |
| Q12 / 5c | 合成軟體名稱、版本與網址 | 連結存在 = 軟體可長期維護；所有取用机制已在此題交代 |
| Q13 / 5d | 各管道 PID 指派／解析、再用可能性 | 已取得 DOI；機構資料託管員一定會指派 DOI |
| Q14 / 6a | 範例團隊角色對應的責任敘述 | 各任務與跨機構分工、實際定期修訂安排均已清楚 |
| Q15 / 6b | 培訓、硬體、儲存庫費用、兩筆預算與來源 | 已有充分成本理由、完整工時估算；表格有金額不代表實施足夠 |

上述只是讀到的範圍。要回答「填很多但輸出太少」的全貌，還需要逐條追蹤 **已填且可達的 KM 答案 → 成品位置或不輸出的合理原因**；本輪沒有完成 592 個 KM 問題的動態覆蓋測試。兩份公開 KM 的 592 問題可達清單是路徑資料，不是 592 問都已在輸出驗證。

## 來源、版本與重現邊界

- 英文來源：`0730b11c4027fcc020c441a3c36264d85649321c`；中文起點：`f6d80789db488e7cfefcb5abbe948944a373785a`；工具來源：`25e339fbdfb1d20796471055790aad6a4226b6ed`。
- 英文 ZIP SHA256：`45f9f3c20e37b9f6b0181addd28a7128dabb18f23471c0d4caf2b451f39d302d`。
- 中文 ZIP SHA256：`675a6b15ef5aeca8510fc4c55e53892e447e5ea1e67e8c96024607e62486557c`。
- 早先產製起點有 QA-only commit 差異，完整重建 manifest 與 ZIP hash 在 `provenance/rebuild-manifest.json`；不能只看相同版號推定同成品。
- SE PDF 本地 hash：`0a5902705feda840f5e5ded0d70bf6831ed8b3cf092fa65ed0673c0cf3cc911f`；主要核對印刷頁 17–25，其中 WD-01 p20、WD-02 p22。DOI：`10.5281/zenodo.4915861`，CC BY 4.0。
- 本輪 6 次渲染使用同一個 tables-only docworker，前後 container/image/start/restart 記錄相同。未用字型變體，未測 stock／正式 worker 相容性。
- 清掉兩個本輪自有暫存模板前已確認無專案／文件參照，ZIP 備份驗證保留。另清掉兩個公開 KM 盤點專案；恢復 stock worker，僅停止四個本機 pilot 服務，保留 volumes/outputs。沒有讀取正式站憑證。
- `review/whole-document-0.3.37` 是短期稽核分支，不是新維護線／新模板版。未改 747 組譯文、來源 lock、Jinja、CSS、Lua 或 Word reference。下一輪從目前修補線接 Q6 的小修補分支，通過中英輸出對照後才更新來源 lock；不另養中文 Jinja。

重現需要既有兩批輸出、相同 fixtures 和 Poppler、python-docx、BeautifulSoup、Pillow。Word 預覽已先按 `preview_word_short_budget.py` 產製；收集器不會自己呼叫正式服務。

```bash
../dsw-document-template-tool/.venv/bin/python scripts/collect_whole_document_review.py \
  --baseline outputs/runtime-tables-k9uy2oe9 \
  --fresh outputs/runtime-tables-nm7ao4rs \
  --english ../science-europe-template --output outputs/new-whole-document-review
../dsw-document-template-tool/.venv/bin/python scripts/review_whole_document_facts.py \
  --review outputs/new-whole-document-review
```

收集器第一版曾假設所有 `.question` 都直接有 `data-requirement-id`，實際不成立；已改為從固定 SE 清單依題號對應，並另保存真實 HTML attribute（可能缺省），不假造原始標記。第一次失敗的本機收集目錄保留為 `outputs/whole-document-review-0.3.37-trial-missing-attribute`，不是成功證據。

## 下一輪的完成定義

本輪本機單元測試 236 個通過（含五個新的稽核證據測試），不是 236 項 DMP 符合性檢查。
原實作分支的 CI 狀態另存 [檢查時間與 commit](ci-status.json)：英文成功；中文當時仍在執行。
先前中文失敗的 Word run-format 檢查已有修正，包含在目前 `f6d8078` 版本；不把舊失敗當作新問題，
也不在最新 run 結束前宣稱已全綠。本稽核分支 `review/**` 不在 push trigger 清單內。

先只修 **WD-01 的已啟用存取控制追問漏填**，用這三例當前後基準，再新增父／子題組合與未知值對照。完成代表已填答案保留、漏填明示、不適用不誤報，且兩語言 PDF／Word 都能正常閱讀；不是把 Q6 全部 SE 要求打勾。
接著 WD-02，再依 WD-03/04/05 個別修補。真正發布還需要自然、去識別化的完整研究案例／領域審閱、實際 Microsoft Word，以及目標部署 worker 驗收；本輪沒有解除這些門檻。
