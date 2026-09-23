# Word 空節間距：配對原型

正式中英來源維持 0.3.49。英文實驗只修改兩個 Word 輔助素材，中文仍經既有
鎖定工具展開、遷移及套回；775 組譯句與翻譯檔案位元必須全部保持一致。
原型使用獨立 `science-europe-word-empty-sections-prototype[-zhtw]:0.3.49` ID，
不是發布或正式升版。`pipeline.yml` 與正式翻譯樹不變。

第一版只有節標題 6pt／3pt 縮距，實際 Word 仍有孤立尾頁，已保留失敗紀錄。
第二版使用 3pt／2pt，並只將同一全空節的非末題與下一題保持連頁；
不改有答案的節、字級、題目文字、PDF 或檢核版。

`lock.json` 分開鎖定英文正式基線、英文實驗提交及工具；兩個 repo 使用短期
`fix/word-empty-section-spacing`，檢核／提交仍為同一來源的格式選項。

```sh
python experiments/word-empty-section-spacing/build_prototype.py \
  --english /path/to/science-europe-template \
  --tooling /path/to/dsw-document-template-tool \
  --baseline /path/to/verified-0.3.49-build \
  --output outputs/new-word-empty-section-prototype
```

建置要求乾淨 checkout，驗證封存基線與完整套件差異，且不覆蓋既有輸出。
引擎邊界檢查、原生文件對照及人工抽看另行記錄；LibreOffice 預覽不等於
Microsoft Word 驗收。私有專案 JSON、PDF、DOCX 與圖片不得放入 repo。
