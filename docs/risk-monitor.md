# Phase 6.3-C Risk Monitor

> Status: implementation contract. The monitor reports observable risk
> conditions only. It does not predict crashes, forecast prices, classify
> bullish/bearish conditions, recommend trades, or call an LLM.

## 1. Purpose and boundary

The monitor consumes exactly three linked artifacts:

```text
evidence_bundle.json
market_signals.json
market_regime.json
        ↓
Deterministic Risk Monitor
        ↓
risk_monitor.json
```

“Risk” means one of the following factual conditions:

- an official event is scheduled within the next 48 hours;
- input coverage, freshness or validation quality is degraded;
- current, non-stale market observations satisfy a frozen stress rule.

An item is not a probability, price outlook, crash warning, trading signal, or
instruction. Absence of a risk item does not mean that an asset is safe.

## 2. Input linkage

All three inputs are mandatory and must pass their existing validators.

- `market_signals.input_run_id` equals `evidence_bundle.run_id`;
- `market_regime.input_refs.evidence_bundle_run_id` equals the Evidence run;
- `market_regime.input_refs.market_signals_run_id` equals the Signal run;
- all three artifacts have the same `report_date`;
- generation order is Evidence → Signals → Regime → Risk Monitor;
- future-dated inputs beyond five minutes are rejected.

A structural, linkage or deterministic-validation error aborts generation.
Stale or partial but structurally valid inputs remain useful for data-quality
risk items; they cannot produce market-stress or upcoming-event items unless
their specific supporting records are current.

## 3. Risk item schema

Each item contains:

| Field | Meaning |
|---|---|
| `risk_id` | Deterministic ID from rule and referenced records |
| `rule_id` | Frozen versioned rule |
| `category` | `upcoming_event`, `data_quality`, or `market_stress` |
| `status` | `scheduled`, `observed`, or `detected` |
| `attention_level` | `high`, `medium`, or `low`; not a probability |
| `title` | Neutral factual label |
| `description` | Deterministic non-causal explanation |
| `related_assets` | Assets copied from input records |
| `time_window` | Observation/event/monitor timestamps |
| `observed_facts` | Exact structured facts used by the rule |
| `evidence_refs` | Complete input and record provenance |
| `verification` | Evidence quality, never likelihood of loss |
| `limitations` | Fixed interpretation boundaries |

Every `evidence_refs` object contains sorted unique arrays for:

- `artifact_run_ids`
- `evidence_bundle_ids`
- `source_ids`
- `observation_ids`
- `event_ids`
- `evidence_ids`
- `signal_ids`
- `regime_dimension_ids`
- `coverage_inputs`

Empty reference types remain present. Every non-artifact ID must resolve in one
of the three input artifacts.

## 4. Upcoming event rules

Rule: `upcoming_official_event_v1`.

An item is emitted for each Evidence Bundle calendar event when:

- bundle type is `calendar_event`;
- event status is `scheduled`;
- `scheduled_at` is after monitor execution and no more than 48 hours ahead;
- event and bundle are not stale;
- at least one source record and its source ID are present;
- the Evidence artifact itself is no more than 24 hours old.

Attention level copies the deterministic calendar impact mapping:

- `high` → high;
- `medium` → medium;
- `low` or unknown → low.

The item states only that the event is scheduled. It does not state how markets
will react or attach the event as a cause of an observed price move.

## 5. Data quality rules

| Rule ID | Trigger |
|---|---|
| `input_coverage_degraded_v1` | Any Evidence coverage record is partial/unavailable or has stale records |
| `consolidation_rejections_present_v1` | Evidence consolidation rejection count is non-zero |
| `market_signal_coverage_degraded_v1` | Signal artifact is partial/unavailable or contains stale/insufficient evaluations |
| `market_regime_coverage_degraded_v1` | Regime artifact is partial/unavailable or classification is null |
| `input_artifact_stale_v1` | Any of the three required artifacts is older than 24 hours |

Attention levels are deterministic:

- unavailable input or null regime: high;
- stale input records, partial input, rejected records, or degraded Signal
  coverage: medium;
- warning-only condition with otherwise available coverage: low.

These are risks to report completeness and trustworthiness, not claims about
market prices.

## 6. Observed market stress rules

All supporting observations must be current, all referenced IDs must resolve,
and the source Signal must have state `observed` with available data quality.

| Rule ID | Observable condition | Attention |
|---|---|---|
| `observed_risk_off_regime_v1` | Current Regime classification is `risk_off` with a valid classification | high |
| `observed_equity_volatility_stress_v1` | SPY and QQQ daily changes are negative while VIX daily change is positive, and the inverse-movement Signal is observed | high |
| `observed_equity_crypto_stress_v1` | SPY, QQQ and BTC-USD daily changes are negative, and their co-movement Signal is observed | high |
| `observed_equity_divergence_v1` | The frozen SPY/QQQ divergence Signal is observed | medium |
| `observed_dollar_yield_pressure_v1` | DXY daily change and US10Y daily basis-point change are both positive, and their co-movement Signal is observed | medium |

The monitor copies exact values into `observed_facts`. It does not describe
these relationships as bullish/bearish, predict persistence, infer a cause, or
convert them into an action.

The regime-level rule and component rules may coexist because they describe
different observable scopes. They are not combined into a crash probability
or severity score.

## 7. Freshness validation

Input artifacts have a maximum age of 24 hours. Each item is also validated at
record level:

- calendar event retrieval and bundle freshness must be current;
- market observations must have `status: success`;
- no supporting ID may appear in a bundle stale-record list;
- Signal state must not be `stale_data` or `insufficient_data`;
- Regime dimensions used by a risk item must be eligible;
- source timestamps and event/observation timestamps are preserved unchanged.

The output `input_freshness` records monitor time, artifact ages, stale
artifact names, stale supporting observation IDs, and status.

## 8. Output schema

```json
{
  "schema_version": "1.0",
  "artifact_type": "risk_monitor",
  "run_id": "run_20260826T120000Z_risk_ab12cd34",
  "report_date": "2026-08-26",
  "generated_at": "2026-08-26T12:00:00Z",
  "status": "partial",
  "monitor_scope": "observable_risk_conditions",
  "rule_set_version": "risk_monitor_rules_v1",
  "input_refs": {
    "evidence_bundle_run_id": "run_evidence",
    "market_signals_run_id": "run_signals",
    "market_regime_run_id": "run_regime"
  },
  "input_freshness": {},
  "risk_count": 2,
  "category_counts": {
    "upcoming_event": 1,
    "data_quality": 1,
    "market_stress": 0
  },
  "risks": [],
  "warnings": [],
  "limitations": []
}
```

Artifact status:

- `available`: all inputs are current and available;
- `partial`: monitor ran but at least one input or supporting record is degraded;
- `unavailable`: reserved for a valid empty input boundary with no auditable
  information; structural/linkage errors abort instead.

Zero market-stress items is a valid result and must not be interpreted as a
guarantee of low future risk.

## 9. Ordering and deduplication

Items are sorted deterministically by category, rule ID, relevant timestamp,
and risk ID. The monitor does not rank risks or calculate an aggregate risk
score. Identical rule/reference combinations share one stable risk ID; all
provenance is retained.

## 10. Validation rules

The validator recalculates the complete artifact from the three inputs and
rejects any difference. It also rejects:

- unknown rules/categories/statuses or duplicate risk IDs;
- dangling Evidence, source, observation, event, Signal or Regime Dimension
  references;
- an upcoming event outside the next 48 hours;
- a market-stress item backed by stale or insufficient data;
- changed values, units, timestamps, event impact or source metadata;
- missing evidence references;
- predictive, causal, crash-probability, bullish/bearish, recommendation,
  price-target or trading language/fields;
- aggregate risk scores, market forecasts or action fields.

## 11. Acceptance criteria

- only the three approved artifacts are read;
- all three risk categories have deterministic fixture coverage;
- upcoming events preserve schedule and official-source provenance;
- degraded inputs produce data-quality risks without fabricated market stress;
- current stress rules preserve exact Signal and Evidence references;
- stale data cannot produce upcoming-event or market-stress items;
- tampering and prohibited content are rejected;
- existing tests remain green.
