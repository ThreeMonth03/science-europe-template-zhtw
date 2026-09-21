# 大量資源分組試作：33 筆長列恢復可讀，尚未整合來源

本輪補足前輪 Word 的原文證據，並在原有表頭試作上加入大量資源處理。
八組中英／兩模式原生對照完成；新增 24 份 HTML／PDF／DOCX、8 份 LO 預覽。
這不是正式發布，英文來源、748 組中文譯文與版號仍維持 **0.3.42**。

## 原生成品結果

| 案例 | 原生 PDF：前 → 後 | Word／LibreOffice：前 → 後 |
| --- | --- | --- |
| 32 筆英文，兩模式 | 14 → 14 | 15 → 15 |
| 32 筆中文，兩模式 | 12 → 12 | 13 → 13 |
| 33 筆英文檢核 | 15 → 14 | 18 → 16 |
| 33 筆英文提交 | 15 → 14 | 17 → 15 |
| 33 筆中文，兩模式 | 13 → 12 | 16 → 14 |

32 筆控制組的 PDF／Word 正文及逐頁影像完全相同。
33 筆原生 PDF 的短列不再拆頁，長用途改為全寬；PDF／Word 每張長列續頁
保留原有名稱、金額及經費來源，60 段用途均完整，最後用途與支援項目同頁。
PDF 與 Word 的 Q15 之前文字座標相同，沒有改動前面章節來換取減頁。

所有原有欄位文字、大小寫、標點、零金額及順序核對保留。
Word 的前 32 筆原列 XML 保留，長列原段落／文字 run／清單 XML 原樣搬至
全寬單元；只增加重複識別表頭、必要空表格分隔段與既有長表樣式。
Word 樣式檔、字型、編號及外部連結不變，HTML 匯出也完全不變。
見 [八組比較](provenance/comparison.json)。

## Word 未確認段落已補上證據，不改寫舊紀錄

[前輪封存](../2026-09-21-mixed-boundary-controls/README.md) 的失敗診斷仍原樣保留。
本輪另對該輪 **40 份 Word 預覽**核對：DOCX 原表格內容對應 HTML 原欄位，
再依 PDF 實際字框位置、唯一資源名稱與完整欄名分配每一行文字，核對每列
三欄的完整內容及順序。跨頁句子允許跨頁，不允許從另一列借同文補足。

只有頁首、且完整符合原名稱／金額／來源的長列重複識別表頭才可扣除；
不任意刪除字詞、不把全篇文字重排後假裝連續。非預算段落仍沿用完整段落核對。
反向測試涵蓋刪字、重複、改標點、金額換欄、缺表頭與交換資源，均會失敗。
結果見 [新原文證據](provenance/prior-word-cell-proof.json)。

此檢查限定於公開合成測資的單行唯一資源名稱與三欄結構，**不是通用 PDF
解析器**，也不代表文字已寫得自然或版面已全部驗收。

## 修改邊界與安全控制

原本 PDF 與 Word 都以整表 32 筆為上限，超過便不展開任何長用途。
新試作取消這個整表門檻，改為保留逐筆內容／字數／結構限制，
將需要輸出的普通短列表格每組限制在 32 筆。不是把上限改成另一個大數字。

- PDF：長列仍用原分類器，普通列仍輸出原捕捉片段；大普通分組切成最多
  32 筆，再交給既有短列規則。長度／不認得的標記等逐筆保護不變。
- Word：仍先檢查整張表的欄數、跨欄、段落、清單、行內內容與字數；
  不合格就保留原表。通過後才展開長列、分組普通列。
- 37 組 Pandoc AST 比較保留原段落／屬性，只接受明列結構差異；包含舊有
  圖片、巢狀清單、巢狀表格、強制換行、過長段落、過長標題等反例，以及
  大表中的不合格經費／用途。純短大表不因這次長列試作被改動。
- PDF 分組驗證涵蓋 32、33、34、64、65、66 筆；普通分組最多 32 筆、
  資源順序與欄名保留。這六組是結構檢查，**不是額外六組原生成品驗收**。

見 [結構報告](structure/report.json)。所有 ZIP 其他檔案／資產與 metadata
均核對不變；只有 `src/budget-reading.html.j2` 與 Word 的 Lua 資產改動。
`package/` 保存修改前後的精確內容，測試重算反向還原，不以差異行數代替驗證。

## 可檢視樣張

- 中文 33 筆：[PDF](after/renders/mixed-bound-33-last-review-chinese.pdf)／
  [Word](after/renders/mixed-bound-33-last-review-chinese.docx)／
  [Word 預覽](after/word-preview/mixed-bound-33-last-review-chinese.pdf)。
- 英文 33 筆：[PDF](after/renders/mixed-bound-33-last-review-english.pdf)／
  [Word](after/renders/mixed-bound-33-last-review-english.docx)。
- 續頁例圖：[中文 PDF](visual/large-resource-native-zh-p11.png)／
  [中文 Word](visual/large-resource-word-zh-p13.png)／
  [英文 PDF](visual/large-resource-native-en-p13.png)。
- 原基準：[中文 PDF](../2026-09-21-mixed-boundary-controls/after/renders/mixed-bound-33-last-review-chinese.pdf)／
  [中文 Word 預覽](../2026-09-21-mixed-boundary-controls/after/word-preview/mixed-bound-33-last-review-chinese.pdf)。

## 仍未完成

英文 Word 第 9、18、27 筆短列的支援敘述仍拆段跨頁，兩種模式前後相同；
新試作只修長列，不把這項舊問題標成通過。尾頁留白也尚未平衡。
本輪沒有修改中文譯文，不宣稱完成語氣與全篇閱讀審查。

全域提交提示開關仍獨立待辦：前輪全空提交有 20 個系統提示節點。
隱藏提示必須保留已填資訊與使用者自寫文字，不把缺答改成已完成。
尚未使用真實專案，也沒有 Microsoft Word 實機驗收。

下一步將已驗證的表頭／長列分組範圍整理回英文共用來源，再用既有流程
重建中文；正式來源版本與部署另行處理。英文 Word 短列與全域提交提示
仍需獨立修正，不能用這批改善代替。

## 來源與清理

基準是前輪未升版表頭試作，不是未修改的 0.3.42；以
[baseline-reference.json](provenance/baseline-reference.json) 綁定其封存校驗值。
原英文來源 `200fac5239051e1a877493c7d52c3a199964c718`，工具
`25e339fbdfb1d20796471055790aad6a4226b6ed`；本輪開始時中文 repo 為 `14b0569`。
基準成品直接引用舊封存，不複製後覆寫或重新封印舊紀錄。

本批於 localhost tables-only worker 原生匯出，沒有 PDF-entry observer、
沒有拿 HTML 匯出假冒 PDF 入口重播。封存 HTML 的嵌入字型以 SHA256 引用
縮存，測試使用鎖定工具字型還原所有原始位元組。LO 25.2.3.2、
Poppler 25.03.0 下核對前後；逐頁像素檢查只要求同一平台前後相同。

兩個本輪暫存模板確認零 project／document 引用後清除，ZIP 備份保留。
stock worker 已還原，四個指定 pilot 服務已停止。未刪其他模板、專案或
volume，未讀取 keyring，未接觸正式站。見 [清理紀錄](provenance/lifecycle.json)。
