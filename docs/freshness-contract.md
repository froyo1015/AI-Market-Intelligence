# Phase 7.1-B Shared Freshness Contract

## Purpose

The freshness contract separates three clocks that previously appeared under
different names across the pipeline:

- **source freshness**: when the underlying fact or observation applied;
- **retrieval freshness**: when this system obtained the source material;
- **artifact freshness**: when this system generated the current artifact;
- **run freshness**: the conservative aggregation recorded by the orchestrator.

Freshness is metadata only. It must not change Signal rules, Regime scoring,
Risk detection, intelligence selection, or any trading behavior.

## Canonical schema

Every JSON artifact exposes these top-level fields:

```json
{
  "freshness_contract_version": "1.0",
  "source_timestamp": "2026-08-27T04:00:00Z",
  "retrieved_at": "2026-08-27T17:32:39Z",
  "generated_at": "2026-08-27T17:32:42Z",
  "age_seconds": 48762.0,
  "freshness_status": "current",
  "freshness_basis": "source_timestamp",
  "stale_after_seconds": 172800
}
```

Required fields may be `null` only as follows:

- `source_timestamp`: null when the source supplies no observation/publication
  timestamp or the source is unavailable;
- `retrieved_at`: null only when no retrieval timestamp can be established;
- `age_seconds`: null for `unavailable` or `unknown` freshness;
- `stale_after_seconds`: null only for run/module aggregation records that do
  not perform a second threshold calculation.

`generated_at`, `freshness_contract_version`, and `freshness_status` are always
present.

## Status meanings

The only freshness statuses are:

| Status | Meaning |
| --- | --- |
| `current` | A valid freshness basis exists and its age does not exceed the artifact threshold. |
| `stale` | A valid freshness basis exists and its age exceeds the artifact threshold. |
| `unavailable` | The source or artifact explicitly reports failed/unavailable data; age is not asserted. |
| `unknown` | The artifact exists, but neither a valid source timestamp nor retrieval timestamp can establish age. |

`partial`, `failed`, `success`, and `mixed` are not freshness statuses. They
belong to data coverage, module execution, or run health contracts.

## Timestamp rules

1. All timestamps use timezone-aware ISO 8601 UTC with a trailing `Z`.
2. `source_timestamp` is the oldest eligible timestamp required to support the
   artifact. Using the oldest supporting fact prevents one newer record from
   hiding stale inputs.
3. Failed/unavailable records are not eligible source timestamps.
4. Scheduled future event time is not a source-freshness timestamp. Calendar
   availability therefore uses retrieval time when no publication time exists.
5. `retrieved_at` is the latest valid retrieval timestamp represented by the
   artifact or its direct inputs.
6. `generated_at` remains the artifact creation time and must not be substituted
   for source time when a real source timestamp exists.
7. Derived artifacts inherit source and retrieval timestamps from their direct
   validated inputs. They do not reset source freshness when regenerated.

## Age calculation

The freshness basis is selected in this order:

```text
source_timestamp
        ↓ unavailable
retrieved_at
        ↓ unavailable
unknown
```

For available data:

```text
age_seconds = max(0, generated_at - freshness_basis)
```

Age is rounded to three decimal places. A freshness basis more than five minutes
after `generated_at` is invalid and produces `unknown`; small clock skew is
clamped to zero.

For an explicitly unavailable source, `age_seconds` is null even if the attempt
has a current retrieval timestamp. A recent failed request is not current data.

## Stale thresholds

Thresholds are defined centrally by artifact type:

| Artifact type | Threshold | Rationale |
| --- | ---: | --- |
| `market_snapshot` | 48 hours | Daily observations, including non-US session timing |
| `macro_snapshot` | 120 hours | Daily macro proxy cadence and market closures |
| `economic_calendar` | 24 hours | Calendar availability must be refreshed daily |
| `news_items` | 30 hours | 24-hour window plus six-hour overlap |
| `events` | 30 hours | Inherits the News ingestion window |
| `observations` | 48 hours | Derived from daily market observations |
| `evidence` | 48 hours | Inherits observation time |
| `evidence_bundle` | 48 hours | Conservative consolidated Evidence age |
| `market_signals` | 48 hours | Describes the same supporting observations |
| `market_regime` | 48 hours | Current-condition classification only |
| `risk_monitor` | 48 hours | Observed conditions and daily source coverage |
| `daily_intelligence` | 48 hours | Latest structured daily intelligence contract |

Unknown artifact types use the shared 48-hour default. Thresholds affect only
the shared metadata contract; pre-existing module eligibility rules remain
unchanged in this phase.

## Unavailable behavior

- Never synthesize a timestamp or reuse a previous run to make unavailable data
  appear current.
- Preserve a real `retrieved_at` for audit when a source attempt failed.
- Set `freshness_status` to `unavailable` and `age_seconds` to null.
- Downstream modules may continue according to their existing soft-dependency
  rules. Coverage/run status, not freshness, records partial operation.
- An available artifact with an empty but successfully retrieved window may be
  `current` based on `retrieved_at`.

## Manifest records

Every artifact and module record in `run_manifest.json` exposes:

- `source_timestamp`
- `retrieved_at`
- `generated_at`
- `age_seconds`
- `freshness_status`

Markdown and HTML presentation modules inherit freshness from their current-run
data dependencies because those formats do not carry JSON metadata themselves.

The manifest top level exposes the same five fields. Its `generated_at` is the
run completion timestamp.

## Manifest aggregation rules

Aggregation uses data freshness only; execution failure remains in `status` and
`failures`.

1. If any participating data module is `unavailable`, aggregate freshness is
   `unavailable`.
2. Otherwise, if any module is `unknown`, aggregate freshness is `unknown`.
3. Otherwise, if any module is `stale`, aggregate freshness is `stale`.
4. Only an entirely current participating set aggregates to `current`.

This conservative ordering prevents a newly generated data-quality artifact or
presentation file from masking missing or unmeasurable source data.

The aggregate `source_timestamp` is the oldest non-null participating source
timestamp, `retrieved_at` is the latest non-null retrieval timestamp, and
`age_seconds` is recalculated at aggregate generation time from the oldest
source timestamp (or latest retrieval timestamp when no source time exists).

## Validation rules

The shared validator rejects:

- missing contract fields;
- unsupported statuses or contract versions;
- non-UTC or malformed timestamps;
- negative/non-finite ages;
- an age that does not match the declared timestamps and basis;
- `unavailable` or `unknown` with a numeric age;
- `current`/`stale` without a valid basis, age, and threshold;
- `current` with age above its threshold;
- `stale` with age at or below its threshold.

Artifact-specific validators continue to validate their existing deterministic
contracts. Freshness enrichment happens after existing logic validation, then
the shared freshness validator validates the serialized artifact.

## Migration behavior

- Existing top-level `generated_at` values remain unchanged.
- Existing nested fields such as `input_freshness`, bundle `freshness`, and
  per-record status remain temporarily for backward compatibility.
- New consumers must prefer the shared top-level fields.
- The Intelligence View prefers the shared `freshness_status`, then falls back
  to legacy coverage fields while older artifacts remain deployable.
- No schema consumer may interpret `freshness_status` as a market opinion or
  prediction.
