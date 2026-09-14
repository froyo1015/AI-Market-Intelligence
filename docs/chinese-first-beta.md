# Phase 10.2.1 — 繁體中文優先介面

本階段只處理介面呈現，不改 intelligence、prompt、ranking、regime、signals、
evidence contract、provider 或 derivatives production gate。

靜態文字由 `src/pages/zh_hant.py` 的精確對照表處理。動態文字在渲染邊界使用
`uiText`，view model 的 enum、badge CSS class 與 JSON 保持原值。
來源名稱、ticker、code 中的 evidence ID、引用及時間不翻譯。
安全 Markdown 仍只建立文字節點，不允許 HTML 注入。

來源與既有簡報的自由敘述保留原文，不以自動翻譯或新 AI 呼叫改寫已驗證事實。
頁面明確說明這個限制。這是 Chinese-first 介面，不是所有來源內容的完整中文譯本。
Beta 狀態仍為 conditional，上次部署驗證版本與日期沒有改寫。

新測試覆蓋中文狀態、導覽、證據 ID／時間／來源保留及安全聲明。
未提交、未部署，等待 review。

## 驗證結果

- 全套 479 項測試：478 passed、1 skipped（原有 GnuPG 環境相依測試）。
- Chrome for Testing 151.0.7922.34：1440／768／390／375px 無水平溢出、無 JS 錯誤。
- 展開證據區後有 144 個 reference 項目，500 字元 ID 壓力測試沒有溢出。
- 375px 截圖檢查：Beta 文案、長版本 ID、狀態與回饋連結可讀。
- 安全渲染與來源／ID 保留測試通過；git diff check 通過。
- beta readiness validator：conditional。沒有改寫既有部署驗證時間。
- 本次只驗證本地候選版，尚未驗證部署後的頁面。
