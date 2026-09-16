# CI 打包時間的淺層歷史問題

0.3.30 的原生候選與最終來源本機重建，兩個 ZIP 都完全相同。
但 [中文 CI 35159916481](https://github.com/ThreeMonth03/science-europe-template-zhtw/actions/runs/35159916481)
雖通過全部檢查，其產物 hash 與本機不同。下載後逐一比較 ZIP 內檔案，
唯一差異為 `template/template.json` 的 `createdAt`／`updatedAt`：

- 正確的最後模板輸入變更：`2026-09-16T22:34:23Z`。
- 淺層 checkout 誤用的測試修正提交：`2026-09-16T22:50:48Z`。

Jinja、CSS、翻譯、字型、Word reference 與其他 ZIP 項目完全相同；沒有
樣張內容改變。不是 ZIP 條目日期或壓縮器差異。

原因是英文 checkout 預設 depth 1。Git 把淺層邊界當作新增整個樹，因此
`git log HEAD -- <package input paths>` 仍會選中只改測試的 commit。
中文 repo 已有 full history，但不能代替英文 repo 的歷史。

修正為英文 checkout 加 `fetch-depth: 0`，建置程式同時拒絕淺層英文 repo，
提示先 `git fetch --unshallow`。不硬寫目前時間或放寬 hash 比對。
測試建立兩個不同日期的提交，再用真正 `--depth 1` 的 file:// clone
重現錯誤；確認拒絕建置，補齊歷史後取回正確時間。另測試 CI 設定本身。

這是建置／CI 修正，不改模板版號、不重寫已歸檔的原生樣張。
0.3.30 正確 ZIP：

| 套件 | SHA256 |
|---|---|
| English | `a2096f905a25c0657340621394dec309ea98c805ad3a8171e42b3fe27dd2656a` |
| 中文 | `a3ef2050c5aa0d2ebd9e08084c040dd5e9a8e95acbda9c6f6f8bc69a65aab13d` |

CI 通過仍不代替原生 PDF／Word 或全篇閱讀驗收。
