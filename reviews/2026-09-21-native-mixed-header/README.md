# 原生混合預算：確定原因、八組前後對照與未升版試作

**這是原生試作，不是 0.3.43，不是正式發布。** 英文來源、中文譯文、pipeline
來源鎖仍為 0.3.42。試作由精確鎖定的套件另存產生，只供本機合成資料使用；
沒有部署正式站，也沒有取用正式憑證。

## 已確定的兩件事

1. 前次離線基準漏了原生 PDF 的格式專屬 CSS。工具鎖定版本的
   `localization.py` 只在中文檢核 PDF 的 UUID 下加入 CJK fallback 與 typography，
   包括字重 600 與行高等規則。從 HTML 格式匯出重建 PDF 不會帶入這些內容，
   中文提交格式也不觸發同一層。不是已證實的字型快取或 worker lifetime 問題。
2. 在真正的中文檢核原生輸出中，WeasyPrint 68.1 第 9 頁確實走到
   `all_groups_layout` 第 529 行：有表頭，但帶表頭的 body 試排回傳空，
   引擎省略表頭後重新排入剩餘文字。`before/trace/` 保存原生觀測紀錄。

`capture.py` 原樣呼叫原本的 DSW conversion step，不改 document、options 或引擎。
使用真正擷取的 PDF-entry HTML 後，離線 baseline 與該份原生 PDF 的所有
文字座標、頁數及字型清單完全相同，也重現第 9 頁缺表頭。
[輸入差異證據](provenance/input-difference.json)、[格式專屬 CSS](provenance/native-review-extra-css.css)。
前次封存資料與缺陷紀錄均保留，不回填成「早已通過」。

## 試作做了什麼

同一個可逆套件配方套入英文／中文，不另寫中文回答邏輯：

- 普通混合分組接回既有、有上下限的短列連頁 helper。
- 已展開的長列 tbody 使用目前引擎的保留表頭分支；長回答仍可跨頁。
- 長資源用途的最後片段與後面的支援項目接續，避免只剩支援項目一行。

修改限定在 `budget-reading.html.j2` 及 PDF 長資源表專用 CSS；每份原生 PDF
輸入反向移除這些精確屬性／規則後，必須逐位元組等於原生基準。
沒有改問題、譯文、原回答、標點、金額、幣別、字型或 Word 邏輯。
明填 0 或 900、缺幣別與缺用途等情境仍保留原狀；不代填、不推定承諾。

## 八組原生結果

| 案例 | 基準 → 試作頁數 | 結果 |
| --- | --- | --- |
| 長列在最後，英文檢核／提交 | 11 → 11 | 短列完整同頁、續頁識別完整 |
| 長列在最後，中文檢核 | **9 → 10** | 原第 9 頁缺表頭已消除，但增加一頁 |
| 長列在最後，中文提交 | 9 → 9 | 短列完整同頁、續頁識別完整 |
| 混合漏填，英文檢核／提交 | 11 → 11 | 保留內容、幣別未知與明填金額 |
| 混合漏填，中文檢核／提交 | 10 → 10 | 支援項目回到最後用途片段同頁 |

全部八組短列完整同頁，長列各續頁有完整名稱／金額／經費來源；所有原文字
及每列內容一致，Q15 以前文字座標與字型不變，沒有新增頁外或底部邊界侵入。
兩語言的八組 Word 正文 XML、樣式、字型、編號及連結不變；16 份 LibreOffice
預覽逐頁文字座標一致，且與原生 DOCX 段落核對。這不是 Microsoft Word 實機驗收。

原生樣張：

- 中文檢核：[基準 PDF](before/native/mixed-long-last-review-chinese.pdf)／[試作 PDF](after/native/mixed-long-last-review-chinese.pdf)。
- 中文提交：[試作 PDF](after/native/mixed-long-last-submission-chinese.pdf)。
- 中文漏填提交：[試作 PDF](after/native/mixed-gaps-submission-chinese.pdf)／[Word](after/native/mixed-gaps-submission-chinese.docx)。
- 英文檢核：[試作 PDF](after/native/mixed-long-last-review-english.pdf)／[Word](after/native/mixed-long-last-review-english.docx)。
- 中文檢核：[第 8 頁短列](visual/chinese-review-08.png)、[第 9 頁續頁表頭](visual/chinese-review-09.png)、[第 10 頁尾段](visual/chinese-review-10.png)。

沒有把多一頁淡化成無退步：最後一頁雖不再只剩一行，仍有大量留白。
完整重播另外保留僅短列、僅 tbody、兩者、短列＋尾句及三者合併等六種對照。
僅接短列會在第 10 頁單獨留下支援項目；尾句規則把最後用途及清單帶過來，
但不會憑空省掉一頁。預覽 UI 曾造成表頭位置誤判；實際 PDF 座標確認沒有裁切，
這不是新增的「表頭跑版」缺陷。

## 下一輪才決定是否收回來源

1. 增加全空、部分填答、純長列、純多列、長列前／中／後、3 列分組及超限
   的原生控制組；本輪只有六組分組／上限結構測試，不能替代這些原生驗證。
2. 評估多一頁與尾頁留白的取捨；不得用刪回答、縮字到難讀或硬塞頁面來過關。
3. 通過後才修改英文 repo 的共用來源、升版並鎖定 commit，中文由現有流程產生；
   這份套件配方是實驗，不變成永久第二套英文／中文來源。
4. 把「格式 UUID 下的 CSS 層」列入未來版本檢查。若要統一檢核／提交排版，
   必須另做前後對照；本輪沒有更改工具、字型策略或漏填提示的關閉範圍。

## 重播、失敗收據與清理

封存 `pdf-input/` 與 `html-input/` 把大型嵌入字型替換為 SHA256 引用，不能直接
拿來預覽。使用鎖定工具的公開字型還原，整份 HTML 必須與原始 SHA256 相同：

```sh
../dsw-document-template-tool/.venv/bin/python scripts/restore_captured_pdf_input.py \
  --input reviews/2026-09-21-native-mixed-header/replay/captured.input.html \
  --font ../dsw-document-template-tool/src/dsw_document_template_tool/resources/fonts/NotoSansTC-Variable.ttf \
  --output outputs/restored-mixed-header/captured.html
```

`reproduce/` 留有觀測／試作／檢查程式快照；工具固定
`25e339fbdfb1d20796471055790aad6a4226b6ed`，英文固定
`200fac5239051e1a877493c7d52c3a199964c718`。
首次試作因本機 DSW 配額不足失敗，保留 failed report 與 log；只清除本輪
已完成、無引用且有 ZIP 備份的基準暫存模板後重試，沒有提高或繞過配額。
Word 預覽先完成六份、最後兩份另補跑；兩份收據都保留，沒有宣稱首次批次完整。

四個本輪暫存模板均已清除，ZIP 備份保留；stock worker 已還原、observer 已移除，
四個 pilot 服務已停止。沒有刪其他專案、模板、volume 或其他 stack。
**限定檢查通過不代表整份模板、任意真實專案或國科會正式提交已驗收。**
