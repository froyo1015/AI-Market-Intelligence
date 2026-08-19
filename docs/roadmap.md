# Market Intelligence Pipeline — Incremental Roadmap

> 目標：在不破壞現有 AI Market Brief MVP 的前提下，用四個開發階段建立 Data → Evidence → Intelligence → Brief 流程。

## 1. Current Baseline

目前已運作並必須保留：

- Yahoo Finance Market Data Adapter。
- Market Data Normalizer。
- Daily/Weekly change、SMA20 及 20-day volatility。
- Asset metadata、market session 及 freshness indicator。
- `market_snapshot.json`。
- Deterministic Market Brief。
- Mock Analyst Adapter。
- GitHub Actions daily run、tests、artifacts 及 Pages deployment。
- Static GitHub Pages renderer。
- Optional Telegram delivery boundary。

目前產品仍是價格摘要。以下 roadmap 的完成定義是加入可追溯的事件、證據、跨資產訊號及市場 regime，而不是增加更多價格卡或 UI。

## 2. Scope Guardrails

整個 v2 MVP 不加入：

- 即時行情或串流。
- 買賣訊號、價格預測或交易執行。
- 回測。
- Multi-agent workflow。
- 複雜資料庫、queue 或常駐 server。
- React dashboard。
- 付費資料作為必要 dependency。
- 新聞全文保存或重新發布。
- 未經證據支持的因果結論。

## 3. Delivery Strategy

每一階段使用 feature-gated、artifact-first 方式加入現有 workflow：

```text
Existing market pipeline continues to publish
                    +
New v2 stage generates validated JSON artifacts
                    ↓
Only after acceptance does the next stage consume them
```

在新 intelligence report 完成驗收前，現有 GitHub Pages 報告繼續作為 production output。任何新階段失敗不得破壞原有 daily run。

## 4. Phase 6.0 — Architecture and Contract Freeze

Status: documentation only.

### Deliverables

- `docs/architecture.md` v2 target architecture。
- `docs/data-schema.md` canonical contracts。
- `docs/intelligence-engine.md` deterministic rules and guardrails。
- Updated incremental roadmap。

### Decisions to approve before coding

- 第一批免費 News、Macro 及 Calendar sources。
- Source licensing and metadata retention rules。
- DXY、US10Y、VIX、Oil 及 breadth 的 exact instruments/providers。
- Report timezone and daily data window。
- Event ranking thresholds。
- Cross-asset rule thresholds。
- Source quality tier policy。
- Whether v2 artifacts are retained in Actions only or committed as static history。

### Exit criteria

- Existing `market_snapshot.json` remains compatible。
- Every new artifact has required fields, validation rules and versioning policy。
- Evidence-to-claim traceability is defined。
- CTO/product owner approves the architecture before implementation。

## 5. Phase 6.1 — Evidence Foundation

Indicative duration: Week 1.

Status: implemented locally; pending review and commit.

### Objective

Prove the frozen observation and evidence contracts using only the existing market snapshot. Do not change the public report or add external dependencies.

### Work

- Convert existing `market_snapshot.json` records into canonical `observations.json`.
- Build deterministic `market_move` evidence bundles in `evidence.json`.
- Preserve source, timestamp, status, metric unit and calculation metadata.
- Add validation for unresolved IDs, unsupported numbers and causal language.
- Mark failed records as unavailable and stale records with reduced confidence.
- Add deterministic fixtures and unit tests.
- Do not add News, Macro, Calendar, LLM, UI or external API integrations.

### Exit criteria

- Existing price records generate versioned observation and evidence artifacts.
- Every evidence bundle resolves to observations and market source metadata.
- A claim such as “Fed caused the market drop” is rejected without event evidence; Phase 6.1 publishes no causal claims.
- Missing or stale market data produces partial artifacts and warnings.
- Existing market pipeline and public Pages output remain unchanged.
- All existing tests continue to pass.

## 6. Phase 6.2 — Real Data Adapters and Event Evidence

Indicative duration: Week 2.

Status: 6.2-A Macro Adapter and 6.2-B Economic Calendar completed locally;
6.2-C News Event Schema approved and frozen locally; source approval and
implementation remain pending.

### Objective

Add approved News, Macro and Calendar sources, then turn normalized source records into ranked event evidence.

### Work

- 6.2-A: Add bounded DXY, US10Y, VIX and WTI proxy ingestion.
- 6.2-B: Add one Economic Calendar Adapter.
- 6.2-C: Add one bounded News Adapter using an approved free/public source.
- Freeze `news_items.json` and news-to-event normalization contracts before
  selecting or implementing the adapter.
- Normalize source records into `events.json` and new observations.
- Preserve canonical URL, publisher, publication time, retrieval time and content hash.
- Exact and deterministic near-duplicate detection.
- Canonical event selection and merged source references.
- Rule-based entity, topic and asset mapping.
- Transparent event relevance scoring.
- Extend `evidence.json` with event-linked bundles.
- Record supporting, conflicting and missing evidence.
- Select zero to three qualifying Top Events.

### Exit criteria

- Duplicate stories do not occupy multiple Top Event positions.
- Every accepted event has at least one valid original or canonical source URL.
- No full copyrighted article content is stored.
- Ranking component scores are inspectable.
- Low-confidence thematic mapping cannot independently promote an event.
- Every eligible interpretation has evidence and source IDs.
- Insufficient evidence is marked `unconfirmed`.
- No LLM is used for facts, ranking or mapping.
- A single macro instrument failure produces a partial artifact rather than a total pipeline failure.
- Each macro observation has source, timestamp, asset mapping and confidence.
- The initial calendar adapter emits a bounded next-48-hours BLS provider
  artifact with deterministic IDs, source metadata, event times and failure
  isolation; broader calendar coverage remains deferred.

## 7. Phase 6.3 — Cross-Asset and Regime Engine

Indicative duration: Week 3.

### Objective

Create deterministic market signals and a current-state regime classification.

### Work

- Add approved market/macro observations required by initial rules.
- Implement versioned cross-asset rules.
- Emit active, inactive, conflicting or insufficient states.
- Implement risk-on/risk-off/mixed scoring.
- Calculate confidence from coverage, freshness and consistency.
- Build Risk Monitor and next-48-hours event list.
- Generate `market_signals.json`.
- Add deterministic `daily_intelligence.json` builder.

### Exit criteria

- Every signal identifies exact observations, evidence and rule version.
- Missing or stale inputs lower confidence rather than default to neutral facts.
- Regime includes classification, score, confidence, conflicts and missing inputs.
- Output is descriptive and contains no prediction or trade instruction.
- Fixture tests cover all three regimes and incomplete data.

## 8. Phase 6.4 — Intelligence Brief and Validation

Indicative duration: Week 4.

### Objective

Publish a useful research-style brief from structured intelligence, with or without an LLM.

### Work

- Build deterministic intelligence brief from `daily_intelligence.json`.
- Add the required Top Events, Cross Asset Signals and Next 48 Hours sections.
- Update Pages from price-card emphasis to research-terminal reading order.
- Add citation resolution to canonical source URLs.
- Add concrete-number, reference and causality validation.
- Test invalid output rejection and deterministic fallback.
- Only after deterministic acceptance, connect a real LLM behind the existing adapter boundary.
- Keep Telegram optional and downstream of validated report generation.

### Exit criteria

- LLM-disabled runs still produce a complete intelligence brief.
- Every published number resolves to an observation.
- Every event claim resolves to source and evidence IDs.
- Unsupported causal language causes validation failure.
- Existing price snapshot remains available as supporting detail.
- Public page leads with intelligence, not a grid of asset prices.

## 9. Workflow Migration Order

Future workflow stages should be added in this order:

```text
tests
  ↓
existing market snapshot
  ↓
new source adapters
  ↓
event / observation validation
  ↓
evidence + ranking
  ↓
signals + regime
  ↓
daily intelligence contract validation
  ↓
deterministic intelligence brief
  ↓
optional LLM brief + output validation
  ↓
static Pages
  ↓
optional Telegram
  ↓
artifacts
```

During migration, a failure before validated intelligence generation should fall back to the existing price brief where safe. A failed or invalid report must not replace the last successful public page.

## 10. Acceptance Metrics

### Data and evidence

| Metric | MVP target |
|---|---:|
| Market observation completeness | ≥ 95% for required existing assets |
| Published events with valid source URL | 100% |
| Published concrete values linked to observations | 100% |
| Signals with rule version and input IDs | 100% |
| Duplicate canonical events in Top Events | 0 |

### Intelligence quality

| Metric | MVP target |
|---|---:|
| Required report sections generated | 100% |
| Unsupported causal claims | 0 |
| Regime output with confidence and conflicts | 100% |
| LLM-disabled useful brief | 100% of successful data runs |
| Top events with why-it-matters and affected assets | 100% |

### Reliability

| Metric | MVP target |
|---|---:|
| Existing test regression | 0 |
| Seven-day scheduled run success | ≥ 90% |
| One source failure causing total pipeline failure | 0 |
| Invalid LLM output published | 0 |

## 11. Demo Review Questions

Before inviting test users, the product owner should be able to answer yes to:

1. Does the report explain why an event matters instead of merely listing a headline?
2. Can each conclusion be traced to evidence and a source URL?
3. Does the report show conflicting evidence and uncertainty?
4. Does it identify cross-asset relationships that are inconvenient to assemble manually?
5. Does it highlight the next 24–48 hour events?
6. Is the output still useful when the LLM is disabled?
7. Would a user learn something beyond checking Yahoo Finance or TradingView prices?

If question 7 is no, the system remains an infrastructure demo and should not be presented as Market Intelligence.

## 12. Deferred Until User Validation

- Persistent database and historical search.
- Multiple provider fallback and paid data.
- Embedding-based semantic deduplication.
- Personalized watchlists or portfolios.
- User accounts and subscriptions.
- Real-time events or alerts.
- Advanced company fundamental research.
- Strategy testing or execution.
- Commercial redistribution of licensed news content.
