# 空節間距正式來源整合（0.3.48）

將已驗證的共用 CSS 接回英文 `src/layout.css`，中文 `pipeline.yml` 鎖定英文完整
commit，中英配對升為 0.3.48。原型 ID 不拿來當正式模板 ID；短期分支是
`fix/empty-section-integration`，檢核／提交不拆永久分支。

只在整節所有直屬題目皆為可信空題、節 ID／題數／標題位置符合預期時縮緊列印
間距。不改題目、答案、字級、行距、Word 步驟或 775 組譯文；保留中性原序編號。
沒有 LLM 改寫，也沒有另維護中文 Jinja。

`scripts/empty_section_spacing_integration.py` 先檢查實際新版套件的完整來源、資產、
metadata、UUID、時間戳及翻譯檔案，再允許舊測試使用逐位元組還原的歷史來源。
新版分支／引擎檢查與舊版回歸分開，不能把歷史來源通過當成新版排版通過。

前輪原型已確認英文全空 3 → 2 頁、英文長文 7 → 6 頁，所有檢核 PDF／Word
預覽不變；本次必須重建實際新版套件，才能比較是否真正接回相同行為。原生證據
另記於 `reviews/2026-09-23-empty-section-integration`，沒有自動代表部署、
Microsoft Word 實機或全面繳交驗收。

將來推送時先讓英文鎖定 commit 可在遠端取得，再推中文配對分支並通過 CI；
目前不建立 release tag 或部署 DSW。後續語氣／標點另開小範圍修改；upstream
更新仍走 `upgrade/*` 並核對 KM、翻譯與實際文件，保留已驗證版本可回退。
