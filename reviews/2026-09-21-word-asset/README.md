# 共用 XML 資產接通；完整翻譯演練修正兩個格式回歸

承接 `2026-09-21-word-short-tables`，舊封存不改寫。本輪仍是 0.3.44 的隔離
原型及完整來源演練，未修改英文來源、正式中文翻譯樹、pipeline lock 或版號。

## 原生資產路徑已驗證

同一份機器 XML helper 改從 `.xml.j2` 模板文字，移到 `.xml` 共用資產；
只改兩個 Word 格式的載入路徑，helper 字節、Lua、字型、CSS、reference DOCX
及舊資產完全不變。TDK 實際將 `.xml` 分類為 `application/xml` 資產。

漏填／已回答／長文 × 中英 × 檢核／提交，共 12 組原生 DSW 比較：

- 新產出 36 份 HTML／PDF／DOCX 和 12 份 LibreOffice Word 預覽。
- 全部 HTML 字節相同，PDF 與 Word 預覽逐頁座標／影像相同。
- 全部 Word ZIP 組件相同，僅允許有效建立／修改時間不同；正文、超連結、
  表頭、列屬性、樣式及作者原文不變。
- 四張長文案例中的短表仍完整同頁：中文檢核第 8 頁、英文檢核第 6 頁，
  中文提交第 6 頁、英文提交第 5 頁。沒有改動前輪已驗證的長表規則。

可直接查看[中文長文 Word 預覽](after/word-preview/ethics-long-review-chinese.pdf)
及[中文長文提交 PDF](after/renders/ethics-long-submission-chinese.pdf)。
這是 DSW 原生轉換，不是下載後加工 Word；也不代表 Microsoft Word 已驗收。

## 完整來源翻譯：先失敗，再修正

除了最小 helper 測試，這次從完整英文來源開始，實際執行 layout preparation、
展開、譯文遷移、同步、結構 audit 與中英 TDK verify/package。
英文共用來源承接前輪五個 Jinja 檔及兩個 Word helper；機器 XML 不再產生譯句。

第一版雖能建置，但 3,312 組結構比較有 **102 組中文失敗**：

1. Q9 改成句子清單切片後，既有中文規則沒辨認到 `join(' ')`，使固定句之間
   又出現英文空格。保留[原始差異](initial-source/examples/chinese-False-html-submission.diff)。
2. Q15 只包住漏填名稱的運算式，改變了翻譯單位邊界，使計畫標籤末尾多一個
   空格。保留[原始差異](initial-source/examples/chinese-False-html-review.diff)。

修正只在英文共用來源的寫法：Q9 先將切片存成具名句子清單；Q15 保留原有
完整段落作為檢核／有名稱分支，另以完整句子呈現提交版的中性計畫標籤。
沒有修生成後的中文 Jinja，沒有改翻譯器或全域刪除回答中的空白。
兩處寫法都能精確還原到先前英文原型，英文渲染不變。

第二版 **3,312 組全部通過**：69 組每語案例 × 中英 × 三個版型結構路徑 ×
兩種跳脫設定 × 預設／檢核／未知／提交模式。檢核、預設、未知模式比對字節；
提交比對含內文與內嵌空白的 DOM，不放寬成只看字數或移除所有空白。

762 組舊的英文／中文譯文配對全部保留，新增五組，共 767 組。原有五個重複
單位未能自動遷移，已確認同一句所有舊譯文完全一致後才搬回；不採模糊猜測。
原計畫索引、0、N/A、作者自行填入的提示樣貌文字及自由回答均沿用既有控制。

## 證據範圍與下一步

`after/` 是實際 DSW 資產路徑原生結果；`source-rehearsal/` 是完整來源生成、
翻譯與 TDK 封裝結果。**後者尚未做其自身套件的原生 PDF／Word 渲染**，不能把
兩種證據合稱已完成配對新版驗收。`initial-source/` 保留第一版失敗，不拿來發布。

下一步把通過演練的共用改動接回英文 repo，新增精確的舊版投影檢查，再由既有
流程產生正式中文翻譯樹；兩 repo 配對升版、中文鎖完整英文 commit。接著用實際
重建套件重跑原生對照。不新增中文／模式永久分支，也不維護第二套中文 Word。
全篇閱讀、全域提交提示、Science Europe 完整符合性及 Microsoft Word 驗收仍另列。

## 本機排程與收尾

最初誤把 profile 後綴放進 fixture 名稱，於讀取測試檔時停止，沒有產出成品；
失敗收據保留，改用新的輸出目錄重跑，沒有覆寫它。原生 checker 初次比較
Python tuple 與 JSON array 時停止；改以相同 JSON 表示比較，未放寬任何值、
像素或座標條件，重新檢查全部 12 組通過。原 checker 與失敗收據也保留。

兩個本機暫存模板已限縮刪除，ZIP 備份留在 outputs；容量已還原，stock worker
已還原，四個專屬 pilot 服務停止。未使用正式 keyring 或修改正式 project。
HTML 封存只抽離字型並附 SHA 收據；原生 PDF／DOCX 與 Word 預覽不加工。
