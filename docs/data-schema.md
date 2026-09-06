# AI Market Intelligence Pipeline — Data Contracts v1.0

> 本文件定義 v2 pipeline 的 canonical JSON contracts。它是架構規格，不代表模組已經實作。

Phase 6.2-C 的 provider-boundary `news_items.json`、news-to-event
normalization metadata、copyright rules 及 implementation gates 詳見
[news-event-schema.md](news-event-schema.md)。

News event 的 `verification_level` 與 quality scores 不代表真實概率。
Canonical event 的資料健康仍由 `status` 表示；事件演進則使用獨立的
`lifecycle_status`、`event_version` 及 transition metadata。

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
| `artifact_type` | string | yes | Provider artifacts：`macro_snapshot`、`economic_calendar`、`news_items`；canonical artifacts：`events`、`observations`、`evidence`、`market_signals`、`daily_intelligence` |
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

Current schema version: `1.1`.

Phase 6.2-B adds a bounded provider artifact for official BLS releases in the
next 48 hours. Phase 7.1-C retains the BLS ICS source as primary and adds the
official BEA release schedule as a priority-2 independent fallback source. It is
an input to the future Event Normalizer, not a substitute for canonical
`events.json`.

| Field | Meaning |
|---|---|
| `event_id` | Deterministic ID derived from normalized name and UTC schedule |
| `event_type` | Fixed as `economic_event` at the provider-artifact boundary |
| `name` / `scheduled_at` | Source-grounded release name and UTC time |
| `country` | `US` for approved BLS and BEA sources |
| `impact` | Deterministic `high`, `medium` or `low` release-class rule |
| `affected_assets` / `topics` | Candidate relevance mapping, not confirmed impact |
| `source` / `publisher` / `source_url` | Provenance retained from the official feed |
| `retrieved_at` / `content_hash` | Retrieval timestamp and exact VEVENT fingerprint |
| `status` | `scheduled`; unavailable source produces no event records |
| `confidence_score` / `confidence_label` | Confidence that the official schedule is represented accurately |
| `verification_level` | `official_primary`, `official_fallback`, `official_corroborated`, or `official_conflict` |
| `provenance` | Every official representation supporting this exact source schedule |
| `conflict_group_id` | Shared deterministic ID when official representations publish different times |

The artifact-level `sources` array records both source attempts, priority,
format, retrieval health, parsed/accepted counts, failure classification, and
retryability. Agreeing representations produce one event with both provenance
links. Conflicting schedules remain separate event records and make the artifact
`partial`; they are never averaged or silently overwritten.

Artifact-level `status` is `complete`, `partial`, or `failed`. Both approved
sources failing must produce a failed envelope, warnings, and an empty `events`
list. Primary failure with official fallback success is partial but retains real
events. The combined boundary covers selected BLS and BEA releases but not FOMC,
Treasury, or private-sector calendars.

`failure_type` is `null` when the primary representation is valid and no source
conflict exists, even when the bounded window contains no scheduled events.
Individual attempts classify primary/fallback access and validation errors. The
artifact uses `all_sources_unavailable`, `source_conflict`, the degrading primary
failure type, or `event_validation_error` as applicable.

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

News-normalized events additionally include a versioned `normalization` object
with input NewsItem IDs, rule/mapping IDs, normalized action, non-probabilistic
quality scores, verification level, and deduplication rule/score. Lifecycle is
kept separately in `event_version`, `lifecycle_status`,
`lifecycle_updated_at`, `lifecycle_reason_code`, and
`retraction_source_ids`. Phase 6.2-C2 leaves `summary`, `occurred_at`,
`scheduled_at` null and `candidate_assets` empty; publication time remains in
each `source_ref`. Unsupported accepted records appear in the artifact-level
`normalization_rejections` audit.

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

## 5. `evidence_bundle.json`

Purpose: provide one validated factual boundary for future Intelligence
processing without changing or interpreting the input records.

The `1.0` envelope contains:

- `status`: `available`, `partial`, or `unavailable`;
- one coverage record for market observations, macro observations, economic
  calendar, news events, and existing Evidence;
- `bundles`: complete embedded source, observation, event and Evidence records;
- `rejections`: invalid record IDs and deterministic reason codes;
- counts, warnings, run ID, report date, and consolidation timestamp.

Each bundle contains:

- stable `id` and factual `type`;
- explicit `related_assets` copied only from existing input mappings;
- `source_records`, `observations`, `events`, and `evidence_records`;
- observed, occurred, scheduled, published, retrieved and consolidated times;
- verification level, data quality and freshness;
- provenance containing every source, observation, event and Evidence ID.

Exact duplicate Evidence facts may share one bundle, but their complete records
and provenance links remain present. Unreferenced valid observations/events are
retained as standalone bundles. Missing inputs never create placeholder facts.
The complete contract and guardrails are defined in
[evidence-model.md](evidence-model.md).

## 6. `observations.json`

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

## 7. `evidence.json`

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

## 8. `market_signals.json`

Purpose: expose deterministic descriptions of same-window cross-asset
relationships before any later Intelligence processing. Phase 6.3-A accepts
only `evidence_bundle.json` and does not use an LLM.

### Signal record

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `signal_id` | string | yes | Stable ID from rule and observation references |
| `rule_id` | string | yes | Versioned deterministic rule |
| `signal_type` | string | yes | Fixed as `cross_asset_relationship` |
| `relationship_kind` | enum | yes | Co-movement, inverse movement, divergence, or quote alignment |
| `label` | string | yes | Neutral descriptive rule name |
| `state` | enum | yes | `observed`, `not_observed`, `stale_data`, or `insufficient_data` |
| `condition_met` | boolean/null | yes | Deterministic result; null with insufficient data |
| `required_assets` | array[string] | yes | Exact rule operands |
| `observed_values` | array[object] | yes | Values copied from input observations |
| `rule_evaluation` | object | yes | Operator, thresholds, time gap and comparison result |
| `evidence_refs` | object | yes | Bundle/source/observation/event/Evidence IDs |
| `confidence` | object | yes | Confidence in data-backed evaluation only |
| `data_quality` | object | yes | Missing, stale and conflicting inputs |
| `limitations` | array[string] | yes | Fixed non-causal caveats |

Example:

```json
{
  "signal_id": "sig_gold_dollar_inverse_move_v1_a1b2c3d4",
  "rule_id": "gold_dollar_inverse_move_v1",
  "signal_type": "cross_asset_relationship",
  "relationship_kind": "inverse_movement",
  "label": "Gold and DXY inverse daily movement",
  "state": "observed",
  "condition_met": true,
  "required_assets": ["GOLD", "DXY"],
  "observed_values": [
    {
      "asset": "GOLD",
      "metric": "daily_change_pct",
      "value": 1.5,
      "unit": "percent",
      "as_of": "2026-08-26T04:00:00Z",
      "observation_id": "obs_gold_daily",
      "source_id": "src_market",
      "evidence_bundle_ids": ["ebd_gold"]
    }
  ],
  "rule_evaluation": {
    "operator": "opposite_sign",
    "comparison_result": true
  },
  "evidence_refs": {
    "evidence_bundle_ids": ["ebd_gold", "ebd_dxy"],
    "source_ids": ["src_macro", "src_market"],
    "observation_ids": ["obs_dxy_daily", "obs_gold_daily"],
    "event_ids": [],
    "evidence_ids": ["evd_dxy", "evd_gold"]
  },
  "confidence": {"score": 0.75, "label": "medium", "basis": "data_quality"},
  "data_quality": {"status": "available", "issues": []},
  "limitations": ["The relationship does not establish causality or persistence."]
}
```

Phase 6.3-A prohibits `direction`, `strength`, bullish/bearish labels,
sentiment, ranking, recommendation, prediction, price target, regime and trade
fields. The complete rule and validation contract is defined in
[cross-asset-engine.md](cross-asset-engine.md).

## 9. `market_regime.json`

Purpose: classify current observed cross-market conditions without modifying
the frozen `market_signals.json` schema.

```json
{
  "schema_version": "1.0",
  "artifact_type": "market_regime",
  "status": "available",
  "classification_scope": "current_observed_conditions",
  "classification": "mixed",
  "rule_set_version": "market_regime_rules_v1",
  "input_refs": {
    "evidence_bundle_run_id": "run_evidence",
    "market_signals_run_id": "run_signals"
  },
  "input_freshness": {},
  "score": {},
  "confidence": {},
  "dimensions": [],
  "evidence_refs": {},
  "warnings": [],
  "limitations": []
}
```

Allowed classifications are `risk_on`, `risk_off`, `mixed`, or null when
current coverage is insufficient. A valid classification requires at least
three eligible dimensions, weight coverage of at least `0.65`, and a current
Equity or Volatility anchor. All concrete values and IDs must resolve through
the exact input runs. The full contract is defined in
[market-regime-classifier.md](market-regime-classifier.md).

## 10. `risk_monitor.json`

Purpose: expose only observable scheduled-event, data-quality and current
market-stress conditions from the three linked Evidence, Signal and Regime
artifacts.

```json
{
  "schema_version": "1.0",
  "artifact_type": "risk_monitor",
  "status": "partial",
  "monitor_scope": "observable_risk_conditions",
  "rule_set_version": "risk_monitor_rules_v1",
  "input_refs": {
    "evidence_bundle_run_id": "run_evidence",
    "market_signals_run_id": "run_signals",
    "market_regime_run_id": "run_regime"
  },
  "input_freshness": {},
  "risk_count": 1,
  "category_counts": {
    "upcoming_event": 0,
    "data_quality": 1,
    "market_stress": 0
  },
  "risks": [],
  "warnings": [],
  "limitations": []
}
```

Every risk includes a frozen rule ID, category, status, attention level,
structured observed facts, time window, verification metadata, limitations and
complete artifact/bundle/source/observation/event/Evidence/Signal/Regime
Dimension references. There is no aggregate risk score. The complete contract
is defined in [risk-monitor.md](risk-monitor.md).

## 11. `daily_intelligence.json` v1

Purpose: assemble the four validated upstream artifacts into one deterministic,
traceable input for a future brief layer. Phase 6.4-A does not create claims,
select events, rank items, summarize, generate prose or invoke an LLM.

### Top-level contract

| Field | Type | Required |
|---|---|---:|
| Common artifact envelope | object fields | yes |
| `composition_scope` | string | yes |
| `input_refs` | object | yes |
| `data_window` | object | yes |
| `coverage` | array[Coverage] | yes |
| `object_counts` | object | yes |
| `market_regime` | IntelligenceObject | yes |
| `cross_asset_signals` | array[IntelligenceObject] | yes |
| `upcoming_events` | array[IntelligenceObject] | yes |
| `data_quality_risks` | array[IntelligenceObject] | yes |
| `observed_market_stress` | array[IntelligenceObject] | yes |
| `provenance_catalog` | object | yes |
| `warnings` | array[string] | yes |
| `limitations` | array[string] | yes |

Every `IntelligenceObject` contains a deterministic ID, exact source artifact
and run IDs, source generation time, `validation_status`, original upstream
data status, observed/scheduled/detected timestamps, normalized provenance
references and an unchanged upstream payload.

Coverage retains both upstream record freshness and the artifact age measured
at composition time. An artifact older than 24 hours is stale and cannot
support current substantive intelligence. Complete field definitions and
ordering rules are frozen in
[daily-intelligence-schema.md](daily-intelligence-schema.md).

## 12. Deterministic Brief Mapping

| Report section | Contract source |
|---|---|
| Current Regime | `market_regime` |
| Cross Asset Signals | `cross_asset_signals` |
| Upcoming Event Risks | `upcoming_events` |
| Data Quality Risks | `data_quality_risks` |
| Observed Market Stress | `observed_market_stress` |
| Sources & Timestamp | `provenance_catalog` + envelope + `data_window` |

Phase 6.4-B1 renders this mapping mechanically into
`daily_market_brief.md`. It retains upstream order, status, timestamps,
warnings and all provenance-reference arrays. It does not select, summarize or
rewrite the intelligence objects. The complete Markdown contract is defined in
[brief-renderer.md](brief-renderer.md).

## 13. Validation Rules

An artifact is invalid if any of the following applies:

- a referenced ID does not resolve within the current run artifacts.
- an event has no source reference.
- an assembled payload differs from its validated upstream object.
- an intelligence object does not have `validation_status: validated`.
- a source generation or record timestamp is malformed.
- a provenance reference cannot be resolved in its designated catalog or
  assembled section.
- an upstream partial, unavailable or stale state is upgraded.
- deterministic reconstruction from the four recorded inputs differs.
- a prohibited prediction, sentiment, ranking, recommendation, LLM or
  bullish/bearish field is introduced.

## 14. Versioning and Compatibility

- Additive optional fields increment the minor version.
- Removing fields, changing meanings or changing enum values increments the major version.
- Readers must reject unsupported major versions.
- Writers must not silently convert an older major version.
- Generated reports must record the exact schema and rule versions used.
- `market_snapshot.json` remains version `1.x` until a separately approved migration is required.
- Observation and evidence artifacts use `1.1` after macro mapping and confidence fields were added; validators continue to accept supported `1.x` artifacts.
