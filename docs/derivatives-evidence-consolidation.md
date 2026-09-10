# Phase D-3 — Derivatives evidence consolidation

Shadow-only `derivatives_evidence_bundle_v1`. Inputs are complete funding/OI
shadow wrappers, not detached observations: their native capture/normalization
validators must pass before consolidation. No provider requests or changes to
production evidence_bundle.json, intelligence or presentation.

## Contract and identity

Envelope: schema_contract, evaluation_cutoff, status, coverage, input_artifacts,
evidence and validation_status. Each fact contains a deterministic evidence_id,
instrument_id, venue_id, base/quote/settlement asset IDs, metric/value/unit,
source_timestamp, time_window, observation_refs, source_records, freshness,
evidence_quality and conflict flag. Only measurement_report claims are emitted.

Grouping uses logical instrument ID plus venue/base/quote/settlement/underlying
identity and UTC calendar-day observation window. Funding and OI can link in
one group only when those fields AND that day match; distinct instrument
revisions remain explicit. Groups disclose observation time range and skew,
never assert simultaneity or a causal relationship. Across days remain separate.

Exact fact equivalence additionally requires metric, timestamp, value, unit and
metric definition (funding interval/sign/kind or OI counting/unit). Repeated
artifacts deduplicate by content hash. Refetches of an identical fact collapse
into one evidence fact while retaining every observation revision/receipt link.
Same identity/time/metric with conflicting values remains separate, flagged;
neither silently wins. Incompatible definitions never collapse.

## Provenance and quality

input_artifacts pin the complete supplied wrapper SHA-256, provider, run ID and
schema. source_records retain original observations (including all timestamps,
hashes, quality, pinned instrument refs), instrument revisions, normalization
receipts and capture descriptors (hash, endpoint, captured_at). No raw response
bytes or normalized bytes are duplicated into this bundle. Exact original bytes
remain resolvable by the input artifact hash in the caller's private archive.
The validator requires those wrappers again and rebuilds the expected bundle;
hash-shaped strings alone are insufficient proof.

Evaluation cutoff must be explicit and >= every input evaluation/capture time.
Recompute freshness at that cutoff using existing funding interval+1800s and
OI 7200s thresholds without rewriting source or retrieval timestamps. Quality
is the minimum input Evidence Quality score and current timeliness; any unknown
score propagates null. Stale facts stay auditable with score zero, not refreshed
by assembly. Quality is not truth probability or directional confidence.

Coverage has four fixed cells (BTCUSDT/ETHUSDT × funding/OI), availability,
fact count and current fact count. status available/partial/unavailable concerns
presence only; freshness reports current/stale/unknown/unavailable separately.
Availability does not mean sufficient fresh data. No unavailable input produces
fabricated evidence. Empty lists are a valid unavailable bundle.

## Execution and validation

`compose(funding_artifacts, oi_artifacts, evaluation_cutoff)` is deterministic,
read-only and does not mutate source artifacts. Invalid inputs reject the request,
not silently turn into missing evidence; valid unavailable wrappers are accepted.
`validate_bundle` replays input validators and composition, including provenance,
quality, deduplication and hashes. No natural-language generation occurs.

CLI requires explicit --as-of and unique --run-id; repeat --funding/--oi for
multiple artifacts. Output is only
outputs/shadow/derivatives/<run_id>/derivatives_evidence_bundle.json. Private
exclusive directory and atomic rename; no production CLI/workflow registration.
Source paths are not published. The D-0 public filter continues to reject this
artifact type. No production consumer is connected.
