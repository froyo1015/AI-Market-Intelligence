# AI Market Intelligence Pipeline — Data Contracts v1.0

> 本文件定義 v2 pipeline 的 canonical JSON contracts。它是架構規格，不代表模組已經實作。

## 1. Contract Principles

- 所有 artifacts 使用 UTF-8 JSON、UTC ISO 8601 timestamps 及明確 `schema_version`。
- 現有 `market_snapshot.json` v1 保持向後兼容，不因 v2 開發而改名或刪除欄位。
- Adapter payload 不可直接進入 intelligence 或 LLM；必須先 normalize。
- 所有 event、observation、evidence、signal 及 claim 使用穩定 ID 互相引用。
- `null` 表示值未知；不可用 `0`、空字串或估算值代替未知資料。
- 每個外部事實均須保留來源及時間。
- 所有百分比使用 percentage points，例如 `1.25` 代表 `1.25%`。
- 所有 confidence values 使用 `0.0–1.0`，並同時提供可讀 label。
- 所有 lists 即使沒有資料亦輸出空陣列，避免省略欄位造成語意不清。

## 2. Common Types

### 2.1 Artifact envelope

所有新 artifacts 使用相同頂層欄位：

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `schema_version` | string | yes | Contract major/minor version，例如 `1.0` |
| `artifact_type` | string | yes | `events`、`observations`、`evidence`、`market_signals` 或 `daily_intelligence` |
| `run_id` | string | yes | 同一批次共用的 stable identifier |
| `report_date` | string | yes | `YYYY-MM-DD`，以報告時區計算 |
| `generated_at` | string | yes | UTC timestamp |
| `status` | enum | yes | `complete`、`partial` 或 `failed` |
| `warnings` | array[string] | yes | 缺漏、延遲或 coverage 警告 |

`failed` artifact 仍須輸出 envelope 及 warnings，但不得包含虛構 records。

### 2.2 Identifier rules

| Entity | Prefix | Example |
|---|---|---|
| Source | `src_` | `src_fred_abc123` |
| Event | `evt_` | `evt_20260818_fed_minutes_a1b2` |
| Observation | `obs_` | `obs_spy_daily_change_20260818` |
| Evidence bundle | `evd_` | `evd_gold_usd_yield_20260818` |
| Signal | `sig_` | `sig_defensive_gold_20260818` |
| Claim | `clm_` | `clm_top_event_01_20260818` |

IDs must be deterministic for the same canonical input where practical. Provider-specific IDs may be stored separately but must not be used as the only internal key.

### 2.3 Source reference

```json
{
  "source_id": "src_example_123",
  "provider": "provider_name",
  "publisher": "original_publisher",
  "source_type": "official_release",
  "quality_tier": 1,
  "title": "Original source title",
  "url": "https://example.org/original",
  "published_at": "2026-08-18T00:00:00Z",
  "retrieved_at": "2026-08-18T01:30:00Z",
  "content_hash": "sha256:..."
}
```

Validation:

- `url`, `publisher`, `retrieved_at` and `content_hash` are required for news and event sources.
- `published_at` may be `null` only when the source genuinely provides no publication time.
- `quality_tier` is `1`, `2` or `3`; lower is stronger.
- Full copyrighted article text must not be stored.

### 2.4 Status and confidence

Data status:

- `success`: value or record was retrieved and validated.
- `stale`: structurally valid but outside the defined freshness window.
- `failed`: unavailable or invalid.
- `scheduled`: future event not yet released.
- `cancelled`: scheduled event has been cancelled.

Confidence labels:

| Score | Label |
|---:|---|
| `0.80–1.00` | `high` |
| `0.55–0.79` | `medium` |
| `0.30–0.54` | `low` |
| `<0.30` | `insufficient` |

`insufficient` claims cannot appear as conclusions; they may appear only as limitations or `unconfirmed` items.

## 3. Existing Contract: `market_snapshot.json`

The existing schema remains authoritative for the current price pipeline:

```json
{
  "schema_version": "1.0",
  "generated_at": "2026-08-18T01:30:00Z",
  "source": "yahoo_finance",
  "change_unit": "percent",
  "volatility_unit": "annualized_percent",
  "records": [
    {
      "symbol": "SPY",
      "asset_type": "equity",
      "price": 0.0,
      "daily_change": 0.0,
      "weekly_change": 0.0,
      "sma20": 0.0,
      "volatility_20d": 0.0,
      "trend": "above_sma20",
      "timestamp": "2026-08-17T04:00:00Z",
      "source": "yahoo_finance",
      "status": "success"
    }
  ]
}
```

v2 does not require changes to this file. The Observation Normalizer converts its records into the canonical observation contract.

## 3.1 `macro_snapshot.json`

Phase 6.2-A adds a provider artifact for four bounded macro market proxies:

| Field | Meaning |
|---|---|
| `symbol` / `provider_symbol` | Canonical and provider identifiers |
| `metric` / `value` / `value_unit` | Current observed level and unit |
| `daily_change` / `weekly_change` | Deterministic change values |
| `change_metric` / `change_unit` | Percent for DXY/VIX/OIL; basis points for US10Y |
| `timestamp` | Provider daily-bar timestamp |
| `source` / `source_url` | Actual market-data provider provenance |
| `semantic_reference_url` | Official benchmark/product definition; not the data source |
| `asset_mapping` | Rule-based candidate affected assets |
| `confidence_score` / `confidence_label` | Source confidence before interpretation |
| `status` | `success`, `stale` or `failed` |
| `price_basis` | Human-readable proxy and delay semantics |

The artifact status becomes `partial` when any instrument is stale or failed.
One record failure never removes successful records.

## 3.2 `economic_calendar.json`

Phase 6.2-B adds a bounded provider artifact for official BLS releases in the
next 48 hours. It is an input to the future Event Normalizer, not a substitute
for canonical `events.json`.

| Field | Meaning |
|---|---|
| `event_id` | Deterministic ID derived from normalized name and UTC schedule |
| `event_type` | Fixed as `economic_event` at the provider-artifact boundary |
| `name` / `scheduled_at` | Source-grounded release name and UTC time |
| `country` | `US` for the BLS source |
| `impact` | Deterministic `high`, `medium` or `low` release-class rule |
| `affected_assets` / `topics` | Candidate relevance mapping, not confirmed impact |
| `source` / `publisher` / `source_url` | Provenance retained from the official feed |
| `retrieved_at` / `content_hash` | Retrieval timestamp and exact VEVENT fingerprint |
| `status` | `scheduled`; unavailable source produces no event records |
| `confidence_score` / `confidence_label` | Confidence that the official schedule is represented accurately |

Artifact-level `status` is `complete`, `partial`, or `failed`. A source failure
must produce a failed envelope, warning, and empty `events` list. The initial
source does not cover FOMC, Treasury, BEA, or private-sector releases.

`failure_type` is `null` for a valid source response, even when the bounded
window contains no scheduled events. A transport or access failure uses
`source_access_error` with `retryable: true`; an invalid source document uses
`source_validation_error`; isolated malformed events use
`event_validation_error` with artifact status `partial`.

## 4. `events.json`

Purpose: represent normalized news, official releases and future calendar events without asserting market impact.

### Event record

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `event_id` | string | yes | Stable internal ID |
| `event_type` | enum | yes | `macro_release`, `central_bank`, `company`, `crypto`, `geopolitical`, `commodity`, `regulatory`, `calendar` |
| `status` | enum | yes | Data status |
| `title` | string | yes | Normalized factual title |
| `summary` | string/null | yes | Short source-grounded summary |
| `occurred_at` | string/null | yes | Event time when known |
| `scheduled_at` | string/null | yes | Future event time when applicable |
| `country_codes` | array[string] | yes | ISO country codes |
| `entity_ids` | array[string] | yes | Companies, institutions or protocols |
| `candidate_assets` | array[string] | yes | Rule-based possible relevance, not confirmed impact |
| `topics` | array[string] | yes | Controlled topic vocabulary |
| `source_refs` | array[SourceReference] | yes | At least one source |
| `canonical_hash` | string | yes | Deduplication key |
| `duplicate_of` | string/null | yes | Canonical event ID if merged |

Example:

```json
{
  "event_id": "evt_20260818_example_a1b2",
  "event_type": "central_bank",
  "status": "success",
  "title": "Central bank publishes meeting minutes",
  "summary": "The official minutes were released at the scheduled time.",
  "occurred_at": "2026-08-18T18:00:00Z",
  "scheduled_at": "2026-08-18T18:00:00Z",
  "country_codes": ["US"],
  "entity_ids": ["federal_reserve"],
  "candidate_assets": ["SPY", "QQQ", "GOLD", "EURUSD", "USDJPY", "BTC-USD"],
  "topics": ["monetary_policy"],
  "source_refs": [
    {
      "source_id": "src_official_a1b2",
      "provider": "official_feed",
      "publisher": "Official institution",
      "source_type": "official_release",
      "quality_tier": 1,
      "title": "Meeting minutes",
      "url": "https://example.org/original",
      "published_at": "2026-08-18T18:00:00Z",
      "retrieved_at": "2026-08-18T18:05:00Z",
      "content_hash": "sha256:example"
    }
  ],
  "canonical_hash": "sha256:canonical-event",
  "duplicate_of": null
}
```

## 5. `observations.json`

Purpose: store directly observed or deterministically calculated market and macro facts.

### Observation record

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `observation_id` | string | yes | Stable internal ID |
| `observation_type` | enum | yes | `market_price`, `market_feature`, `macro_value`, `survey`, `breadth` |
| `subject` | string | yes | Symbol or indicator ID |
| `metric` | string | yes | Controlled metric name |
| `value` | number/string/null | yes | Observed value |
| `unit` | string/null | yes | Unit or null |
| `period` | string/null | yes | `daily`, `weekly`, `20d`, etc. |
| `as_of` | string | yes | Timestamp represented by the value |
| `source_id` | string | yes | Source reference ID |
| `status` | enum | yes | Data status |
| `calculation` | object/null | yes | Rule and input IDs for calculated values |
| `asset_mapping` | array[string] | v1.1 | Candidate related assets; direct market observations map to themselves |
| `confidence_score` | number | v1.1 | Source/data confidence from `0.0–1.0` |
| `confidence_label` | enum | v1.1 | Label derived from the confidence score |

Calculated observations must retain their formula version and inputs:

```json
{
  "observation_id": "obs_spy_daily_change_20260818",
  "observation_type": "market_feature",
  "subject": "SPY",
  "metric": "daily_change_pct",
  "value": 0.42,
  "unit": "percent",
  "period": "daily",
  "as_of": "2026-08-17T20:00:00Z",
  "source_id": "src_yahoo_spy_20260818",
  "status": "success",
  "calculation": {
    "rule_id": "daily_change_v1",
    "input_ids": ["obs_spy_close_20260817", "obs_spy_close_20260816"]
  }
}
```

Phase 6.1 imports already-calculated legacy features from `market_snapshot.json`.
Until raw close observations are introduced, these records use an empty
`input_ids` list together with `source_artifact: "market_snapshot.json"`. The
feature value and rule remain owned by the existing Feature Calculator; the
Evidence Foundation does not recalculate or modify them.

## 6. `evidence.json`

Purpose: group the minimum evidence required to support a market interpretation.

### Evidence bundle

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `evidence_id` | string | yes | Stable internal ID |
| `claim_type` | string | yes | Versioned claim category; Phase 6.1 uses `market_move` |
| `statement` | string | yes | Short machine-generated proposition |
| `relation` | enum | yes | `observed`, `associated`, `supported_interpretation`, `unconfirmed` |
| `event_ids` | array[string] | yes | Referenced events |
| `observation_ids` | array[string] | yes | Referenced observations |
| `supporting_source_ids` | array[string] | yes | Sources supporting the proposition |
| `contradicting_evidence_ids` | array[string] | yes | Explicit conflicts |
| `confidence_score` | number | yes | `0.0–1.0` |
| `confidence_label` | enum | yes | Derived confidence label |
| `affected_assets` | array[string] | v1.1 | Union of mapped assets from supporting observations |
| `limitations` | array[string] | yes | Missing or uncertain evidence |

Rules:

- `observed` requires at least one observation or primary event source.
- `associated` requires both an event and an observation but must state that cause is unconfirmed.
- `supported_interpretation` requires at least two independent observations or sources.
- `unconfirmed` is mandatory when evidence is conflicting or below the publication threshold.

## 7. `market_signals.json`

Purpose: expose deterministic cross-asset and risk rules before any LLM processing.

### Signal record

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `signal_id` | string | yes | Stable internal ID |
| `rule_id` | string | yes | Versioned deterministic rule |
| `signal_type` | enum | yes | `cross_asset`, `risk`, `trend`, `divergence`, `regime_input` |
| `label` | string | yes | Human-readable name |
| `state` | enum | yes | `active`, `inactive`, `insufficient_data`, `conflicting` |
| `direction` | enum/null | yes | `risk_on`, `risk_off`, `supportive`, `restrictive`, `mixed`, null |
| `strength` | number | yes | Normalized `0.0–1.0` |
| `observation_ids` | array[string] | yes | Exact inputs |
| `evidence_ids` | array[string] | yes | Supporting evidence |
| `affected_assets` | array[string] | yes | Relevant assets |
| `explanation_template` | string | yes | Deterministic, non-causal explanation |
| `limitations` | array[string] | yes | Missing inputs and caveats |

Example:

```json
{
  "signal_id": "sig_defensive_gold_20260818",
  "rule_id": "gold_usd_yield_alignment_v1",
  "signal_type": "cross_asset",
  "label": "Gold aligned with softer dollar/yields",
  "state": "active",
  "direction": "supportive",
  "strength": 0.72,
  "observation_ids": ["obs_gold_daily", "obs_dxy_daily", "obs_us10y_daily"],
  "evidence_ids": ["evd_gold_usd_yield_20260818"],
  "affected_assets": ["GOLD", "EURUSD", "USDJPY"],
  "explanation_template": "Gold strengthened while the dollar and yields softened; this alignment is supportive, but the specific cause is unconfirmed.",
  "limitations": []
}
```

## 8. Regime Contract

The regime is embedded in `market_signals.json` and copied into `daily_intelligence.json`:

```json
{
  "classification": "mixed",
  "score": 0.08,
  "confidence_score": 0.61,
  "confidence_label": "medium",
  "supporting_signal_ids": ["sig_example_1"],
  "conflicting_signal_ids": ["sig_example_2"],
  "missing_inputs": ["market_breadth"],
  "rule_version": "market_regime_v1"
}
```

Allowed classifications are `risk_on`, `risk_off` and `mixed`. This is a current-state classification, not a forecast.

## 9. `daily_intelligence.json`

Purpose: act as the single allowed factual input to deterministic and LLM brief generators.

### Top-level contract

| Field | Type | Required |
|---|---|---:|
| Common artifact envelope | object fields | yes |
| `data_window` | object | yes |
| `coverage` | object | yes |
| `regime` | Regime | yes |
| `top_events` | array[IntelligenceItem] | yes |
| `market_overview` | array[Claim] | yes |
| `asset_sections` | object | yes |
| `cross_asset_signals` | array[SignalReference] | yes |
| `next_48_hours` | array[EventReference] | yes |
| `risk_monitor` | array[Claim] | yes |
| `sources` | array[SourceReference] | yes |
| `disclaimer` | string | yes |

### Claim

```json
{
  "claim_id": "clm_overview_01_20260818",
  "text": "Risk conditions are mixed across equities, crypto and defensive assets.",
  "relation": "supported_interpretation",
  "confidence_score": 0.64,
  "confidence_label": "medium",
  "evidence_ids": ["evd_example_1", "evd_example_2"],
  "signal_ids": ["sig_example_1", "sig_example_2"],
  "source_ids": ["src_example_1"],
  "limitations": ["Market breadth was unavailable."]
}
```

### Intelligence item

```json
{
  "rank": 1,
  "event_id": "evt_example_1",
  "headline": "Normalized event title",
  "why_it_matters": "Source-grounded explanation of relevance.",
  "affected_assets": ["SPY", "QQQ"],
  "relevance_score": 0.86,
  "confidence_score": 0.81,
  "confidence_label": "high",
  "evidence_ids": ["evd_example_1"],
  "source_ids": ["src_example_1"],
  "causality": "unconfirmed"
}
```

### Asset sections

```json
{
  "equities": [],
  "crypto": [],
  "gold_dollar_commodities": [],
  "forex": []
}
```

Each section contains Claim objects. Sections with insufficient data remain present and contain a claim explaining the limitation.

## 10. Required Report Mapping

| Report section | Contract source |
|---|---|
| Today's Three Most Important Events | `top_events` |
| Market Overview | `regime` + `market_overview` |
| US Equities | `asset_sections.equities` |
| Crypto | `asset_sections.crypto` |
| Gold / Dollar / Commodities | `asset_sections.gold_dollar_commodities` |
| Forex | `asset_sections.forex` |
| Cross Asset Signals | `cross_asset_signals` |
| Next 48 Hours Events | `next_48_hours` |
| Risk Monitor | `risk_monitor` + `warnings` |
| Sources & Timestamp | `sources` + envelope + `data_window` |

The generator may change wording and ordering within a section but cannot introduce facts absent from these fields.

## 11. Validation Rules

An artifact is invalid if any of the following applies:

- a referenced ID does not resolve within the current run artifacts.
- an event has no source reference.
- a source URL is missing or not HTTP(S).
- `generated_at`, `as_of`, `published_at` or `scheduled_at` is malformed.
- confidence label does not match its numeric range.
- a `supported_interpretation` has fewer than two supporting inputs.
- a claim contains a concrete number that is absent from its observations.
- a top event has no relevance reason or affected assets.
- a scheduled event appears in the past without a resolved status.
- a failed or stale input is represented as current.

## 12. Versioning and Compatibility

- Additive optional fields increment the minor version.
- Removing fields, changing meanings or changing enum values increments the major version.
- Readers must reject unsupported major versions.
- Writers must not silently convert an older major version.
- Generated reports must record the exact schema and rule versions used.
- `market_snapshot.json` remains version `1.x` until a separately approved migration is required.
- Observation and evidence artifacts use `1.1` after macro mapping and confidence fields were added; validators continue to accept supported `1.x` artifacts.
