# Phase 6.3-A Cross-Asset Relationship Engine

> Status: implementation contract. `evidence_bundle.json` is the only runtime
> input. This phase evaluates observed relationships; it does not predict,
> recommend trades, classify bullish/bearish direction, score sentiment, rank
> assets/events, or call an LLM.

## 1. Purpose and boundary

The engine evaluates versioned deterministic relationships between existing
daily-change observations:

```text
evidence_bundle.json
        ↓
Cross-Asset Relationship Engine
        ↓
market_signals.json
```

In this phase, “signal” means an auditable rule evaluation describing whether
an observed relationship exists in the supplied data. It is not a trading
signal, forecast, recommendation, causal explanation, or market regime.

The Phase 6.3-A contract supersedes older draft fields such as `direction`,
`strength`, `risk_on`, `risk_off`, `supportive`, and `restrictive`. Those fields
are prohibited from this runtime output.

## 2. Artifact contract

`market_signals.json` envelope:

| Field | Type | Rule |
|---|---|---|
| `schema_version` | string | Fixed as `1.0` |
| `artifact_type` | string | Fixed as `market_signals` |
| `run_id` | string | Stable for the input run and evaluation time |
| `report_date` | date | Copied from the consolidated input |
| `generated_at` | UTC timestamp | Engine evaluation time |
| `status` | enum | `available`, `partial`, or `unavailable` |
| `input_artifact` | string | Fixed as `evidence_bundle.json` |
| `input_run_id` | string | Exact consolidated artifact run ID |
| `rule_set_version` | string | Fixed as `cross_asset_rules_v1` |
| `warnings` | array[string] | Missing/stale/partial-input disclosures |
| `signal_count` | integer | Number of rule evaluations |
| `observed_count` | integer | Evaluations with state `observed` |
| `signals` | array[RelationshipSignal] | One evaluation per registered rule |

Artifact status:

- `available`: input is available and every rule has current required data;
- `partial`: at least one rule can be evaluated or disclosed, but the input or
  one or more rules are stale/incomplete;
- `unavailable`: the input is unavailable or no registered rule has any usable
  observation.

No missing relationship is replaced by an assumed value.

## 3. Signal contract

```json
{
  "signal_id": "sig_equity_index_co_movement_v1_ab12cd34",
  "rule_id": "equity_index_co_movement_v1",
  "signal_type": "cross_asset_relationship",
  "relationship_kind": "co_movement",
  "label": "SPY and QQQ daily co-movement",
  "state": "observed",
  "condition_met": true,
  "required_assets": ["SPY", "QQQ"],
  "observed_values": [],
  "rule_evaluation": {},
  "evidence_refs": {},
  "confidence": {},
  "data_quality": {},
  "limitations": []
}
```

Required fields:

| Field | Meaning |
|---|---|
| `signal_id` | Deterministic ID from rule ID and referenced observations |
| `rule_id` | Versioned rule identifier |
| `signal_type` | Fixed as `cross_asset_relationship` |
| `relationship_kind` | `co_movement`, `inverse_movement`, `divergence`, or `quote_alignment` |
| `label` | Neutral description without interpretation or direction advice |
| `state` | `observed`, `not_observed`, `stale_data`, or `insufficient_data` |
| `condition_met` | Boolean when all inputs exist; `null` when insufficient |
| `required_assets` | Exact subjects required by the rule |
| `observed_values` | Values copied from input observations |
| `rule_evaluation` | Operators, thresholds and deterministic result |
| `evidence_refs` | Complete bundle/source/observation/Evidence references |
| `confidence` | Confidence in the data-backed evaluation, not future outcome |
| `data_quality` | Missing/stale input disclosure |
| `limitations` | Fixed non-causal caveats |

### 3.1 State semantics

- `observed`: all inputs are current and the deterministic condition is true;
- `not_observed`: all inputs are current and the condition is false;
- `stale_data`: all inputs exist, but one or more are stale; `condition_met` may
  record the historical calculation but the relationship is not current;
- `insufficient_data`: at least one required observation is absent or invalid;
  `condition_met` is `null`.

Only `observed` increments `observed_count`. `not_observed` is not a contrary
prediction. `stale_data` is not silently promoted to `observed`.

## 4. Rule format

Rules are code-defined immutable records:

```json
{
  "rule_id": "gold_dollar_inverse_move_v1",
  "relationship_kind": "inverse_movement",
  "required_inputs": [
    {"asset": "GOLD", "metric": "daily_change_pct"},
    {"asset": "DXY", "metric": "daily_change_pct"}
  ],
  "operator": "opposite_sign",
  "minimum_absolute_move": {
    "GOLD": 0.10,
    "DXY": 0.10
  },
  "maximum_time_gap_hours": 36
}
```

Every rule must specify:

- versioned rule ID;
- required asset/metric pairs;
- neutral relationship kind and label;
- deterministic operator;
- thresholds with units;
- maximum allowed observation-time gap;
- fixed limitation text.

No rule may reference news wording, sentiment, price targets, event ranking, or
future values.

## 5. Phase 6.3-A rules

| Rule ID | Required observations | Condition |
|---|---|---|
| `equity_index_co_movement_v1` | SPY, QQQ daily % change | Same non-zero sign; each absolute move ≥ 0.10% |
| `crypto_co_movement_v1` | BTC-USD, ETH-USD daily % change | Same non-zero sign; each absolute move ≥ 0.10% |
| `equity_crypto_co_movement_v1` | SPY, QQQ, BTC-USD daily % change | All have same non-zero sign; each absolute move ≥ 0.10% |
| `equity_volatility_inverse_move_v1` | SPY, QQQ, VIX daily % change | SPY/QQQ same sign and VIX opposite; thresholds ≥ 0.10% |
| `gold_dollar_inverse_move_v1` | GOLD, DXY daily % change | Opposite signs; each absolute move ≥ 0.10% |
| `dollar_fx_quote_alignment_v1` | DXY, EURUSD, USDJPY daily % change | EURUSD opposite DXY and USDJPY same as DXY; thresholds ≥ 0.05% |
| `equity_index_divergence_v1` | SPY, QQQ daily % change | Opposite signs and absolute spread ≥ 1.00 percentage point |
| `dollar_yield_co_movement_v1` | DXY daily %, US10Y daily bps | Same non-zero sign; DXY ≥ 0.10%, US10Y ≥ 1 bp |

All required observation timestamps must be within 36 hours of one another.
Sign comparison across different units is permitted only where the rule states
it explicitly; values are never arithmetically combined across incompatible
units.

## 6. Observed values and evidence references

Each observed value contains:

```json
{
  "asset": "GOLD",
  "metric": "daily_change_pct",
  "value": 1.5,
  "unit": "percent",
  "as_of": "2026-08-26T04:00:00Z",
  "observation_id": "obs_gold_daily",
  "source_id": "src_market",
  "evidence_bundle_ids": ["ebd_example"]
}
```

`evidence_refs` contains sorted unique arrays of:

- `evidence_bundle_ids`
- `source_ids`
- `observation_ids`
- `event_ids`
- `evidence_ids`

All IDs must resolve inside `evidence_bundle.json`. Events are referenced only
when they are already part of the same input bundle as a required observation;
the engine never links an event to a price move merely because timestamps are
close.

When the same observation is embedded in multiple bundles, all bundle,
Evidence and source provenance is retained. The numerical observation is used
once per rule.

## 7. Confidence handling

Confidence describes reliability of the deterministic evaluation, not the
probability of a forecast or the economic importance of a relationship.

```text
base_confidence = minimum input observation confidence_score

current complete input: base_confidence
stale input:           min(base_confidence × 0.50, 0.50)
insufficient input:    0.00
```

Labels use the existing thresholds:

- `high`: score ≥ 0.80
- `medium`: score ≥ 0.55
- `low`: score ≥ 0.30
- `insufficient`: score < 0.30

The signal stores `basis: data_quality`, making clear that this is confidence
in source/freshness coverage rather than relationship strength.

## 8. Rule evaluation object

```json
{
  "operator": "opposite_sign",
  "thresholds": {"GOLD": 0.10, "DXY": 0.10},
  "threshold_unit": "percent",
  "maximum_time_gap_hours": 36,
  "actual_time_gap_hours": 1.0,
  "comparison_result": true,
  "rule_version": "v1"
}
```

For mixed-unit rules, thresholds include an explicit unit per asset. The
engine records values and thresholds but does not calculate a normalized
strength score.

## 9. Validation rules

Validation must reject:

- any input other than `evidence_bundle.json`;
- unknown rule IDs or a missing registered-rule evaluation;
- duplicate signal IDs or multiple evaluations for one rule;
- observation, bundle, source, event, or Evidence IDs not resolvable in input;
- a value, unit, metric, timestamp or confidence score that differs from the
  referenced input observation;
- `observed` when any required input is missing, stale, outside the 36-hour
  window, or fails its threshold/relationship condition;
- `not_observed` when input is missing or stale;
- causal or predictive language;
- fields or values representing `direction`, `strength`, bullish/bearish,
  sentiment, ranking, recommendation, forecast, price target, regime, or trade;
- an unsupported number in any human-readable text.

The validator recalculates rule results from the referenced observations. It
does not trust the emitted state or `condition_met` value.

## 10. Failure behavior

- Unavailable input produces an `unavailable` artifact with all rules marked
  `insufficient_data` and no fabricated values.
- Partial input evaluates each rule independently.
- Missing required assets produce `insufficient_data` for only affected rules.
- Stale required observations produce `stale_data` even when the mathematical
  condition is true.
- Conflicting duplicate observations for the same asset/metric are treated as
  insufficient and disclosed; the engine does not choose one silently.

## 11. Acceptance criteria

- `evidence_bundle.json` is the sole runtime input;
- all eight rules produce deterministic evaluations;
- every concrete value and ID resolves to the consolidated evidence artifact;
- stale and missing inputs cannot produce `observed` state;
- no event-price causality is created;
- no LLM, prediction, sentiment, ranking, regime, trading signal, or
  bullish/bearish label is present;
- existing tests remain green.
