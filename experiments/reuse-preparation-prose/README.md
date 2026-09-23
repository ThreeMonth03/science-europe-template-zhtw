# 資料再利用準備敘述：中英原型

正式輸入仍鎖定 0.3.48。只在短期 `fix/reuse-preparation-prose` 分支新增
實驗檔案；`pipeline.yml`、正式翻譯樹及樣式不變。原型使用獨立
`science-europe-preparation-prototype[-zhtw]:0.3.49` ID，不是正式升版。

`units.json` 列出九組舊／新英文與中文；既有轉換工具重新展開英文條件句，
再遷移譯文並精確核對 766 組保留、9 組移除、9 組新增，共 775 組。
修正英文語病、將「調和」改為「一致化處理」，並以「轉換後的資料」取代
指涉模糊的「此形式」。不把漏填推斷成會分享或不分享，也不翻譯使用者答案。

前兩次純文字替換演練被翻譯閘門攔下：既有工具對此段使用與舊英文逐字綁定
的特殊規則，潤飾後會碎句。因此英文原型將機器可讀段落改成分支內完整句子，
不新增轉換工具特例、不維護獨立中文條件邏輯。失敗演練不列為通過產物。

`lock.json` 分開鎖正式英文基線、英文實驗提交及工具提交。後續 upstream
更新若改到基線，實驗會停止，必須重新檢視差異與跑測試，不能直接套舊驗收。
檢核／提交仍為同一模板的格式選項，不建立兩條長期分支。

重建需乾淨的中英與工具 checkout；輸出資料夾不可已存在：

```sh
python experiments/reuse-preparation-prose/build_prototype.py \
  --english /path/to/science-europe-template \
  --tooling /path/to/dsw-document-template-tool \
  --baseline /path/to/verified-0.3.48-build \
  --output outputs/new-preparation-prototype
```

目前範圍不包含空白標準名稱修復、其他題目的中文潤飾或排版規則變更。
生成 PDF 與 Word 後仍需視覺檢視；LibreOffice 預覽不代表 Microsoft Word 驗收。
