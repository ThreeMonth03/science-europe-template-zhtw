# Worker PDF 穩定性診斷：未證明歷史 exit 139 已解決

結論與限制見 [診斷報告](../../docs/worker-pdf-stability.md)。模板仍為 0.3.25，
本輪沒有替換原生 worker、沒有變更中英譯文或重產 Word。

- 六組隔離測試：80 次 PDF 轉換、20 次字型生命週期探針，均未當機。
- [前後比對](comparison.json)：28 組、188 對頁面的文字座標、字型、連結與
  96 dpi 影像一致。這是固定 HTML 輸出的轉檔對照，不是原生 PDF 入口。
- `worker-*/` 保留 stdout／stderr、退出狀態與工具快照；兩組混合案例
  各保留 28 份 PDF。第一輪 cache 不可寫警告也保留。
- `historical-incident/` 保留上輪 exit 139、同映像恢復與原生 manifest；
  缺少當時 stack trace，無法據此確診。
- `synthetic-inputs.tar.xz` 只有明列的合成 HTML、PilotTC.ttf 與 OFL 授權。
  `provenance.json` 記錄解壓後來源 hash；`checksums.json` 核對封存證據。

重現時先將輸入解壓到全新空目錄，核對 hash，再使用 repository 內的現行
腳本。不要將診斷 PDF 覆蓋原生 0.3.25 樣張，也不要把 `experiment/` 的快照
當成獨立可建置的目錄（Docker context 是 repository root）。例如：

```sh
../dsw-document-template-tool/.venv/bin/python scripts/probe_worker_pdf_lifecycle.py \
  --source NEW_INPUT_DIRECTORY --output NEW_OUTPUT_DIRECTORY \
  --cases empty-english.html empty-chinese.html partial-english.html partial-chinese.html \
  --cycles 2 --gc after-each --save-all \
  --image science-europe-pilot-worker:4.30-font-lifetime-experiment
```

完整 14 個輸入及原始執行順序見 `worker-mixed-patched/settings.json`。
修補不能視為穩定性修復的完成證據；原生佇列回放與較長監測仍待做。
