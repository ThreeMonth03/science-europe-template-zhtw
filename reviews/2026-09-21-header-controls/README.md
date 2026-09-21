# 表頭試作：20 組基本原生控制，不是正式提交驗收

本輪完成五案例 × 中英 × 檢核／提交兩模式的 **20 組前後對照**。
基準與試作各產生 60 份原生 HTML／PDF／DOCX，另有共 40 份 LibreOffice
預覽。所有選定控制通過；英文來源、中文譯文及套件版號仍為 **0.3.42**，
沒有把試作收進英文來源、合併主線、發布或部署正式站。

## 結果

| 控制案例 | 英文 PDF，基準 → 試作 | 中文 PDF，基準 → 試作 |
| --- | --- | --- |
| 全空 | 4 → 4 | 3 → 3 |
| 部分填答 | 6 → 6 | 6 → 6 |
| 八筆短列 | 9 → 9 | 8 → 8 |
| 長回答缺幣別，另帶一筆短列 | 10 → 10 | 9 → 9 |
| 真正單筆長回答 | 10 → 10 | 9 → 9 |

表中每列均涵蓋檢核／提交兩模式。不是只比較頁數：

- 全部原生 PDF 的文字座標、字型、頁面邊界及逐頁影像相同；每側共 148 頁。
- 全部 Word 正文 XML、樣式、編號、字型與外部連結相同；全部 LibreOffice
  預覽文字座標及逐頁影像相同，並核對 DOCX 的完整段落可見。
- 八筆短列仍各自完整同頁。長案例的 60 個完整原段落各出現一次且順序相同，
  每張續頁保有名稱／金額／來源；最後用途及其支援項目同頁。
- 5000 缺幣別仍不代填幣別；明填 0 TWD 保留。相同的支援文字依各自資源列
  定位，不能拿另一列的同文充當內容保留證據。
- 全空的 15 題保留，沒有因缺答而整題消失。HTML 除未升版試作的那條 PDF CSS
  外逐位元組相同，沒有重譯自由回答或更動標點。

完整機械紀錄見 [comparison.json](provenance/comparison.json)。影像比較在同一
Poppler 25.03.0 下，以 72 DPI 對所有頁面計算；回歸測試重新驗證前後相等，
不要求其他作業系統產生同一個平台特定影像雜湊。

## 尚不能稱為正式提交版

全空提交版仍有 **20 個 `.data-gap` 系統提示節點**（檢核版 22 個）；
長回答缺幣別的提交版仍有一個。這是既有的提示開關範圍不足，本輪沒有新增
或隱藏它們。部分填答、八筆短列及單筆長回答的選定提交測資沒有此類節點，
但不代表所有問卷分支都已支援。使用者自己寫的「尚待補充」方法說明仍保留。

因此 **排版控制通過 ≠ 全空文件可繳交 ≠ 內容已完整**。
全域提交開關還需要另做提示來源／欄位狀態盤點；只移除模板生成的診斷，
保留已知事實與使用者文字，不把未填改寫成否定或承諾，也不靠全文字串刪除。

尾頁大量留白仍存在，並非這次修補造成，也沒有在本輪改善。
上一輪混合長列在最後的中文檢核試作 **9 → 10 頁**，仍是待評估取捨；
本批全部不變不能抵銷那個反例。

## 可直接檢視的樣張

- 中文單筆長回答：[基準 PDF](before/renders/budget-single-long-review-chinese.pdf)／
  [試作 PDF](after/renders/budget-single-long-review-chinese.pdf)／
  [試作 Word](after/renders/budget-single-long-review-chinese.docx)。
- 英文單筆長回答：[試作 PDF](after/renders/budget-single-long-review-english.pdf)。
- 中文部分填答提交：[PDF](after/renders/profile-partial-submission-chinese.pdf)／
  [Word](after/renders/profile-partial-submission-chinese.docx)。
- 全空中文提交的未完成範圍：[PDF](after/renders/empty-submission-chinese.pdf)／
  [第 3 頁](visual/header-control-empty-submission-zh.png)。
- 稀疏尾頁：[中文](visual/header-control-after-pure-long-zh.png)／
  [英文](visual/header-control-after-pure-long-en.png)。

## 重建、來源與清理

基準為乾淨建置 `build-06807ywr`：英文來源
`200fac5239051e1a877493c7d52c3a199964c718`、中文
`03e7fc7abc3b69cecfb9c8da69d6ce24f8ba5200`、工具
`25e339fbdfb1d20796471055790aad6a4226b6ed`。
試作的英中 ZIP 雜湊與[上一輪原生試作](../2026-09-21-native-mixed-header/README.md)
完全相同；配方多了 `--without-capture`，只改實驗 provenance，不改套件內容。

本批直接使用原生輸出；沒有擷取 PDF-entry HTML，也沒有從 HTML 匯出重建
PDF 後冒充原生結果。使用 tables-only worker，沒有 font-lifetime patch 或 observer。
所有答案先與本機編譯後 KM 的可達路徑核對；純長案例只移除既有測資的短尾列。
公開 KM 可由鎖定英文 repo 取回，雜湊記於每份 fixture 收據；不重複存入大型 KM。

封存的 `renders/*.html` 已把內嵌字型替換成 SHA256 引用，**不是可直接預覽的
原 HTML，也不是 PDF-entry HTML**。其 `.html.compact.json` 保存完整原檔雜湊，
測試使用鎖定工具的 Noto Sans TC 字型還原全部原始位元組。

Word 預覽第一次因批次名稱超過檔名上限，在產出預覽前失敗；工具已修正為
長批次名稱使用有界摘要，舊短名稱不變。基準完整重跑 20 份，試作分四批各
4／4／4／8 份，所有成功收據保留，沒有覆寫失敗成品或舊封存。

四個本輪暫存模板已確認零 project／document 引用後清除，ZIP 備份保留。
stock worker 已還原，四個指定 pilot 服務已停止；未刪其他模板、專案或 volume，
未讀取 keyring 或接觸正式站。見 [清理紀錄](provenance/worker-lifecycle.json)。

下一步補長列在前／中、三列分組與 32／33 列邊界的原生驗證，再決定是否把
表頭修正收回英文共用來源升版，中文繼續走既有轉換流程。
完整提交模式、真實專案與 Microsoft Word 實機仍須另驗收。
