# Phase A — Derivatives V2 shadow contracts

Implemented only under `src/shadow/derivatives`; synthetic JSON fixtures live
under `tests/fixtures/shadow/derivatives`. No production imports, CLI registration,
collector, v1 projection, publication or intelligence rule is introduced.

## Contracts

`derivatives_observation_v2` represents one available typed measurement.
`derivatives_evidence_v2` represents a `measurement_report` supported by one or
more revision-pinned observations of exactly that measurement. No free-text
interpretation is accepted. Both use the common record identity, instrument,
asset, source, freshness, evidence quality and replay envelope defined in
[Phase 0.5](evidence-architecture-hardening.md). These names replace the earlier
illustrative derivative payload v1 names; production schemas are unaffected.

`derivatives_fixture_v2` is a shadow-only registry/container, not the future
production module-result implementation. Models round-trip dictionaries;
`validate_artifact` is the mandatory trust boundary, returning errors rather
than admitting malformed records. Unknown fields and versions fail closed.

The container holds run_id, assets, venues, instruments, sources, observations,
evidence, coverage, a fixed cutoff and replay mode. All IDs are namespaced;
record/source/instrument references pin `@version`. Assets and venues are
stable registry IDs. Different venues/contracts remain distinct even with the
same base asset. Evidence references preserve the union of supporting sources.

## Metric payloads

All values are canonical finite decimal strings (no exponents, trailing zeros,
NaN or negative zero). Unknown measurements have no record: a coverage cell
with a normalized missing reason represents them. Optional metadata may be null.

| Metric | Unit / additional fields |
| --- | --- |
| funding_rate | fraction_per_interval; settled/indicated, interval_seconds, settlement_at, positive_long_pays_short |
| open_interest | base_asset/quote_asset/contracts; nonnegative value, single_side/both_sides counting basis |
| liquidation_quantity | base_asset/quote_asset/contracts; long/short, window_start/end, coverage_fraction; incomplete coverage cannot certify zero |
| long_short_ratio | ratio; account_count/notional, all_accounts/top_accounts/positions, period_seconds; finite nonnegative value |
| positioning_change | percent; formula_id=relative_change_v1; exactly two aligned OI observation refs, positive baseline, same instrument/unit/counting basis |

Positioning formula is a validation of a fixture's arithmetic, not an engine
that generates positioning intelligence. No annualization, ranking, sentiment
or price interpretation is supported.

## Registry and asset abstraction

Assets carry asset_class, symbol and identifiers. Instrument definitions carry
venue, type, base/quote/settlement asset refs, underlying asset ref, definition
version and conditional derivative/token metadata. Perpetual/future/option
require contract size/unit and expiry semantics. Tokenized shares require
chain/network/address/issuer identity, with nullable redemption ratio; issuer
documentation refs are mandatory when that ratio is known. Equity, tokenized
share and perpetual on the token have distinct IDs. This is synthetic schema
coverage only, not token ingestion or a claim of legal equivalence.

## Quality and timing

`evidence_quality` contains policy `derivatives-quality-v1`, nullable score and
four components: data_reliability, timeliness, temporal_coverage,
definition_consistency. Score is their minimum; any null implies null score.
Reliability must match the source registry's declared data reliability (minimum
for multiple sources). This is an explicitly supplied quality assessment, not
an independently verified source reputation or market-confidence estimate.
Derived scores cannot exceed any input; unknown input quality propagates.

Times are canonical UTC `Z` timestamps. observed <= retrieved <= generated;
known_at equals the latest first retrieval among direct sources and dependencies.
Archived replay requires all known_at <= cutoff. transformation_only permits
later retrieval but does not establish historical availability. Future indicated
settlement is allowed; future observed time is not. No schedule/news events are
implemented in this measurement-only contract.

Freshness carries source_timestamp, retrieved_at, generated_at, age_seconds,
freshness_status and policy_id. At the fixed cutoff, age is cutoff minus
observed time. OI/ratio/positioning/liquidation threshold is 7200 seconds;
funding threshold is its interval plus 1800 seconds. `current` includes the
boundary; `stale` exceeds it. Unknown observed time gives `unknown`/null age.
Unavailable exists at coverage level, never as a fake observation. Generated
time does not refresh source time. These are shadow fixture policies only.

## Identity, provenance and validation

Record SHA-256 covers sorted-key canonical JSON, excluding content_hash;
reference arrays are treated as sorted sets. Duplicate refs reject. Identity
includes instrument, metric definition, observation time and source IDs; revisions
are explicit. This Phase A validator verifies uniqueness and revision-pinned
resolution, not continuity against an external historical record store.
Source entries include publisher, fixture raw locator, retrieved_at and raw
payload SHA-256. Fixtures embed raw payloads so hashes can actually be checked.
Direct observations must exactly match a measurement in every cited raw
fixture, not merely carry a syntactically valid hash or source ID.

Validation checks closed shapes/types, registry links, hashes, metric semantics,
time/age/status, quality, arithmetic dependencies, acyclic observation lineage,
evidence equality, missing-data coverage and PIT. Audit results are returned as
`evidence_validation_event_v1`, with target hash, cutoff, validator version and
pass/fail, run identity, known_at and policy versions; transformation-only PIT
is explicitly indeterminate. The audit targets the complete shadow artifact;
raw inputs are embedded, so input_artifact_refs is empty. Evaluated_at uses
the injected cutoff, not the wall clock. This phase does not persist an audit
history or implement per-record revision storage. They are not
economic `events.json` and do not enter any consumer.

## Review and usage

Run `python -m pytest tests/test_derivatives_shadow.py`, then the complete suite.
Fixtures are synthetic, never fetched, published or copied to `src/output`.
No write API is provided; validation is read-only. Tests validate all five
families, optional/missing data, token identity, stale/unknown data, provenance,
PIT, hashes, bad shapes and production isolation. Existing v1 regression tests
remain authoritative; no v1-to-v2 projection is claimed by Phase A.
