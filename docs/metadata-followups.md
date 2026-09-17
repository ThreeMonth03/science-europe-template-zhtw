# Q3 資料字典與後設資料追問：0.3.33

本輪補回資料字典的「是／否」回答，並區分漏填與無法辨識的選項。
選擇後設資料不公開、原因未填時，顯示獨立待補提示；選擇公開，卻未填
取用說明或自動擷取／索引形式時，也分別提示。使用者已填的原因保留原有
Markdown 段落、強調與連結；不把漏填解讀成否定，不代填政策。

英文來源只改 Q3 與三個已核對 KM 的 UUID。中文循既有流程產生，
原有 735 組譯文全保留，只新增 9 組，詳見
[逐組翻譯差異](metadata-followup-translation-delta.json)。不改字型、CSS、
Word Lua 或參考 DOCX。DC／DataCite／DDI／關鍵字／W3C PROV 的明確否定
目前仍未完整呈現，不包含在本輪修正範圍內。

中英文使用相同八組合成問卷做前後 HTML／PDF／Word 比較，另檢查漏填、
空白字串、未知選項、明確否定及自填區塊；不能以單元測試取代成品驗收。
Word 預覽使用 LibreOffice，不等於 Microsoft Word 驗收。

[實際樣張與限定結果](../reviews/2026-09-17-metadata-followups/README.md)已保存。
本輪內容檢查通過，但新增提示造成 3 個中文 Q5 回答／限制說明分離反例，
需於下一輪單獨修正分頁；不可宣稱整份版面已驗收。

兩個 repo 都使用短期 `fix/q3-metadata-followups` 分支。`pipeline.yml` 鎖定
英文完整 commit，不各自維護一份中文 Jinja。之後的 upstream 升級另開
升級分支，先做來源／KM／譯文與樣張比較，再更新中文鎖定點；不在本輪混入。
維持實驗版本：未上傳正式站、未標 tag、未宣布全篇 Science Europe 合規。
