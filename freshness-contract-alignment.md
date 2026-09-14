# Phase 11.1 — Freshness Contract Alignment

## Decision map and canonical meaning

| Layer | Decision before | Alignment |
| --- | --- | --- |
| Source adapters | fetch success is not source currency | preserve status, source timestamps and existing 48h market / 120h macro thresholds |
| Observations / evidence | artifact generation can mask old observations in domain consumers | assess observation as_of at the existing 48h evidence threshold |
| Evidence bundles | generated_at / latest retrieved_at drives fresh | old observation IDs explicitly enter stale_record_ids; retrieval never refreshes a market fact |
| Signals | bundle stale IDs + 36h alignment | preserve signal rules and 36h threshold; corrected freshness feeds existing exclusion |
| Regime | dimensions / weights / coverage | unchanged classifier; no forced state or threshold change |
| Daily / Top | generated coverage vs oldest source envelope | preserve conservative envelope; add reference-scoped freshness_items metadata |
| Public artifacts | envelope forwarded | existing artifact paths; no new source or private data publication |
| Frontend | Top stale envelope hides every item | validated current items remain visible; stale items labeled historical; missing/unknown basis never upgraded |

Canonical fields: source_timestamp (oldest actual required observation), retrieved_at
(latest receipt among required sources), generated_at (assessment time), age_seconds
(generated minus source, seconds), freshness_status (current/stale/unavailable/unknown).
All timestamps are timezone-aware UTC. Retrieval does not substitute for a missing
market observation. Future timestamps outside the existing five-minute skew fail
closed. Existing thresholds are not increased. Derived evidence uses 48h; a 120h
macro adapter allowance does not authorize a 120h cross-market conclusion.

## Aggregation and visibility

An artifact's existing conservative oldest-source envelope remains unchanged and
retains stale warnings. It is a coverage warning, not a universal item visibility
decision. `freshness_items` is a versioned metadata extension, outside the frozen
domain/ranking payload. It maps stable item IDs to independently validated canonical
freshness fields and explicit observation/event/source references. Missing referenced
records yield unknown/unavailable, never current. Each item uses only its own
references; unrelated source-catalog timestamps cannot age an otherwise current item.

The frontend preserves order, scores and references. It renders validated current
items and labeled stale historical items without silently relabeling them current.
Unknown/unavailable records remain unavailable. Legacy artifacts without the new
extension keep the existing conservative behavior. Browser time can downgrade an
item after expiry, never upgrade a recorded stale item. Whole-section unavailability
still applies when no usable items exist. No ranking, scoring, dedup, regime, prompt,
source API or derivatives gate changes are authorized by this phase.

Replay uses saved production inputs at the original production timestamp, not a
new fetch or today's time. Any fewer upstream candidates after correcting stale
observation exclusion are a freshness consequence, not a ranking change.

## Implementation and conservative compatibility

`src/data/item_freshness.py` produces `freshness_items.version=reference_scoped_v1`.
Metadata is recomputed against dependency catalogs by signal/regime/daily/Top
validators; extra fields (including raw_response) are rejected by the closed item
metadata validator. Existing domain schemas, ranking weights, story keys and score
calculation remain intact. The new metadata is stripped before domain equality
validation, then checked independently. Legacy artifacts without item metadata keep
their previous conservative whole-artifact visibility rule.

Scheduled calendar evidence may use source receipt time when no publication time
exists: source_timestamp remains null, freshness_basis is retrieved_at, and the
existing calendar 24h limit is retained. A future scheduled event time is never
treated as an already observed source timestamp. This exception cannot be used
for market observations. Missing records or source failures are unavailable. A
provider stale flag with a contradictory recent timestamp is unavailable rather
than silently current. Future/invalid dependency timestamps fail closed.

The only selector modification is its **freshness prerequisite**: when validated
scoped metadata exists, assess the candidate's references instead of inheriting
unrelated record staleness. Artifact generation-age checks still apply. No score,
sort order, theme diversity, story grouping or regime dimension rule was changed.
Correcting freshness can change eligibility/counts; it does not guarantee three
stories. Stale historical display never grants current eligibility.

## Production replay (2026-09-14 run 34821085882)

Input commit: `1bd76780faac1861bc82fc65bd06ec262eb9427e`.
Saved production market/macro/calendar/news/observation/evidence inputs were reused
offline. Consolidation through brief renderer was rebuilt at each original module
timestamp; dependent validators and deterministic brief validation passed. No
source request, production output overwrite, workflow run or deployment occurred.

| Measure | Before | After |
| --- | --- | --- |
| Top envelope | stale | stale (unchanged warning) |
| Daily intelligence | partial | partial |
| Visible current Top | 0 | 2 |
| Gold / DXY inverse movement | selected score 68, hidden by envelope | current and visible, score 68 |
| BTC / ETH co-movement | selected score 61, hidden by envelope | current and visible, score 61 |
| Regime coverage diagnostic | selected with stale dependencies | no current eligibility; not relabeled current |
| SPY / QQQ co-movement | observed despite Friday bars | stale_data |
| Equity divergence evaluation | not_observed despite Friday bars | stale_data |
| Regime | unavailable | unavailable (classifier untouched) |
| Three time-gap failures | insufficient_data | unchanged |

Gold/DXY source time: 2026-09-14T04:00:00Z, age14901.712s; BTC/ETH:
2026-09-14T00:00:00Z, age29301.712s. Both use unchanged172800s TTL.
At replay time +3 days the browser labels both stale, not current.
See `freshness-alignment-comparison.json` for machine-readable comparison.

## Validation / boundaries

- Tests cover mixed/all current/all stale, missing source and reference, public
  metadata allowlist, forged ages, reference/receipt preservation, provider failure,
  stale observation after new retrieval, legacy fallback, browser aging and calendar.
- Complete regression suite: 493 passed, 1 skipped (existing GnuPG requirement).
- Beta readiness validator remains conditional; this is not a new readiness approval.
- The existing deferred `src/intelligence/pipeline.py` edit is not part of this work.
- No AI prompt, source API, regime decision logic, trading logic or derivatives gate
  edits. New JS is packaged at the existing approved static asset path. No new
  public endpoint or secret-bearing artifact is introduced.
- This is a frozen-input replay, not evidence that future source availability or
  the six-current-core-assets usefulness gate will pass. Calendar coverage and
  session-aware timestamp policy remain separate follow-ups.
- Local Chrome replay at 1440/768/390/375px: both current stories rendered,
  whole-report stale warning remained visible, no horizontal overflow or JS errors.
  Six replay JSON artifacts passed freshness validation and sensitive-pattern scans.
  Original Chinese copy is preserved, including the existing broad `Observed:`
  translation; this phase does not expand into copy editing.
