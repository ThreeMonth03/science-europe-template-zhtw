# 全空節的 PDF 間距原型

正式來源與 `pipeline.yml` 仍為 0.3.47。這是英文全空提交 PDF 第 15 題孤立尾頁的
下一輪原型，不是既有模板升版或部署。兩 repo 使用短期 `fix/empty-section-spacing`。

只在已知六個節、標題位置與題目數完全正確，而且每一題都有既有的「確定無答案」
標記時，縮小該節的列印間距。該節只要有一題已填，就不套用；未知結構也保持原樣。
不改字級、行距、題目、自由文字、Word 步驟或空答案容器。

`lock.json` 分別鎖定正式英文來源、英文原型 recipe 與工具 commit，並綁定上一輪
封存證据。重播時英文 checkout 必須位於 `english_recipe_commit`，兩個實驗 repo
均須乾淨；不能把正式 `pipeline.yml` 的鎖定移到試驗版來繞過驗證。

以既有乾淨 0.3.47 建置為 baseline，執行：

```bash
../dsw-document-template-tool/.venv/bin/python experiments/empty-section-spacing/build_prototype.py \
  --english ../science-europe-template --tooling ../dsw-document-template-tool \
  --baseline outputs/build-v0i7akit --output outputs/empty-section-spacing-02
```

建置流程由英文共用 CSS overlay 經原翻譯器生成中文，775 組譯文必須逐組相同。
所有其他 prepared 來源、資產、格式 UUID、轉換步驟與時間戳均比對基線；原型採
獨立 templateId 與 0.3.48 版號，並不表示正式模板已升到 0.3.48。

每語 396 組 Jinja／結構比較，加上英文 recipe 的 63 組實際選擇器與 28 組
列印／螢幕樣式檢查，是局部驗證；完整 PDF、Word、真實快照與長文仍須另驗。
不把頁數減少等同完整排版驗收；私有專案內容與產物不進 repo。
