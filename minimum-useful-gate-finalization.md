# Phase 11.5 — Minimum Useful Intelligence Gate Finalization

## Decision

Adopt **hybrid breadth-and-depth policy D** as the proposed Gate A contract.
It uses only facts the current system can prove and does not count stale,
unavailable, unknown or unverified-close records. This phase is audit-only:
the contract is not wired to orchestration, manifest, public metadata or UI.

The fixed Phase 11.4 snapshot is **minimum useful, but overall degraded**.
That is not equivalent to ready, complete, fresh, or healthy across every market.
Its five current core assets span crypto, FX and commodities; two validated Top
stories and four current macro indicators provide substantive intelligence.
Equities and Regime remain explicitly unavailable, and the report stays partial /
stale. No fact was promoted to current to obtain this result.

## Why six raw assets is not the final product threshold

Alternative A (`>=6 current`) is simple and conservative, but arbitrary: six
correlated instruments in one class can pass while the report has no cross-market
breadth. It also turns a weekend equity closure into a total usefulness failure
even when current crypto, FX, commodity and macro evidence supports two stories.

Alternative B (`>=5 + macro + Top`) measures depth but still permits concentration
in one asset class. It is insufficient alone.

Alternative C (all equity, crypto, FX and commodity classes required) matches the
declared product scope, but makes a cross-market daily report unusable whenever
one legitimately closed or delayed class is absent. Missing a class should be a
visible limitation and prevent a fully healthy result, not erase other evidence.

Policy D combines:

- at least 5 distinct canonical current core instruments;
- at least 3 distinct current core asset classes;
- at least one current risk-asset class: equity or crypto;
- at least 1 current macro indicator;
- at least 2 current validated Top items;
- valid Regime or evidence-backed, clearly explained unavailability;
- meaningful Risk Monitor output or explicit no validated upcoming risks;
- substantive grounded brief;
- mandatory provenance and freshness integrity.

These values are product policy constants, not empirical guarantees of market
correctness. They are intentionally independent of current ranking scores. Missing
a declared core class caps the overall state at degraded. A future change to these
constants requires a versioned policy and replay review.

## Proof and counting semantics

Core symbols are distinct; aliases cannot inflate counts. Macro records do not
count toward core. Only canonical `freshness_status=current` records count. Current
retains its existing contract meaning and is not renamed live. Stale, unknown and
unavailable never count. `verified_latest_session_close` remains count zero and
cannot satisfy this version; Phase 11.4 found no approved price-finality evidence.
Derivatives shadow is excluded.

Asset-class breadth is based on the normalized, validated asset type already tied
to each canonical market observation. The fixed snapshot classes are commodity,
crypto and forex. Missing equity is recorded even though breadth passes. A sixth
instrument is no longer a magic threshold: adding another FX pair changes depth,
not breadth.

## System health and product usefulness are independent

### System health

- `healthy`: pipeline completed; required artifacts exist and validate; publication,
  provenance and freshness checks pass. Valid `partial` / `unavailable` domain
  artifacts are controlled data outcomes, not software failures.
- `degraded`: integrity remains intact, but a non-integrity operational check is
  degraded (for example, deployment retry or optional operational service issue).
- `unusable`: pipeline/publication/required validation, provenance integrity or
  freshness integrity fails.

Source/data coverage belongs primarily to usefulness. A provider transport error
can also become system degradation if it breaches an operational SLO; this contract
does not infer that from an unavailable domain record alone.

### Product usefulness

- `useful`: all Policy D useful requirements pass.
- `degraded`: integrity passes and minimum partial content remains (>=3 current
  core assets across >=2 classes, >=1 macro, >=1 Top, substantive brief), but one
  or more useful requirements fail.
- `unusable`: integrity fails or even the degraded content floor is not met.

### Overall aggregation

- `healthy`: system healthy, product useful, report available/current, and every
  declared core class represented.
- `degraded`: neither side is unusable, but coverage/report/operational limitations
  exist. A justified unavailable Regime or missing class is visible here.
- `unusable`: either system or product is unusable.

`minimum_useful=true` means product useful and system non-unusable. It does not
override `overall_state=degraded` or suppress reasons.

## Fixed production snapshot evaluation

Input is verified production run `34847614658` at
`2026-09-14T13:11:30.000414Z`. This is deterministic evaluation of saved inputs,
not a current-date fetch. See `minimum-useful-gate-evaluated-snapshot.json`.

| Criterion | Result | Evidence |
|---|---|---|
| Core coverage | PASS | 5 / 5: BTC, ETH, Gold, EURUSD, USDJPY |
| Asset-class breadth | PASS with limitation | 3 / 3; equity missing |
| Risk-asset class | PASS | crypto |
| Macro coverage | PASS | 4 / 1 |
| Top Intelligence | PASS | 2 / 2 current and validated |
| Regime | PASS as justified unavailable | 2 dimensions, weight 0.35; stale equity; no anchor |
| Risk Monitor | PASS | substantive partial: stress + data-quality risks; no validated upcoming event |
| Brief usefulness | PASS | grounded deterministic fallback with approved 11.2 reading order |
| Provenance integrity | PASS | validators and references passed |
| Freshness integrity | PASS | no stale/unknown/unverified record counted |

- System health: **healthy**. The production workflow and required/public artifacts
  completed and validated; valid unavailable Regime is not a code failure.
- Product usefulness: **useful with explicit limitations**.
- Overall: **degraded**, because equity is missing, Regime unavailable, and the
  report is partial/stale.
- Minimum Useful gate: **true under proposed policy D**.

This differs from the earlier proposed `>=6` audit gate, which failed 5/6. The
underlying records and statuses are identical. The policy changed because raw
instrument count was found to be a weaker proxy than evidence breadth and depth,
not because Yahoo data was relabeled or Gate B enabled.

## Machine-readable contract and evaluator

`minimum-useful-gate-contract.json` contains the candidate versioned policy.
`src/evaluation/minimum_useful_gate.py` is an audit-only pure evaluator: it accepts
explicit facts and performs no I/O, fetch, publication or feature enablement.
It rejects duplicate symbols and non-current records supplied as current.
`minimum-useful-gate-evaluated-snapshot.json` includes both inputs and result for
byte-stable reproduction. It explicitly records zero verified-close assets.

The JSON file is a policy document, not yet a formal JSON Schema. Before production
integration, implement a closed schema/version validator so unknown or malformed
fields fail closed. The current evaluator deliberately does not infer facts from
raw artifacts; production integration must supply facts only after canonical
validators pass.

## Integration impact notes — review only

No changes are implemented below.

### Orchestration

Add a final read-only evaluation step after Top, Risk and brief validation. It must
consume validated summaries, never affect upstream execution or publication.
Failure to evaluate is a manifest-visible gate error, not permission to publish a
healthy label. Pin policy ID/hash and evaluated artifact hash. Keep Gate B disabled.

### Run manifest

Add distinct `system_health`, `product_usefulness`, `overall_state`,
`minimum_useful`, policy ID, criterion results/reasons and evaluated_at. Do not
overload existing pipeline `status` or freshness fields. Preserve module failures
and warnings independently. State whether evaluation is production or audit-only.

### Public report metadata

Publish only a closed projection: states, counts, class coverage, missing classes,
policy version and normalized reasons. Do not expose internal paths, raw records,
receipts or secrets. Report status/freshness remains independent from usefulness.

### Frontend status display

Render separate system and usefulness labels. For this snapshot: system healthy,
content useful, overall degraded. Always show missing equity, unavailable Regime,
partial/stale report and deterministic fallback. Never translate `minimum_useful`
as real-time, complete, investment-ready or trading-safe. Existing UI design need
not change; this is status-semantic work for a later reviewed phase.

### Tests required before production wiring

Retain current audit tests plus orchestration ordering/failure tests, closed manifest
schema tests, public allowlist/security tests, frontend state combinations and
replay against current/stale/unavailable mixed artifacts. Production policy changes
must not alter ranking, scoring, Regime, prompts, freshness or adapters.

## Validation performed

Tests cover deterministic fixed-snapshot reproduction, missing-class downgrade,
duplicate/non-current rejection, integrity failure, degraded content, unjustified
Regime unavailability, and six same-class assets failing breadth. Full suite and
diff/security checks are reported at handoff. Stop for review before integration.
