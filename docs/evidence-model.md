# Phase 6.2-D Evidence Consolidation Contract

> Status: implementation contract for the Evidence Consolidation Layer. This
> phase combines existing factual records only. It does not perform ranking,
> sentiment, market-impact analysis, prediction, signal generation, or LLM work.

## 1. Purpose and boundary

The consolidator creates one read-only, traceable boundary between ingestion
and future Intelligence processing:

```text
observations.json ───────────────┐
                                │
evidence.json ──────────────────┤
                                ├─ Evidence Consolidator ─ evidence_bundle.json
economic_calendar.json ─────────┤
                                │
events.json ────────────────────┘
```

`observations.json` already contains both market and macro observations. The
consolidator keeps them distinguishable through `observation_type` and reports
separate market and macro coverage. Economic-calendar and normalized-news
events remain distinct event classes. Existing Evidence records are preserved
as source-grounded factual claims; the consolidator does not rewrite them.

The layer answers only:

- which factual records are available;
- which records refer to the same exact fact;
- where every record came from;
- when each record was observed, published, scheduled, or retrieved;
- whether records are stale, incomplete, unavailable, or verified.

It must never answer what an event means for price, whether an asset is
bullish/bearish, what caused a move, or what may happen next.

## 2. Artifact envelope

`evidence_bundle.json` uses the following envelope:

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | string | Fixed as `1.0` for Phase 6.2-D |
| `artifact_type` | string | Fixed as `evidence_bundle` |
| `run_id` | string | Deterministic consolidation run identifier |
| `report_date` | string | Report date in `Asia/Taipei` |
| `generated_at` | UTC timestamp | Consolidation time |
| `status` | enum | `available`, `partial`, or `unavailable` |
| `warnings` | array[string] | Missing, stale, rejected, or partial-input disclosures |
| `coverage` | array[CoverageRecord] | Health of all five required input classes |
| `bundle_count` | integer | Number of valid consolidated bundles |
| `rejection_count` | integer | Number of rejected broken input records |
| `rejections` | array[RejectionRecord] | Audit trail; never converted into facts |
| `bundles` | array[ConsolidatedEvidenceBundle] | Valid factual bundles |

Artifact status rules:

- `available`: every required input class is available and no accepted record
  was rejected or marked stale;
- `partial`: at least one valid bundle exists, but an input is partial,
  unavailable, stale, or contains rejected records;
- `unavailable`: no valid factual bundle can be produced.

A valid source with zero records is still `available`; a failed or missing
source is `unavailable`. No placeholder observation, event, or Evidence record
may be generated for unavailable input.

## 3. Coverage record

There is exactly one coverage record for each input class:

- `market_observations`
- `macro_observations`
- `economic_calendar`
- `news_events`
- `existing_evidence`

```json
{
  "input_type": "macro_observations",
  "artifact": "observations.json",
  "run_id": "run_example",
  "generated_at": "2026-08-26T00:00:00Z",
  "status": "partial",
  "record_count": 3,
  "stale_record_count": 1,
  "warnings": ["One macro observation is stale."]
}
```

Coverage status describes access and record health, not the truth, importance,
or market impact of the underlying data.

## 4. Consolidated evidence bundle

Every bundle contains all retained input records needed to reconstruct it:

| Field | Type | Required rule |
|---|---|---|
| `id` | string | Stable `ebd_` ID from the exact fact key |
| `type` | enum | `evidence_fact`, `observation`, `calendar_event`, or `news_event` |
| `related_assets` | array[string] | Union of explicit input mappings only |
| `source_records` | array[SourceReference] | Complete, de-duplicated provenance records |
| `observations` | array[Observation] | Complete original observation objects |
| `events` | array[Event] | Complete original calendar/news event objects |
| `evidence_records` | array[Evidence] | Complete original Evidence objects |
| `timestamps` | object | Preserved observed/scheduled/published/retrieved times |
| `verification_level` | enum | `official`, `corroborated`, `observed`, `single_source`, or `unverified` |
| `data_quality` | object | Record health only; never market quality |
| `freshness` | object | `fresh`, `stale`, `mixed`, or `unknown` |
| `provenance` | object | All input artifacts, run IDs and record IDs |

`evidence_records` is additive to the minimum requested contract. It prevents
loss of the existing factual statement, relation, limitations, confidence, and
contradiction links. The consolidator never creates or paraphrases a statement.

### 4.1 Timestamps

```json
{
  "observed_at": [],
  "occurred_at": [],
  "scheduled_at": [],
  "published_at": [],
  "retrieved_at": [],
  "consolidated_at": "2026-08-26T00:00:00Z"
}
```

All arrays are unique, sorted UTC timestamps copied from input records.
Publication time must not be converted into event occurrence time.

### 4.2 Data quality and freshness

```json
{
  "status": "partial",
  "issues": ["stale_observation"],
  "source_count": 1,
  "observation_count": 2,
  "event_count": 0,
  "evidence_count": 1
}
```

```json
{
  "status": "stale",
  "as_of": "2026-08-19T04:00:00Z",
  "stale_record_ids": ["obs_example"]
}
```

Native input health is authoritative. An observation marked `stale` remains
stale. A news event with lifecycle `expired` or `retracted` is stale for current
processing but remains present for audit. Unknown freshness is disclosed; it
must not be silently treated as fresh.

### 4.3 Provenance

```json
{
  "input_artifacts": ["observations.json", "evidence.json"],
  "input_run_ids": ["run_example"],
  "source_ids": ["src_example"],
  "observation_ids": ["obs_example"],
  "event_ids": [],
  "evidence_ids": ["evd_example"],
  "consolidation_rule_id": "exact_fact_consolidation_v1",
  "deduplication_key": "sha256:..."
}
```

Every ID in provenance must resolve to an embedded record or a matching
`source_record`. No dangling references are permitted.

## 5. Relationship rules

1. An existing Evidence record produces an `evidence_fact` bundle containing
   every referenced observation, event, and source.
2. Valid observations not referenced by existing Evidence produce standalone
   `observation` bundles. This prevents price, feature, and macro records from
   being discarded merely because no current claim uses them.
3. Valid calendar or news events not referenced by existing Evidence produce
   standalone `calendar_event` or `news_event` bundles.
4. Two existing Evidence records merge only when their deterministic exact-fact
   key matches. Their complete Evidence records and all provenance links are
   retained. No semantic or LLM deduplication is allowed.
5. Event proximity to an observation never creates a relationship. Causal or
   associative linkage remains a later, separately validated phase.

## 6. Verification rules

- `official`: an event is supported by a Tier 1 official source;
- `corroborated`: the exact fact retains two or more independent valid
  provider/publisher origins;
- `observed`: a factual Evidence record is supported by validated observations;
- `single_source`: one valid non-official source supports the record;
- `unverified`: retained audit material lacks sufficient verification and must
  not be treated as an intelligence conclusion.

Verification level is not truth probability and is not directional analysis.

## 7. Missing and invalid data

- Missing input file: mark its coverage `unavailable`; continue other inputs.
- Failed input artifact: preserve its warning in coverage; create no bundle.
- Observation with an unknown `source_id`: reject that observation and every
  Evidence record depending on it; keep an audit rejection.
- Evidence with unknown observation/event/source IDs: reject the Evidence
  record; do not invent the missing record.
- Invalid event source metadata: reject that event; do not create fake source
  metadata except the deterministic SourceReference conversion defined for a
  valid calendar event.
- Partial input: keep valid records, mark coverage and artifact `partial`.

## 8. Validation guardrails

Validation must reject:

- duplicate bundle, observation, event, Evidence, or source IDs within an
  incompatible payload;
- dangling provenance IDs;
- a bundle without any observation, event, or existing Evidence record;
- source records without timestamps and a stable content hash;
- unsupported or timezone-naive timestamps;
- causal language such as `caused`, `because of`, `led to`, `由於`, or `導致`
  in existing factual statements;
- fields for sentiment, bullish/bearish classification, prediction, ranking,
  price impact, recommendation, LLM output, or trading signals;
- an `available` data-quality state when linked records are stale or missing.

## 9. Acceptance criteria

- market and macro records consolidate in one artifact without losing their
  original type or provenance;
- exact duplicate Evidence records collapse into one bundle while retaining all
  Evidence and source links;
- missing sources produce rejections and partial/unavailable coverage, never
  fabricated evidence;
- stale observations remain visibly stale at bundle and artifact level;
- calendar and news source IDs, event IDs, and timestamps remain traceable;
- every valid unreferenced observation/event is retained in a standalone bundle;
- existing tests remain green and no downstream module is changed.
