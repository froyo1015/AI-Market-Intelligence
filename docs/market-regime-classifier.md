# Phase 6.3-B Market Regime Classifier

> Status: implementation contract. The classifier describes current observed
> conditions only. It does not forecast prices, predict persistence, recommend
> trades, emit trading signals, or call an LLM.

## 1. Purpose and boundary

The classifier consumes exactly two validated artifacts:

```text
evidence_bundle.json + market_signals.json
                    ↓
          Market Regime Classifier
                    ↓
            market_regime.json
```

The allowed current-condition classifications are `risk_on`, `risk_off`, and
`mixed`. When current evidence is insufficient, `classification` is `null`;
the system must not use `mixed` as a substitute for unknown data.

Phase 6.3-B creates a separate artifact and does not add regime fields to the
frozen Phase 6.3-A `market_signals.json` contract.

## 2. Input requirements

Both inputs are mandatory:

- `evidence_bundle.json` must pass the Phase 6.2-D validator;
- `market_signals.json` must pass the Phase 6.3-A validator when recalculated
  from that exact Evidence Bundle;
- `market_signals.input_run_id` must equal `evidence_bundle.run_id`;
- both inputs must have the same `report_date`;
- the signal artifact must not predate its Evidence Bundle;
- neither artifact generation timestamp may be more than 24 hours old at
  classifier execution time.

An input linkage or deterministic-validation failure aborts generation. A
well-formed but old input produces an unavailable artifact with a null
classification and explicit freshness warnings.

## 3. Regime dimensions

The rule set is fixed as `market_regime_rules_v1`.

| Dimension | Weight | Signal input | Current-condition rule |
|---|---:|---|---|
| Equity | 0.30 | `equity_index_co_movement_v1` | SPY and QQQ both higher = `risk_on`; both lower = `risk_off`; otherwise `mixed` |
| Volatility | 0.25 | `equity_volatility_inverse_move_v1` | VIX lower = `risk_on`; VIX higher = `risk_off`; below threshold = `mixed` |
| Crypto | 0.20 | `crypto_co_movement_v1` | BTC-USD and ETH-USD both higher = `risk_on`; both lower = `risk_off`; otherwise `mixed` |
| Dollar/yield | 0.15 | `dollar_yield_co_movement_v1` | DXY and US10Y both lower = `risk_on`; both higher = `risk_off`; otherwise `mixed` |
| Cross-asset alignment | 0.10 | `equity_crypto_co_movement_v1` | SPY, QQQ and BTC-USD all higher = `risk_on`; all lower = `risk_off`; otherwise `mixed` |

“Higher” and “lower” refer only to the daily changes embedded in the input
signal. Each value must also meet that Phase 6.3-A rule's frozen minimum move.
A value below its threshold contributes `mixed`, not an assumed direction.

The dimensions are transparent observations of the same current data window.
Weights express classifier composition only; they are not economic truth
probabilities or trading conviction.

## 4. Dimension eligibility and Evidence requirements

A dimension is eligible only when all conditions hold:

1. its exact registered Phase 6.3-A signal exists once;
2. signal state is `observed` or `not_observed`;
3. signal data-quality status is `available`;
4. all required asset/metric observations are present;
5. every observation ID, source ID, Evidence ID and bundle ID resolves in
   `evidence_bundle.json`;
6. each required observation is successful, is absent from all stale-record
   lists, and has the exact value/unit/timestamp emitted in the signal;
7. the signal's maximum comparison window and thresholds are unchanged from
   the frozen Phase 6.3-A rule.

`stale_data` and `insufficient_data` signals never contribute a dimension.
An ineligible dimension has `observed_state: unavailable`, contribution
`null`, and a deterministic reason code.

Every eligible dimension retains:

- `signal_id` and `rule_id`;
- Evidence Bundle IDs;
- source, observation, event and Evidence IDs;
- the exact observation timestamps used;
- its source signal confidence.

No event is interpreted as the cause of a market move. Event IDs are retained
only as inherited provenance.

## 5. Score and classification

Each eligible dimension contributes:

```text
risk_on  = +1
mixed    =  0
risk_off = -1

weighted_sum = Σ(weight × contribution)
eligible_weight = Σ(weight for eligible dimensions)
normalized_score = weighted_sum / eligible_weight
```

Classification requires:

- at least three eligible dimensions;
- eligible weight of at least `0.65`; and
- at least one eligible anchor dimension: Equity or Volatility.

When those requirements are met:

| Normalized score | Classification |
|---:|---|
| `>= +0.25` | `risk_on` |
| `<= -0.25` | `risk_off` |
| otherwise | `mixed` |

When requirements are not met, classification is `null`. Scores remain in the
artifact for audit but must not be presented as a valid regime.

The score describes current cross-market alignment only. It must never be
worded as a future market direction, persistence claim, probability, or trade.

## 6. Confidence handling

Confidence means confidence in current data coverage and deterministic
classification, not confidence that prices will move in any direction.

For a valid classification:

```text
coverage_score = eligible_weight
input_quality = minimum confidence score among eligible source signals
agreement_score = largest of risk_on/mixed/risk_off eligible weight
                  divided by eligible_weight

confidence_score =
    0.50 × coverage_score
  + 0.25 × input_quality
  + 0.25 × agreement_score
```

For a null classification, confidence is `0.0` and label `insufficient`.
Labels use the existing thresholds: high `>= 0.80`, medium `>= 0.55`, low
`>= 0.30`, otherwise insufficient.

## 7. Freshness validation

The output contains an `input_freshness` object with:

- classifier timestamp;
- each input's generation timestamp and age in hours;
- maximum permitted artifact age (`24` hours);
- stale input artifact names;
- stale supporting observation IDs;
- `current`, `stale`, or `inconsistent` status.

Rules:

- future-dated input beyond five minutes is inconsistent and rejected;
- signal generation earlier than Evidence Bundle generation is inconsistent
  and rejected;
- input age above 24 hours makes every dimension ineligible;
- stale observations make only their dependent dimensions ineligible;
- freshness is checked again from Evidence Bundle records, rather than trusting
  only the signal state.

## 8. Output schema

`market_regime.json`:

```json
{
  "schema_version": "1.0",
  "artifact_type": "market_regime",
  "run_id": "run_20260826T120000Z_regime_ab12cd34",
  "report_date": "2026-08-26",
  "generated_at": "2026-08-26T12:00:00Z",
  "status": "available",
  "classification_scope": "current_observed_conditions",
  "classification": "risk_on",
  "rule_set_version": "market_regime_rules_v1",
  "input_refs": {
    "evidence_bundle_run_id": "run_evidence",
    "market_signals_run_id": "run_signals"
  },
  "input_freshness": {},
  "score": {
    "weighted_sum": 0.75,
    "eligible_weight": 0.85,
    "normalized_score": 0.882353,
    "risk_on_threshold": 0.25,
    "risk_off_threshold": -0.25,
    "minimum_eligible_weight": 0.65,
    "minimum_eligible_dimensions": 3
  },
  "confidence": {
    "score": 0.86,
    "label": "high",
    "basis": "coverage_quality_agreement"
  },
  "dimensions": [],
  "evidence_refs": {},
  "warnings": [],
  "limitations": []
}
```

Artifact status:

- `available`: all five dimensions are eligible and classification is valid;
- `partial`: classification is valid but one or more dimensions are ineligible;
- `unavailable`: classification requirements are not met and classification is
  null.

Each dimension contains `dimension_id`, `weight`, `signal_id`, `rule_id`,
`eligibility`, `observed_state`, `contribution`, `weighted_contribution`,
`observed_values`, `evidence_refs`, `confidence`, and `reason_codes`.

## 9. Validation rules

Validation recalculates the complete output from both inputs and rejects any
difference. It also rejects:

- an unknown, missing or duplicate dimension;
- an unsupported classification or scope;
- a non-null classification below coverage requirements;
- risk-on/risk-off classification from stale or insufficient inputs;
- references that do not resolve in the Evidence Bundle;
- values, units, timestamps, confidence or states different from source input;
- predictive, causal, recommendation, price-target or trading language/fields;
- a score, threshold, weight or contribution different from the frozen rules;
- a run/report-date mismatch between inputs.

## 10. Acceptance criteria

- only `evidence_bundle.json` and `market_signals.json` are read;
- all five deterministic dimensions are present;
- current complete fixtures classify `risk_on`, `risk_off`, and `mixed`;
- stale, missing, old or mismatched inputs fail closed;
- all provenance is preserved and resolvable;
- validator rejects tampering and prohibited predictive/trading content;
- existing tests remain green.
