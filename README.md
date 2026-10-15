# Science Europe 繁體中文翻譯與相容建置

本 repo 只維護一份可編輯中文譯文：`locales/zh-Hant.po`。
共用 Jinja、回答對應、PDF／Word 排版由
[英文 repo](https://github.com/ThreeMonth03/science-europe-template)維護。
不另維護中文 Jinja，不把產出的 ZIP／MO 當成翻譯來源。

## 目前流程

`pipeline.yml` 是版本配對與依賴的唯一設定來源，鎖定英文及 Tool 的完整 commit。

| 執行環境 | 交付方式 |
| --- | --- |
| DSW 4.34 | 由英文 DT 與中文 PO 產生中文相容 ZIP，內含 MO。 |
| DSW 4.35 | 使用共用英文 DT，另附中文 PO locale，產生文件時選 `zh-Hant`。 |

提交版與內部檢核版是同一套來源的不同格式，不使用永久分支分開維護。
4.34 相容程式仍是現行功能；已停用的是舊抽字串／改寫中文 Jinja 的流程。

## 安裝與建置

先 checkout `pipeline.yml` 鎖定的英文與 Tool commit，再在隔離環境安裝
Tool 及本 repo 的 `requirements-dev.txt`。Tool 必須從該 checkout 以 editable
方式安裝（在 Tool repo 執行 `pip install -e '.[dev]'`），不能只裝同名 PyPI 套件。
以下範例假設三個 repo 放在同一層，
工具環境為 `../dsw-document-template-tool/.venv`：

```sh
../dsw-document-template-tool/.venv/bin/python scripts/build.py \
  --english ../science-europe-template \
  --tooling ../dsw-document-template-tool
```

正式候選要求所有輸入乾淨且已提交。尚未提交的開發測試可加 `--preview`；
預覽不具發布資格。每次建立新的 `outputs/build-*`，不覆寫舊產物。

目前沒有自動更新或批准 PO 的建置選項。先審閱 PO，再建置。
POT 抽取／PO 更新入口是下一個翻譯工作項目，不沿用舊操作指令。

## 檢查與版本管理

- [目前檢查與成品驗收](docs/testing.md)
- [版本配對與發布規則](docs/version-management.md)
- [最近一組原生成品驗證摘要](docs/po-cutover.json)

CI 沿現有三組工作檢查英文來源、中文建置／候選規則及雙語整合。
CI 綠燈不代表 PDF／Word 全面驗收，也不會自動部署至 DSW。
先在本機以相同回答比較實際中英文 PDF／Word，再明確決定發布。

## 歷史與清理範圍

舊 `translation/`、逐輪實驗／review 產物及前 PO 測試合約已從現行工作樹移除。
它們仍保留在 Git 歷史；清理前的中文 commit 為
`6865bd595b836862de015560bfd14253dd93f36a`。可用
`git show COMMIT:path` 讀取歷史檔案，不應再照舊文件操作現行流程。

本 repo 不儲存線上帳密、真實專案回答或部署憑證。
建置直接使用英文 repo 的穩定 `PACKAGE_README.md`，不另維護未使用的中文副本。
授權見 `LICENSE`。
