# Phase 6.4-A Structured Daily Intelligence Contract

> Status: implementation contract. This phase assembles validated structured
> objects only. It does not summarize, interpret, rank, generate prose, call an
> LLM, score sentiment, predict markets, classify bullish/bearish conditions,
> or recommend trades.

## 1. Purpose and boundary

The composer consumes exactly four linked artifacts:

```text
evidence_bundle.json
market_signals.json
market_regime.json
risk_monitor.json
        ↓
Structured Intelligence Composer
        ↓
daily_intelligence.json
```

The composer performs only these operations:

- validate the four input artifacts and their run linkage;
- wrap existing Signal, Regime and Risk objects in a common contract;
- partition existing Risk objects by their existing categories;
- resolve referenced Evidence records into a provenance catalog;
- calculate artifact coverage and timestamp windows;
- sort objects using fixed non-ranking rules.

It does not create a market claim, explanation, “top” item, relevance score,
opinion, or new financial fact.

## 2. Required input linkage

All inputs must pass their existing deterministic validators.

- `market_signals.input_run_id` equals `evidence_bundle.run_id`;
- Regime input references equal the Evidence and Signal run IDs;
- Risk Monitor input references equal the Evidence, Signal and Regime run IDs;
- all four artifacts have the same `report_date`;
- generation order is Evidence → Signals → Regime → Risk Monitor → Composer;
- future-dated input beyond five minutes is rejected.
- inputs older than 24 hours at composition time are marked stale and cannot
  support current substantive intelligence.

Structural, reference, deterministic-validation or run-linkage errors abort
composition. A valid upstream `partial` or `unavailable` artifact is assembled
without synthetic replacement data.

## 3. Intelligence object contract

Every assembled Signal, Regime or Risk item uses the same wrapper:

```json
{
  "object_id": "int_signal_sig_example",
  "object_type": "cross_asset_signal",
  "source_artifact": "market_signals.json",
  "source_run_id": "run_signals",
  "source_generated_at": "2026-08-27T04:00:00Z",
  "validation_status": "validated",
  "data_status": "observed",
  "timestamps": {
    "observed_at": [],
    "scheduled_at": [],
    "detected_at": []
  },
  "evidence_refs": {},
  "payload": {}
}
```

Rules:

- `payload` is an exact copy of the validated upstream object;
- `validation_status` is fixed as `validated`; invalid objects never enter the
  output;
- `data_status` copies the upstream state/status and is never upgraded;
- the wrapper adds no analytical label or text;
- `object_id` is deterministic from object type, source run and source object
  ID;
- timestamps are copied or collected from the payload and referenced records;
- references are normalized into the common provenance-reference contract.

Object types:

- `market_regime`: exactly one wrapper, even when classification is null;
- `cross_asset_signal`: one wrapper for every validated Signal rule;
- `upcoming_event_risk`: Risk items already categorized `upcoming_event`;
- `data_quality_risk`: Risk items already categorized `data_quality`;
- `market_stress_risk`: Risk items already categorized `market_stress`.

The composer does not filter stale or unavailable objects out. Their original
status remains visible so downstream consumers cannot mistake them for current
intelligence.

## 4. Output sections

```json
{
  "market_regime": {},
  "cross_asset_signals": [],
  "upcoming_events": [],
  "data_quality_risks": [],
  "observed_market_stress": []
}
```

These sections are mechanical partitions, not ranked selections:

- `market_regime` wraps the full Regime artifact's classification object;
- `cross_asset_signals` contains all Signal records;
- the three Risk sections contain every Risk record from the matching existing
  category;
- no section is renamed to “top”, “important”, “best”, or “actionable”.

## 5. Provenance reference contract

Every intelligence object contains these sorted unique arrays:

- `artifact_run_ids`
- `evidence_bundle_ids`
- `source_ids`
- `observation_ids`
- `event_ids`
- `evidence_ids`
- `signal_ids`
- `regime_dimension_ids`
- `risk_ids`
- `coverage_inputs`

References already present upstream are retained. The composer may add the
source artifact run ID and the source object's own ID, but may not remove any
upstream reference.

Evidence-layer references must resolve in the output `provenance_catalog`:

```json
{
  "evidence_bundles": [],
  "source_records": [],
  "observation_records": [],
  "event_records": [],
  "evidence_records": []
}
```

Catalog records are copied exactly from `evidence_bundle.json` and sorted by
their stable IDs. Evidence Bundle catalog entries retain type, related assets,
timestamps, verification level, data quality, freshness and provenance. Only
records referenced by assembled intelligence objects are included; the
composer does not create references for unused facts.

Signal IDs resolve to `cross_asset_signals`, Regime Dimension IDs resolve
inside the preserved Regime payload, and Risk IDs resolve in the three Risk
sections. Artifact run IDs resolve through `input_refs` and `coverage`.

## 6. Timestamp preservation

Each wrapper contains:

- exact `source_generated_at`;
- all relevant `observed_at` values from Signal/Regime observations;
- exact `scheduled_at` and `detected_at` values from Risk time windows;
- no inferred event time.

Top-level `data_window` records sorted unique input-generation, observation,
scheduled, detected, published and retrieved timestamps, plus the earliest and
latest value for each non-empty category. Empty categories use empty arrays and
null boundaries.

## 7. Input validation and data quality

Top-level `coverage` contains exactly four records in this order:

1. `evidence_bundle.json`
2. `market_signals.json`
3. `market_regime.json`
4. `risk_monitor.json`

Each record includes:

- artifact name/type and run ID;
- source generation timestamp;
- `validation_status: validated`;
- original upstream `data_status`;
- object count;
- current/stale record freshness status when the input exposes it;
- current/stale artifact freshness based on composition-time age;
- artifact age in hours and the fixed 24-hour maximum age;
- original warning count.

No upstream status is normalized from unavailable to partial or available.

The composer records deterministic warning codes only:

- `upstream_partial:<artifact>`
- `upstream_unavailable:<artifact>`
- `upstream_stale:<artifact>`
- `no_current_substantive_intelligence`
- `provenance_catalog_empty`

It does not rewrite upstream warnings into new prose.

## 8. Available, partial and unavailable behavior

Substantive current intelligence means at least one of:

- a non-null validated Regime classification;
- a Signal with state `observed` or `not_observed` and available data quality;
- an existing upcoming-event or market-stress Risk item.

Data-quality Risk items remain important but do not count as substantive market
intelligence.

Output status:

- `available`: substantive current intelligence exists and all four upstream
  artifacts are available and no artifact is older than 24 hours;
- `partial`: substantive current intelligence exists, but at least one upstream
  artifact is partial or unavailable while the supporting artifact chain is
  current;
- `unavailable`: no substantive current intelligence exists. Valid data-quality
  objects and provenance are still preserved. This includes runs where the
  relevant upstream artifact chain is older than 24 hours.

Unavailable does not trigger guessed values, placeholder events, a neutral
Regime, or generated commentary.

## 9. Output schema

```json
{
  "schema_version": "1.0",
  "artifact_type": "daily_intelligence",
  "run_id": "run_20260827T040000Z_intelligence_ab12cd34",
  "report_date": "2026-08-27",
  "generated_at": "2026-08-27T04:00:00Z",
  "status": "partial",
  "composition_scope": "validated_structured_intelligence",
  "schema_contract": "daily_intelligence_v1",
  "input_refs": {
    "evidence_bundle_run_id": "run_evidence",
    "market_signals_run_id": "run_signals",
    "market_regime_run_id": "run_regime",
    "risk_monitor_run_id": "run_risk"
  },
  "data_window": {},
  "coverage": [],
  "object_counts": {},
  "market_regime": {},
  "cross_asset_signals": [],
  "upcoming_events": [],
  "data_quality_risks": [],
  "observed_market_stress": [],
  "provenance_catalog": {},
  "warnings": [],
  "limitations": [
    "structured_assembly_only",
    "no_new_interpretation",
    "no_market_outlook_or_trade_action"
  ]
}
```

## 10. Ordering rules

Ordering is deterministic and does not express importance:

- Signals: `rule_id`, then `signal_id`;
- each Risk section: `rule_id`, relevant timestamp, then `risk_id`;
- coverage: fixed pipeline order;
- catalog records: their stable record ID;
- timestamps and all reference arrays: lexical UTC/ID order.

The composer never sorts by confidence, attention level, score, asset return,
or perceived market importance.

## 11. Validation rules

The validator rebuilds the entire output from the four inputs at the recorded
composition time and rejects any difference. It also rejects:

- a missing, duplicate or unknown intelligence object;
- a payload that differs from its upstream object;
- `validation_status` other than `validated`;
- upgraded or changed upstream data status;
- dangling or removed provenance;
- a catalog record that differs from Evidence Bundle input;
- ordering different from the frozen non-ranking rules;
- fabricated values, events, references or timestamps;
- natural-language analysis, generated claims or unsupported text fields;
- sentiment, prediction, bullish/bearish, recommendation, price-target,
  trading-action, ranking or LLM fields/content.

## 12. Acceptance criteria

- exactly four approved artifacts are read;
- complete inputs assemble every validated object with status `available`;
- partial inputs preserve degraded objects and produce status `partial`;
- no current substantive inputs produce status `unavailable` without losing
  data-quality objects;
- every reference resolves and every timestamp is preserved;
- two runs with identical inputs and composition time are byte-equivalent;
- existing tests remain green;
- UI, Telegram, GitHub Pages and scheduler are unchanged.
