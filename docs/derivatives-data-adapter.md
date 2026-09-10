# Phase B — Derivatives Data Adapter Architecture

Review draft, 2026-09-09. Documentation only: no ingestion, network runner,
production integration or new dependencies are implemented or authorized here.
Builds on [Phase A contracts](derivatives-schema.md) and
[architecture hardening](evidence-architecture-hardening.md).

## 1. Scope and source tiers

Proposed first collector: one approved venue, BTC/ETH USDT linear perpetuals,
settled funding and native open interest. This tests reliable evidence ingestion,
not a Funding Bot, sentiment service or market-wide positioning model.

| Tier | Qualification | Policy |
| --- | --- | --- |
| T1 — direct publisher | Official venue endpoint with documented field semantics | Preferred for that venue's measurements; not automatically complete or correct |
| T2 — traceable distributor | Documented upstream venue, timestamps, units, transformations and usage rights | Future separately approved adapter; cannot replace T1 silently |
| T3 — opaque/unsupported | Unverifiable aggregation, missing definitions or unclear provenance | Audit/quarantine only; ineligible for evidence |

Tier is source origin, not a probability or directional confidence. Preserve
Evidence Quality components, including Data Reliability, separately. Initial
reliability assignments remain versioned review decisions, not measured accuracy.
Null reliability stays unknown. Low liquidity does not falsify a settlement,
but limits representativeness; liquidity remains unknown unless measured with
its own scope, time and provenance. Funding is not market sentiment.

Bybit official public endpoints are the proposed first candidate, not a verified
deployment dependency. Runner access, field semantics and storage/redistribution
terms require approval before collection. Do not bypass access restrictions.
Another venue is another population: preserve separate records, never switch
venues while retaining the same source/instrument ID. No fallback provider is
approved in this phase; unavailable is preferable to undocumented substitution.

## 2. Provider-neutral boundary

Use a static descriptor registry, not dynamic plugins or a second scheduler.
Exchange-specific parsing belongs solely in the provider adapter/normalizer.

| Contract | Proposed fields / responsibility |
| --- | --- |
| ProviderDescriptor | provider_id/version, venue_id, endpoint allowlist, supported instruments/metrics, native units, pagination, timestamp precision, policy versions |
| CollectionRequest | run_id, requested cutoff/window, canonical instrument refs, metric set, budgets, config hash |
| FetchResult | immutable response receipts, per-cell availability, pagination completeness, safe failures; no intelligence |
| NormalizationResult | candidate observations, source/instrument revisions, transformation receipts, rejections and coverage |
| ValidationResult | accepted candidates and audit; unresolved references or semantics cannot enter evidence |

Conceptual flow: `fetch(request, transport, clock) -> FetchResult`, then
`normalize(fetch_result, registry) -> NormalizationResult`. The host enforces
budgets, persistence, reference resolution and final validation. An injected
transport/clock supports offline fixtures. Normalization must not fetch again.

Asset IDs identify economic assets; instrument IDs additionally identify venue,
contract type, settlement and definition revision. Do not index derivatives by
spot aliases. Future tokenized stocks retain chain/issuer and underlying
relationships; they are not included in this collector's coverage.

### Phase A compatibility gate

The existing `derivatives_fixture_v2` validator requires `synthetic=true` and
matches normalized fixture measurements embedded in raw fixtures. Real exchange
responses have different shapes. **Never mark live data synthetic or rewrite raw
responses to satisfy that validator.** Before implementation, approve a distinct
non-synthetic shadow collection envelope and versioned raw-to-normalized receipt
validator. Reuse compatible `derivatives_observation_v2` payloads, but do not
claim the current fixture container is a production ingestion interface.

## 3. Metric coverage matrix

| Capability | Candidate source | First collector | Meaning / constraints |
| --- | --- | --- | --- |
| Instrument metadata | Official instruments-info | Required | Symbol, contract/settlement, interval and definition revision |
| Settled funding | funding/history REST | Enabled after approval | Preserve interval, rate sign, settlement timestamp; not next indicative rate |
| OI | open-interest REST | Enabled after approval | Native quantity, unit and counting basis; no inferred USD value |
| Long/short ratio | account-ratio REST | Deferred | Account proportions, not capital long versus short; any derived ratio needs formula and nonzero denominator |
| Liquidation | allLiquidation WebSocket | Not collected | Requires separate continuous-coverage design; not recoverable from a short daily connection |
| Positioning change | Derived from validated OI | Deferred to evidence-generation phase | Two matching definitions/windows and explicit formula lineage; not a provider fact |
| Liquidity context | No source approved | Unknown | No assumed depth, turnover or market-share denominator |

Funding intervals are instrument-specific. OI units and single/both-side counting
must be preserved rather than guessed. Account ratios cannot stand for notional
positioning. See official [funding](https://bybit-exchange.github.io/docs/v5/market/history-fund-rate),
[OI](https://bybit-exchange.github.io/docs/v5/market/open-interest),
[account ratio](https://bybit-exchange.github.io/docs/v5/market/long-short-ratio)
and [instrument metadata](https://bybit-exchange.github.io/docs/v5/market/instrument) contracts.

The [liquidation stream](https://bybit-exchange.github.io/docs/v5/websocket/public/all-liquidation)
supplies bankruptcy price, which is not realized trading loss. Missing stream
history must never become zero liquidation or an estimated complete-day total.

Coverage is keyed by instrument and metric with a frozen configuration hash:
requested acquisition coverage, five-family target coverage and market coverage
are separate. For two instruments with funding/OI only, target coverage is 4/10
if all four are available; acquisition can be complete while target coverage is
partial. Market coverage remains null without a verified denominator. Report
numerators, denominators and fresh-eligible counts, not just a blended score.

## 4. Freshness and point-in-time requirements

Retain source_timestamp, retrieved_at, generated_at, age_seconds,
freshness_status and policy version. Native timestamp precision must survive
in the raw receipt; do not silently truncate identity-bearing milliseconds.
Phase A only accepts whole-second UTC times, so finer normalized precision needs
a separately reviewed contract extension before such records are admitted.

Preserve current Phase A thresholds as shadow proposals, not production tuning:

- Settled funding: current through interval_seconds + 1800 seconds after source
  time. No universal eight-hour assumption; metadata interval changes split history.
- OI: latest completed one-hour sample; current through 7200 seconds of age.
- Deferred ratio/positioning/liquidation: Phase A's 7200-second rule alone does
  not prove interval completeness or alignment. Those capabilities need their
  additional window/continuity checks before collection is enabled.
- Unknown source time: unknown freshness. Missing source: unavailable coverage.
  Stale data stays auditable, not silently refreshed by report generation.

Use two times: requested observation cutoff at run start, and evaluation cutoff
after receipts are captured. Query observations no later than the requested
cutoff; assess age and knowledge eligibility at the explicit evaluation cutoff.
This avoids claiming newly fetched data was known before retrieval. For a supplied
historical replay cutoff, only archived receipts known by that cutoff qualify;
fresh backfills are transformation-only. Never backdate retrieved_at.

known_at is the latest first retrieval of pinned dependencies, including the
instrument definition used for interpretation. Phase A's fixture source-only
knowledge check is insufficient for live metadata: extending provenance and PIT
validation for registry revisions is a required pre-ingestion gate.

## 5. Rate limits and bounded execution

Official Bybit documentation currently specifies a default IP ceiling of 600
HTTP requests per five seconds and a minimum ten-minute stop after the explicit
“access too frequent” 403. It also documents application rate-limit code 10006
and response budget headers. These are provider limits, not our target throughput;
UID/trading endpoint tables must not be assumed to describe every public endpoint.
[Official rate-limit policy](https://bybit-exchange.github.io/docs/v5/rate-limit).

Proposed local safety budget (configuration, not claims about API capacity):

| Limit | Initial value |
| --- | --- |
| Concurrency | One in-flight request per provider |
| Pace | At most one request per second; burst size one |
| Request timeout | 10 seconds total |
| Overall collection deadline | 120 seconds |
| Total HTTP attempts | 20 including metadata, pagination and retries |
| Pagination | Maximum three pages per instrument/metric query |
| Response body | Maximum 2 MiB per response after decompression |
| Retry | At most one per request, only transient failures |

Use the stricter local/provider budget. Respect valid Retry-After/reset headers;
if waiting exceeds the remaining deadline, stop that source and record the
retry-after time rather than sleeping past budget. For transient transport/5xx,
use a bounded backoff; malformed responses, unit/schema errors and access denials
are not retryable. A rate-limit response opens a provider-level circuit; allow
at most the single bounded retry after reset, never retry per symbol in a loop.
Explicit IP-ban 403 stops the provider for this run with no retry. Generic 403
is access_denied, not automatically classified as a rate ban. No proxy rotation.
Shared runner IP traffic may consume capacity outside this process; local pacing
does not guarantee access. No WebSocket connections in the first collector.

## 6. Failure isolation

Normalize errors as code, provider_id, instrument_ref, metric, attempt count,
retryable, retry_after_at and safe reason; exclude raw provider error bodies.

| Failure | Isolation / output |
| --- | --- |
| Timeout, network error, 5xx | Affected request/cell; bounded retry, then unavailable |
| Rate limit / IP ban | Provider circuit; retain already validated cells, stop further calls |
| Access denied | Provider unavailable, no workaround |
| Bad metadata / unknown unit | Affected instrument or dependent metric only |
| Bad measurement | Reject record, preserve audit and other valid records |
| Incomplete pages / budget exhausted | Mark window incomplete; no complete aggregate claim |
| Empty successful response | Acquisition succeeded; required current measurement still unavailable, never zero |
| Conflicting revisions | Preserve both receipts; unresolved conflict ineligible for a single authoritative current fact |

Store valid observations from partial responses with explicit incomplete coverage;
do not aggregate them as complete. Provider/source health is distinct from
evidence availability. No accepted evidence means unavailable; accepted evidence
with target gaps means partial. Independent market/macro/calendar/news production
runs are not dependencies of this shadow job and must not be changed or failed.
No retry or stale-cache recovery may fabricate a current-run success.

## 7. Provenance and integrity

Each receipt preserves provider/venue/publisher, allowlisted endpoint and safe
query parameters, request/response times, status, pagination cursor lineage,
content type, raw byte SHA-256 and immutable relative artifact path. Retain only
approved non-secret headers. Public market endpoints require no trading account;
never collect credentials, account positions or private balances.

Normalization receipts must pin raw locator(s), native field/value/unit,
instrument/source definition revision, transformation ID/version and output
record hash. Keep raw and normalized hashes separate: normalization is not a
replacement for raw evidence. Native decimals are parsed without float rounding.
No source priority can erase conflicting evidence or independent provenance.

Stable IDs separate observation identity from revision and receipt identity.
Deduplicate only proven identical source records; a correction appends a revision.
Exact duplicates across fetches retain all capture receipts. Persistence must
retain original first-seen times for PIT; a latest-only overwrite is insufficient.
Cross-run retention policy and storage permission must be approved before live
collection. Source terms may constrain raw retention and redistribution.

## 8. Shadow output flow

```text
Explicit shadow invocation (not production scheduler)
  -> provider descriptor + frozen request/budget
  -> immutable raw receipts + collection health
  -> normalization receipts + candidate observations
  -> separate non-synthetic shadow validator
  -> accepted observations / rejections / coverage / validation audit
  -> internal manifest with versions and hashes
  -> STOP; evidence generation/integration is separately approved
```

Proposed run-isolated namespace:

```text
outputs/shadow/derivatives/<run_id>/
  raw/                         # private source receipts, not version-controlled
  collection_manifest.json
  normalization_receipts.json
  observations.json
  coverage.json
  validation_events.json
  rejections.json
```

Names are proposals; this phase creates none of these artifacts. Sanitize run IDs,
resolve paths within the shadow root, reject traversal/symlink escape and write
atomically from per-run temporary paths. No fallback to a previous run's files.
The standalone shadow manifest is not production run_manifest.json. Neither
GitHub Pages nor production artifact uploads may include this directory; verify
allowlists before any future job is added. Do not write src/output or masquerade
as canonical evidence_bundle.json. No production consumer reads shadow output.

## 9. Architecture review and next gate

Design recommendation: proceed to a reviewed adapter contract bridge before
minimal collection. Do not directly reuse the synthetic fixture envelope for
live ingestion. Required decisions are non-synthetic envelope/receipt validation,
timestamp precision, metadata PIT, source terms/access and retention policy.

Future implementation acceptance tests: mocked endpoint success, provider error
inside HTTP 200, rate-limit circuit, bounded retries/page budgets, metadata failure
isolation, partial/empty windows, source conflicts, exact provenance, millisecond
preservation, historical backfill rejection, safe paths and no production imports
or publication changes. Existing v1 tests must remain green.

No live API call, ingestion implementation, source availability verification or
production readiness is claimed by this architecture document.
