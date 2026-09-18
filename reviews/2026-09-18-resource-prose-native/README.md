# 0.3.41：Q15 固定敘述合段的原生驗證

英文共用模板已實作；中文循既有翻譯流程產生。這裡是原生 DSW 成品，
不是前一輪手改 HTML／DOCX 的離線試作。仍是實驗版，**不是整份 DMP 或
Microsoft Word 的正式驗收**，也未部署正式站。

## 先看成品

- 中文提交：[PDF](after/native/profile-partial-submission-chinese.pdf)、[可編輯 Word](after/native/profile-partial-submission-chinese.docx)、[Word 預覽](after/word-preview/profile-partial-submission-chinese.pdf)。
- 英文提交：[PDF](after/native/profile-partial-submission-english.pdf)、[Word](after/native/profile-partial-submission-english.docx)。
- 中文全空：[PDF](after/native/empty-submission-chinese.pdf)、[Word](after/native/empty-submission-chinese.docx)。
- [Word 修正前第 5 頁](visual/word-before-chinese-submission-p5.png)、[修正前第 6 頁](visual/word-before-chinese-submission-p6.png)、[修正後第 6 頁](visual/word-after-chinese-submission-p6.png)。

「不需要額外軟硬體」且已回答是否收費時，兩句固定敘述合成一段。
中文兩行變一行；英文仍可能兩行，但中間不再插一個段落間距。
原句、句號與兩項事實都保留，沒有補寫漏答，也沒有重寫自由文字。
中文提交 Word 的 Q15 標題與預算由第 5／6 頁改為同在第 6 頁，全文仍為 6 頁。
PDF 沿用上一版的有界短區塊連頁規則。

## 範圍及結果

四種公開合成案例（部分填答、全空、長篇且未填幣別、八筆預算），
兩種語言 × 內部檢核／提交預覽，共 16 組前後對照。
新增 48 份原生 HTML／PDF／DOCX 與 16 份 LibreOffice 預覽；封存前後
64 份 PDF／DOCX、32 份 Word 預覽、fixture 收據及 15 題內容快照。
HTML 僅保存題目內容及原始檔雜湊，避免重複嵌入整份字型。

限定檢查全部通過：15 題內容只有指定合段；Word 其他正文 XML、連結、
styles/fontTable/numbering 不變；原生 PDF 與 Word 預覽頁數、字型清單不變；
Q15 以前的正文文字座標不變；全空案例的全部正文座標不變。
既有字型度量框重疊記錄沒有增加，不把這種度量框直接當成墨跡碰撞。

中英翻譯分支 500 組（40 組合段）；原有 748 組譯文完全沿用。
兩個 prepared 字型版本各跑 130 組 escaping／結構檢查及 130 組
print／screen 前後排版檢查。全部歷史來源基準保留，先精確逆向還原
0.3.40 的來源與完整 prepared-source hashes，再跑原有檢查。

## 沒有忽略的擷取／檢查差異

- 長篇 Word 原來是 `FirstParagraph`／`BodyText`，短案例則是兩個 `PilotLead`。
  只在實際 reference 的段落與字元設定完全相同、且前者明確繼承後者時，
  才容許這組別名。第一段設定不改；其餘 XML 仍精確比較。
- 長篇合段後，有些用途段落提前到前頁；重複表頭因此插在不同文字位置。
  只排除續頁頁首的完整已知表頭／資源識別，首個真正表頭保留，再比較全文。
- 八筆預算有一列跨頁，PDF 的儲存順序可能先輸出金額／經費、稍後輸出用途。
  額外逐列消耗每個完整段落一次，要求金額與經費屬於正確列、用途段落順序不變；
  刪字、重複、錯列及用途倒序都有拒絕測試，不用字元總數掩蓋答案遺失。

初始檢查器不認得上述擷取差異的失敗報告保存於 `diagnostics/`，
修正的是檢查方法；原生候選套件始終相同，未為了讓測試通過重產另一套來源。
前一輪「中文檢核 PDF 離線基準字型不同」也未冒稱已修復；本輪直接比較
原生對原生，所有 16 組字型清單均相同。

## 仍需修正

**八筆預算的英文 PDF，第 7 列名稱與用途仍跨頁。**
[原版第 8 頁](diagnostics/many-en-before-page8.png)／[第 9 頁](diagnostics/many-en-before-page9.png)，
[新版第 8 頁](diagnostics/many-en-page8.png)／[第 9 頁](diagnostics/many-en-page9.png)。
內容沒有遺失，但續頁缺少該列名稱脈絡，不能稱為完整閱讀品質驗收。
下一個實驗應對「短的單列」設定有界連頁；長列則保留可跨頁與識別重複，
不能把整張長表強制綁在一起。

提示關閉仍只涵蓋既有提交預覽的明列範圍，不等於所有國科會繳交情境已處理。
真實代表性專案、Microsoft Word 實機、ODT／LaTeX 仍未在本輪驗收。

## 版本與重建

- 英文：`6ef78e859598d1c0866f9bbd71a066a4a1559341`，0.3.41。
- 中文候選：`abd0029e9b6efcba2a98dda6439fbb507881bc77`，0.3.41。
- 工具：`25e339fbdfb1d20796471055790aad6a4226b6ed`。
- 英文 ZIP：`5502b42d4562473cc47be0db5cae30a8a8aaf7f713df8a9d91a7675a86d2abe0`。
- 中文 ZIP：`3c43de03474df02a713c8a2a62905712ced09a81cdaec86e77cc1e55a375e971`。

乾淨候選 `outputs/build-fajoo5c3`；原生測試 `outputs/runtime-tables-2u5b7rav`，
基準 `outputs/runtime-tables-_78yhkvb`。精確指紋見 `provenance/`，
檢查器與來源片段見 `reproduce/`。使用本機 tables-only worker，未套字型實驗 patch。
已核對 ZIP 備份與零 project/document 引用，僅刪除此輪兩個暫存模板；
原廠 worker 已還原，四個 pilot 容器均停止，其他服務／volume 保留。

```bash
../dsw-document-template-tool/.venv/bin/python scripts/probe_metadata_gap_prose_scope.py \
  --build outputs/build-fajoo5c3 --english ../science-europe-template \
  --output-profiles --preservation-reading --short-resources --resource-prose
../dsw-document-template-tool/.venv/bin/python scripts/probe_resource_prose_translation.py \
  --build outputs/build-fajoo5c3 --english ../science-europe-template
../dsw-document-template-tool/.venv/bin/python scripts/check_resource_prose_outputs.py \
  --build outputs/runtime-tables-2u5b7rav --prior outputs/runtime-tables-_78yhkvb \
  --english ../science-europe-template --output outputs/resource-prose-new-check.json
```

報告禁止覆寫；重跑請用新的輸出檔名／新建置路徑。CI 成功也不等於上述未解項目已完成。
