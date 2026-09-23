# 第 3 題中文句間空格：原型，非正式版本

正式 EN/ZH 保持 0.3.50，`pipeline.yml` 不變。英文 recipe 和中文原型各在
`feat/cjk-punctuation-probe` 短期分支；`lock.json` 記錄完整英文 commit，
不是用長期分支名稱當版本。本實驗沒有新建獨立維護的中文 Jinja。

範圍只有 Q3 固定句子清單的 join separator。英文照舊，中文不再在這幾句
固定敘述之間加入 ASCII 空格。字型、CSS、Word 樣式及 Lua、使用者填寫內容、
其他段落和 775 份翻譯檔必須逐位元相同。不是全文件移除空格，也不是全形
標點壓縮。其他 CSS / Lua 產生的段落間空格暫不處理。

在乾淨 checkout 與既有工具 venv 下執行：

```sh
python experiments/cjk-punctuation-probe/build_prototype.py \
  --english ../science-europe-template \
  --tooling ../dsw-document-template-tool \
  --baseline outputs/build-aphphgpw \
  --output outputs/cjk-punctuation-prototype-01
```

輸出目錄必須不存在。先驗證封存的 0.3.50 證據和實際套件，再以同一鎖定工具
expand/export/merge/sync；任何翻譯檔變動都會拒絕建置。封裝後再次確認只有
Q3 source 和原型識別碼/衍生 UUID 可變，並對實際套件執行中英文答案矩陣。

原型有獨立套件 ID，名稱明示「非提交版」。兩次乾淨建置的 ZIP 應相同。
私人專案和文件只存本機私有目錄。PDF 與 LibreOffice 預覽需另驗證，
LibreOffice 通過不代表 Microsoft Word 驗收；本實驗不推送、不部署。
