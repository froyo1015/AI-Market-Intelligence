# AI Market Brief MVP — Production Readiness Checklist

審查日期：2026-07-29  
審查角色：CTO  
審查範圍：現有 Market Data、Brief、Mock Analyst、GitHub Pages、Telegram 與 GitHub Actions 流程  
變更範圍：本文件只記錄審查結果，沒有修改任何程式碼或 workflow

## Executive Decision

**目前結論：NO-GO for external beta。**

現版本適合作為內部技術預覽，但未適合直接提供給 10 名外部測試用戶。主要原因不是系統規模，而是以下兩個 release blocker：

1. 本地 `main` 尚未有 commit，所有 MVP 檔案均未被 Git 追蹤；遠端 default branch 亦未能讀取到 `daily_market_brief.yml`。目前沒有證據證明 GitHub Actions、Pages 或 Telegram 曾在 production 環境成功運行。
2. 唯一市場數據源為 Yahoo Finance／`yfinance`。`yfinance` 官方聲明工具只供研究及教育用途，Yahoo Finance API intended for personal use。向 10 名測試用戶或公開 GitHub Pages 分發價格前，必須確認使用權。

| 檢查範圍 | 狀態 | CTO 判斷 |
|---|---|---|
| 安全 | Amber | Secret 處理及靜態頁面防護合理，但供應鏈與資料授權仍未完成 |
| GitHub Actions | Red | workflow 設計大致合理，但尚無遠端 commit 或 production run 證據 |
| API 失敗處理 | Amber | Telegram 較完整；Yahoo data fetch 缺少重試、timeout 與 fallback |
| 資料品質 | Red | 缺少跨來源校驗、品質門檻及一致的市場時間定義 |
| 10 人測試 | Red | 完成全部 P0 gate 後，才適合開始受控 beta |

優先級定義：

- **P0**：開始 10 人 beta 前必須完成。
- **P1**：beta 前強烈建議完成；如延後，必須接受並監察風險。
- **P2**：可在 beta 期間處理。

## 1. Security Checklist

### 已通過

- [x] Repository 掃描未發現硬編碼 Telegram token、私鑰或常見 GitHub token。
- [x] `TELEGRAM_BOT_TOKEN` 及 `TELEGRAM_CHAT_ID` 只透過 GitHub Secrets 注入 Telegram step。
- [x] Telegram secrets 沒有暴露給測試、市場資料或 Pages generation steps。
- [x] workflow 預設 `contents: read`；Pages deploy job 只增加必要的 `pages: write` 與 `id-token: write`。
- [x] workflow 只由 schedule 或手動執行，沒有在不受信任的 pull request code 上使用 Telegram secrets。
- [x] GitHub Pages generator 對輸入文字及 citation metadata 使用 HTML escaping。
- [x] 靜態頁面設定 restrictive Content Security Policy，沒有 JavaScript、外部 script 或表單。
- [x] Telegram 使用 plain text，沒有啟用 Markdown／HTML parse mode，降低內容注入風險。
- [x] Telegram 錯誤訊息沒有輸出包含 token 的 request URL。

### 必須處理

- [ ] **P0 — 確認 Yahoo Finance data rights。** 書面確認 10 人 beta、Telegram 分發及公開 Pages 是否符合 Yahoo 條款；未確認前，只可作個人／內部研究展示。
- [ ] **P0 — 驗證 production secrets。** 確認 repository secrets 已建立、bot 只加入指定測試 chat，並以非管理員最低權限運行。
- [ ] **P0 — 建立 token rotation procedure。** 記錄 bot token 洩漏時如何 revoke、重建及更新 GitHub Secret；不要在 checklist 記錄實際 token。
- [ ] **P1 — 將 GitHub Actions 固定至完整 commit SHA。** 現時使用 `actions/*@vX` movable major tags，仍有 supply-chain tag movement 風險。
- [ ] **P1 — 鎖定 Python dependency graph。** `pandas`、`yfinance`、`pytest` 只有範圍限制，沒有 lock file 或 hashes；同一 commit 在不同日期可能安裝不同版本。
- [ ] **P1 — 執行 dependency vulnerability audit。** 本次只確認 `pip check` 無 broken requirements，未有 `pip-audit`／Dependabot 證據。
- [ ] **P1 — 保護 `github-pages` environment。** 只允許 default branch deployment，限制可批准或修改 deployment 的帳戶。
- [ ] **P2 — 補充 repository security policy。** 定義 secret exposure、錯誤市場資料及安全問題的回報方式。

## 2. GitHub Actions Stability Checklist

### 已通過

- [x] workflow 同時支援 daily schedule 及 `workflow_dispatch`。
- [x] schedule 使用明確的 `Asia/Taipei` timezone。
- [x] 排程位於每小時第 30 分鐘，避開 GitHub 官方指出較高負載的整點。
- [x] Python 版本固定為 3.12。
- [x] 測試在資料生成、Telegram 及 Pages deployment 前執行。
- [x] generate job 設有 20 分鐘 timeout，deploy job 設有 10 分鐘 timeout。
- [x] concurrency 避免同一 daily workflow 重疊執行。
- [x] 生成檔案會先作 non-empty 檢查。
- [x] artifacts 設定唯一名稱、缺檔失敗及 30 日 retention。
- [x] Pages deploy job 明確依賴 generate job，並符合 Pages permission／environment 結構。
- [x] Telegram step 只在之前 steps 成功後執行，而且 `continue-on-error` 不會阻止 artifact 或 Pages。
- [x] 本地完整測試結果為 **20 passed**；`pip check` 結果為 **No broken requirements found**。

### 必須處理

- [ ] **P0 — 建立第一個 commit 並推送 default branch。** 本次審查的 checkout 中 `main` 沒有 commit，所有檔案均為 untracked。
- [ ] **P0 — 確認遠端 workflow 可見。** GitHub default branch 必須存在 `.github/workflows/daily_market_brief.yml`；本次 remote file check 回傳 404。
- [ ] **P0 — 啟用 GitHub Actions 及 Pages。** Pages publishing source 必須選擇 GitHub Actions。
- [ ] **P0 — 執行一次 production `workflow_dispatch`。** 保存成功 run URL，確認 tests、snapshot、brief、Pages artifact、deployment 及 Telegram 各 step 的結果。
- [ ] **P0 — 驗證公開 Pages URL。** 使用未登入瀏覽器確認頁面可讀、日期正確、沒有舊報告或 404。
- [ ] **P1 — 建立真正的 data quality gate。** 現時只在全部 10 個 symbol 都 failed 時才使 pipeline 失敗；1 success + 9 failed 仍會公開報告。
- [ ] **P1 — 驗證 JSON schema，而不只是 `test -s`。** 非空檔案仍可能包含錯誤 schema、舊 timestamp 或非有限數字。
- [ ] **P1 — 加入 PR／push CI policy。** 現時 daily workflow 不會自動驗證每次 push；合併前至少要有同一套 tests。
- [ ] **P1 — 建立 failure runbook。** 定義 generation、Pages、Telegram 或 scheduled run 缺失時由誰檢查及如何手動補跑。
- [ ] **P1 — 接受 schedule 非準時保證。** GitHub 說 scheduled jobs 在高負載時可能延遲甚至被丟棄；目前沒有 missed-run detection 或 backfill。
- [ ] **P1 — 監察 public repo inactivity。** GitHub 可在 public repository 60 日無活動後停用 scheduled workflows。
- [ ] **P2 — 執行 workflow lint。** YAML 可成功解析，但尚未有 `actionlint` 或 GitHub production parser 的通過證據。

## 3. API Failure Handling Checklist

### Yahoo Finance／Market Data

- [x] 單一 symbol 失敗不會令其他 symbol 一併失敗。
- [x] 每個 record 有 `success`、`stale` 或 `failed` status。
- [x] 失敗 record 不會偽造價格，欄位會變成 `null`／`unavailable`。
- [x] provider errors 會截短後寫入 record，避免無限制增長。
- [ ] **P0 — 確認可接受的最低成功率。** 建議 beta launch gate 為所有核心 symbol 均成功；任何例外必須在報告頂部明示。
- [ ] **P1 — provider call 沒有 application-level retry/backoff。** 一次短暫 DNS、429 或 Yahoo outage 會直接令該 symbol failed。
- [ ] **P1 — provider call 沒有明確 timeout。** 只能依賴 library/network 預設及整個 job 的 20 分鐘 timeout。
- [ ] **P1 — 沒有 last-known-good fallback。** provider 失敗時，不會保留上一個成功 snapshot 作明確標記的 stale fallback。
- [ ] **P1 — 沒有第二資料源。** 無法判斷成功回傳的錯誤價格、symbol mapping 或 corporate action adjustment。
- [ ] **P1 — partial failure 仍可生成及發布。** workflow non-empty check 不代表報告可用。

### Telegram Bot API

- [x] 發送設有 15 秒 timeout。
- [x] 每個 message 最多嘗試 3 次。
- [x] network error、HTTP 429 及 5xx 會重試。
- [x] 429 會尊重 Telegram `retry_after`，其他 transient errors 使用 exponential backoff。
- [x] 4xx permanent error 會停止重試。
- [x] 超過 Telegram message limit 的內容會分段。
- [x] 未配置 secrets 時會安全跳過；推送失敗不影響 Pages 主流程。
- [ ] **P0 — 執行一次真實 chat delivery test。** 現有 tests 使用 fake transport，未證明 bot token、chat ID、bot membership 或 production network 正常。
- [ ] **P1 — 不應把「跳過」當作已送達。** `--skip-if-unconfigured` 及 `continue-on-error` 可令整體 workflow 綠燈但 10 名用戶完全收不到訊息。
- [ ] **P1 — 接受 duplicate delivery 風險。** Telegram 已接收但 client 未收到 response 時，retry 可能造成重複訊息。
- [ ] **P1 — 接受 multi-part partial delivery 風險。** 第一段成功而後續段失敗時，不會 rollback。

### AI Analyst

- [x] 目前沒有外部 LLM API，因此沒有 LLM token、quota、timeout 或 hallucination API failure。
- [x] prompt 明確要求只引用輸入資料、保留 source/timestamp 及標記未知。
- [x] Mock adapter 對 failed／stale data 有明確文字處理。
- [ ] **P0 — 對測試用戶清楚標示這是 Mock Analyst。** 不應把 deterministic mock 描述成真正 AI research。
- [ ] **P1 — `market_context.json` 目前是 unavailable mock。** 每日 workflow 沒有生成 macro/news context；使用者必須知道「宏觀新聞」尚未實作。

## 4. Data Quality Checklist

### 已通過

- [x] Snapshot 有 schema version、generated timestamp、source、change unit 及 volatility unit。
- [x] 每一個 instrument 有獨立 source、market timestamp 及 status。
- [x] 時間統一輸出為 UTC ISO 8601。
- [x] history 會排序、移除 duplicate timestamp、轉換 numeric close 及排除 null。
- [x] output 採 temporary file replace，降低讀到半寫入檔案的風險。
- [x] daily、weekly、SMA20、20-period annualized volatility 規則為 deterministic。
- [x] 頁面對 missing/stale/failed data 有可顯示的 fallback。

### 必須處理或明確披露

- [ ] **P0 — 清楚定義資料時間。** Equity 是上一個交易日 close；Crypto／FX 最新 daily row 可能仍在形成中，各資產不是同一市場截點。
- [ ] **P0 — 披露非即時資料。** 本產品不能描述為 real-time terminal；價格可能延遲或只代表日線資料。
- [ ] **P0 — 披露 Gold 定義。** `GOLD` 實際映射為 `GC=F` 黃金期貨，不是 spot gold；期貨 rollover 會影響價格及變動。
- [ ] **P0 — 披露 adjusted price。** Equity history 使用 `auto_adjust=True`，數值是調整後 history，不應默認視為即時 quote。
- [ ] **P0 — 修正或披露 Crypto weekly semantics。** weekly change 使用第 6 個 daily observation，對 7 日交易的 Crypto 實際是約 5 日變動。
- [ ] **P1 — freshness gate 太寬。** Equity／Gold／FX 在超過 5 calendar days 才算 stale，日報可能把數日前資料仍標示為 success。
- [ ] **P1 — future timestamp 未被拒絕。** provider clock／timezone 錯誤可能產生負 age 並被標為 success。
- [ ] **P1 — 缺少合理性檢查。** 沒有驗證 price > 0、finite number、極端單日跳幅、缺失交易日或異常 volatility。
- [ ] **P1 — JSON 可能接受 NaN／Infinity。** Python default JSON serialization 可輸出非標準有限值；現有 snapshot 沒有出現，但 contract 未防止。
- [ ] **P1 — 缺少 cross-source reconciliation。** 現有資料成功只代表 provider 有回覆，不代表市場價格正確。
- [ ] **P1 — source provenance 不完整。** 報告只有 `yahoo_finance`，沒有 provider symbol、session definition、adjustment policy 或擷取版本。
- [ ] **P1 — mock context timestamp 可能與每日 snapshot 不一致。** workflow 會讀取 repository 內既有的 `market_context.json`，不會每日更新 context。
- [ ] **P1 — 現有測試沒有 live provider contract test。** 20 個 unit tests 無法發現 Yahoo response schema 或 symbol behavior 改變。

## 5. Ten-User Beta Readiness

### 建議使用方式

只建議先進行：

- 一個受控 Telegram private group；
- 最多 10 名已知測試者；
- 明確標示 delayed/free data、Mock Analyst、非投資建議；
- 測試者知道服務可能漏發、延遲或顯示 unknown；
- 不收集個人財務資料、不提供個人化交易建議。

### P0 Launch Gates

以下每項都必須有 evidence，全部完成後才由 CTO 改為 **GO for limited beta**：

- [ ] `main` 已有可追溯 commit，所有 MVP files 已推送到正確 GitHub repository。
- [ ] GitHub 遠端可讀取 workflow，Actions 已啟用。
- [ ] GitHub Pages source 設為 GitHub Actions，production URL 可由未登入瀏覽器打開。
- [ ] Yahoo／yfinance 使用權已確認允許目前的 10 人及公開展示方式。
- [ ] `TELEGRAM_BOT_TOKEN`、`TELEGRAM_CHAT_ID` 已配置，bot 權限最小化。
- [ ] 一次 manual production run 全部 generation、artifact 及 Pages steps 成功。
- [ ] 同一次 run 的 Telegram 訊息真實送達正確 private group。
- [ ] 該次 snapshot 所有核心 instruments 均有可接受狀態；任何 stale/failed 均清楚顯示。
- [ ] Pages 與 Telegram 顯示同一報告日期、generated timestamp 及 source。
- [ ] 測試者 onboarding 明示資料延遲、Gold futures、Mock Analyst、macro/news unavailable 及非投資建議。
- [ ] 指定一名 operator 每日檢查 workflow run、Pages 日期與 Telegram delivery。
- [ ] 準備 token rotation、manual rerun、錯誤資料撤回及通知測試者的簡短 runbook。

### 建議 Beta Acceptance Criteria

- [ ] 正式邀請測試者前，連續 3 次 scheduled/manual production runs 成功。
- [ ] Beta 期間，每日報告成功生成率目標至少 95%。
- [ ] 核心 symbol data success rate 每日可見並有人檢查。
- [ ] Pages 報告不得較預定時間落後超過 24 小時而沒有警告。
- [ ] Telegram 漏發或錯發能在同一工作日被發現。
- [ ] 所有錯誤價格回報均保留 snapshot、run URL、source timestamp 及處理紀錄。

## CTO Final Assessment

架構本身對 10 人 MVP 並不過度複雜：單一 batch workflow、靜態 Pages、Telegram 及 deterministic output 都適合小規模測試。主要風險集中在 operation 與 data governance，而不是容量。

在 10 人規模下，GitHub-hosted runner、Pages 及單一 Telegram group 的容量足夠；不需要 server、database 或額外付費 infrastructure。可是「可承載 10 人」不等於「已可對外使用」。在 P0 gates 完成前，狀態維持 **NO-GO**。

## Review Evidence

- Local Git state：`main` has no commits；MVP files 全部 untracked。
- Remote workflow check：`froyo1015/AI-Market-Intelligence` default branch 讀取 `.github/workflows/daily_market_brief.yml` 回傳 404。
- Local tests：20 passed。
- Dependency consistency：`pip check` 無 broken requirements。
- Reviewed local runtime：Python 依賴包括 `pandas 2.3.3`、`yfinance 0.2.66`。
- Secret pattern scan：未發現硬編碼 token／private key。
- Existing sample snapshot：10 records 均為 success；這只證明單次 sample，不代表 production SLA 或數據正確性。

## Authoritative References

- [GitHub Actions workflow syntax — scheduled workflow、timezone、default branch](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)
- [GitHub Actions troubleshooting — scheduled jobs may be delayed or dropped](https://docs.github.com/en/actions/how-tos/troubleshoot-workflows)
- [GitHub secure use — pin Actions to full commit SHA](https://docs.github.com/en/actions/reference/security/secure-use)
- [GitHub Actions secrets reference](https://docs.github.com/en/actions/reference/security/secrets)
- [GitHub Pages custom workflows and required permissions](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
- [GitHub Pages publishing source and public visibility](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)
- [Telegram Bot API — `sendMessage` and `retry_after`](https://core.telegram.org/bots/api)
- [yfinance official README — research/educational purpose and personal-use notice](https://github.com/ranaroussi/yfinance)

