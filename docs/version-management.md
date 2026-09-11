# 版本與分支契約

目前 0.3.0 的英中工作分支為 `feat/storage-sharing-readability`，承接先前實驗。
未合併、未發布正式版本，也不操作線上 DSW。下列正式工作線仍是驗收後政策。

## 三種版本不能混為一談

- 官方基底：英文 repo 的 `.upstream/base.json` 固定完整 commit；官方 tags 存放
  `upstream/v*`，不占用客製版 `v*` 名稱。
- 客製英文：自己發布 `v0.1.0`、`v0.2.0` 等，不跟著官方版號跳動。
- 客製中文：`pipeline.yml` 分開記錄英文 commit／版本和中文套件版本。例如中文
  `0.1.1` 可以仍使用英文 `0.1.0`；只修中文不需要發布新英文版本。

DSW 的三段式套件 ID 包含 organization、template、version。英中使用不同 ID，
也與官方版、既有官方繁中版分開。Git branch 是工作線；Git tag 和不可覆寫的
套件才是可安裝的版本。不能拿 branch 頭部當正式版的唯一引用。

## 工作線

英文沿用客製 `main`，修改走短期 `feat/*`／`fix/*`，官方升級走 `upgrade/upstream-v*`。
`upstream/main` 只是遠端追蹤 ref。只有確實承諾維護舊相容線時才保留 `maint/*`。

中文沿用既有工作模式的概念：`operations` 管建置／驗收政策，`sync/v0.1.0`
對應客製英文 **來源版本**，其中的中文輸出版本可以獨立增加。實驗驗收前不
自動建立這些正式工作線；本 repo 也沒有照搬舊版可覆寫 release 的 workflow。

下一個英文版本進來時，由目前已審閱的來源線建立短期升級分支，改 lock、重抽
並精確遷移翻譯。新舊差異、未沿用單位、實際 PDF／Word 都通過審閱後才建立
新的 `sync/v*` 工作線。舊線只有仍有使用者需要時才維護，不為每個中文修字建立
長期 branch。工具政策修正以小 commit 移植到仍維護的來源線，逐線重測。

若臺灣版更改 KM／增加問題，視為新的 schema 相容線：維護自己的 KM 版本與
SE/TW requirement IDs，不只建立一個名叫 `taiwan` 的 branch 就算完成相容管理。

## 發布門檻

1. 英文、中文、工具修改先提交；lock 指向精確英文及工具 commit。
2. 非 preview 建置拒絕 dirty／不符 lock 的 checkout、未翻完或結構不符的翻譯。
3. 每次建置是新目錄；manifest 記錄來源、翻譯單位、樣式、ZIP checksum。
   套件檔案 UUID／ZIP 時間戳記採確定性建置，不以 TDK 的隨機 UUID 當版本差異。
   本機測試複製套件時，工具也須把內部 file／asset UUID 改到測試專屬命名空間；
   只改模板名稱不足以隔離 DSW 資料庫的全域 ID。本次已加入重建碰撞回歸測試。
4. 同一批合成回答經英中 HTML／PDF／DOCX 測試；接受報告綁定套件 checksum。
   成品、術語、Science Europe 內容與目標 Microsoft Word 環境仍需審閱。
5. `scripts/stage_candidate.py` 只把合格候選版存到本機不可覆寫目錄；preview、
   已知失敗、不同套件的報告及已存在的版本均拒絕。它不是 GitHub 發布指令。
6. 正式 Git tag／release asset 不覆寫。錯誤版本標記撤回，發布修正版；回退則重新
   選用上一個已驗收套件，不移動舊 tag。不要重跑舊版 CI 覆蓋同名 ZIP。

原始基底、審查到的官方版本、已採用／刻意不採用／待處理變更要分別記錄。
選擇性移植官方修正不等於全面合併；不能直接把 baseline 改成最新版本。

## 中文單獨修版演練

固定英文、工具、翻譯內容後，比較兩次 preview，其中一次加上
`--translation-version 0.1.1`。英文 ZIP 必須逐位元相同，中文 metadata／ZIP
必須不同。這個參數只准用於 preview；真正修版要修改並提交 `pipeline.yml`。
