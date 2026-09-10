# Phase C — Production Observation Foundation

Contract implementation only. No provider, ingestion, scheduled job or production
consumer is connected. `src/shadow/derivatives/production_*` defines non-synthetic
observations staged in a shadow output contract, not production readiness.

## Envelope and separation

`derivatives_production_observation_v1` is a separate closed schema from Phase A
`derivatives_observation_v2` and `derivatives_fixture_v2`. No synthetic wrapper
conversion or fallback is allowed. `synthetic` must be false in both the new
observation and its `derivatives_shadow_output_v1` envelope. Offline unit tests
construct artificial examples of this shape; passing validation does NOT certify
that a real exchange supplied them. Authentic acquisition is a future adapter duty.

The envelope has run_id, requested_cutoff, evaluation_cutoff, replay_mode,
source registry, immutable instrument revisions, observations and coverage.
Only direct funding and OI measurements are accepted initially; the other Phase A
families remain unavailable. No evidence claims or derived intelligence are built.
Each observation pins an instrument revision and raw receipt, has canonical
decimal value/unit, native epoch timestamp/precision, source timestamp, retrieval,
generation, known_at, freshness and Evidence Quality. Identity and content SHA-256
are distinct. Explicit versions preserve corrections; supplied previous output
is checked for revision mutation, including removed-then-reintroduced identities
only to the extent that the caller supplies a complete historical registry.

## Raw receipts and validation boundary

Caller supplies raw UTF-8 JSON bytes separately, keyed by safe shadow-relative
receipt paths. Bytes are hashed before parsing; duplicate JSON keys/nonfinite
numbers are rejected. A receipt records source ID, captured_at, SHA-256 and path.
Sources have publisher, venue and nullable Data Reliability. No networking or
filesystem writer exists. Paths reject traversal, absolute paths and backslashes;
a future writer must additionally guard symlinks and atomic publication.

Instrument revisions pin a metadata receipt and JSON Pointer to an exact
definition object (venue, native symbol, asset IDs, derivative type, unit,
counting basis, funding interval, effective range). Observation receipts use
JSON Pointers for metric/native symbol/value/epoch time. They must belong to the same
source as the instrument definition and resolve exactly to the declared values.
This is a generic receipt contract, not an exchange parser. A future adapter must
provide an authentic source definition object or separately reviewed verifiable
normalization receipt bridge. It must not alter raw exchange bytes to match it.

## Asset and revision handling

Asset IDs are namespaced and distinct from instrument IDs. Venue and native symbol
are part of the pinned definition, never substituted with a spot ticker.
base/quote/settlement/underlying asset IDs permit crypto, equity or tokenized asset
registries in future; this foundation does not resolve token legal equivalence.
Supported measured instruments are perpetual/future. Units and funding interval
come from the applicable definition, not an inference from symbol names.
Funding is explicitly settled funding with positive-long-pays-short semantics;
its source timestamp is settlement time. Indicated funding is not admitted.

Definitions use `[effective_from, effective_to)`; null end means open-ended.
The observation time must fall in the pinned revision's range. Revision hashes
cover all content except content_hash. Different revisions may overlap because
corrections can restate history; no validator silently picks the latest. Callers
must pin the exact revision. Conflicting same-ID/same-version contents reject.
Historical validation accepts optional prior output to detect mutations but is
not itself a durable append-only store or a complete revision selector.

## Precision and freshness

All normalized timestamps use UTC with exactly three fractional digits and `Z`.
Native source timestamp carries an integer and unit `s` or `ms`. Conversion is
exact using integer arithmetic; sub-millisecond formats reject, never truncate.
Native `s` timestamps pad `.000` but retain the original precision declaration.
Freshness age_seconds is a decimal string computed from integer milliseconds.
Funding uses interval + 1800 seconds; OI uses 7200 seconds, inclusive boundary.
These named foundation policies preserve Phase A proposals, not live calibration.

Source time <= requested_cutoff <= evaluation_cutoff. Observation retrieval and
metadata capture must precede generation; generation <= evaluation_cutoff for
archived replay. Freshness is evaluated at evaluation_cutoff, never generated_at.
Unavailable measurements exist only in coverage; there is no fabricated record.

## PIT and quality

known_at equals max(observation receipt captured_at, metadata receipt captured_at).
Archived replay requires both <= evaluation_cutoff. New retrieval after run-start
is valid only against the later explicit evaluation cutoff. Transformation-only
backfills may be retrieved/generated later, but historical_availability remains
indeterminate. Later metadata is never made historical by its effective_from.

Evidence Quality is min(Data Reliability, timeliness, temporal coverage,
definition consistency). Direct point measurements have temporal coverage 1;
this is NOT full query-window coverage or market share. Unknown source reliability
propagates null. No confidence, sentiment or directional labels are supported.
Validation proves internal consistency and receipt linkage, not source truth.

## Shadow output and readiness

Namespace is `outputs/shadow/derivatives/<run_id>/`. Receipt paths must be within
that exact run namespace. No files are written by this implementation. The output
contract records available/unavailable instrument/metric coverage; all five metric
families must be represented for every declared instrument. A validated empty
run may carry unavailable coverage; it is not successful collection of facts.
Aggregate availability is returned separately from contract validity. Neither
v1 projection, production run_manifest nor publication allowlists are changed.

Tests cover precision, byte hashes/pointers, instrument effective revisions,
metadata lookahead, immutable revisions, unavailable output, separation and
production isolation. Provider integration still requires authentic receipt mapping,
retention/first-seen persistence, access/terms review, ingestion safety and live
policy calibration. Stop for review before those steps.

## Local validation

Run `.venv/bin/python -m pytest tests/test_derivatives_production_foundation.py`
for the foundation suite, or `.venv/bin/python -m pytest` for all regressions.
Tests build artificial receipts in memory; there are no live artifacts to publish.
No existing Phase A schema/validator is changed, and its synthetic fixtures remain
synthetic. The new schema uses small shared primitive checks from the shadow
validator, not its fixture envelope or raw-measurement matching logic.
