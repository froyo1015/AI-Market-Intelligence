# Daily Reference external scheduler candidate

Local implementation only; not deployed or production-validated.

## Scope / Cron

The existing `ai-market-morning-watchdog` Worker and SQLite Durable Object class are reused. Add UTC `3 0 * * *`, `13 0 * * *`, `23 0 * * *` (Taipei 08:03 / 08:13 / 08:23); retain `55 0 * * *` for unchanged Morning recovery. GitHub's `3,13,23 0 * * *` remains unchanged as fallback. No additional service, binding, credential or class migration is needed: the constructor creates an additive table on the existing SQLite class.

## Decisions

| Canonical checkpoint / runtime | Result |
| --- | --- |
| Valid dated capture with unique create-only commit and trusted creator run | No-op |
| Missing file with empty history, 08:00 through 08:30 inclusive | Atomic slot claim; first attempt or retry after explicit rejection |
| Missing before 08:00 or after 08:30 | No dispatch |
| Invalid/removed checkpoint, missing branch, read/parse failure | Fail closed |
| Active claim, successful dispatch, unknown outcome or same/older slot | No duplicate dispatch |
| Explicit dispatch failure and strictly later Cron slot | Retry within legal window |
| Claim crosses cutoff | No POST; claim retained; GitHub fallback remains available |

Worker validates canonical byte encoding, envelope, PIT timestamps, reference digest, dated path, unique archive commit, exact repository/branch/workflow, creator SHA/run identity and whole-file digest. It is a conservative dispatch guard, not a replacement for Python's full source/unit/decimal/public schema validator. A trusted checkpoint still passes the existing Python validator before workflow reuse. No API-visible JSON shape alone is accepted as provenance. Historical capture validation is not retroactively changed (the existing validator's date/cutoff behavior is retained).

## Isolation and race safety

Daily Reference uses DO instance `ai-market-daily-reference`, table `reference_attempts`, keyed by reference date with `last_slot` (3, 13, 23). Morning continues using its original instance, tables, decision logic and inputs. Atomic SQL UPSERT claims either a new date or an explicitly failed attempt with a strictly later slot. Active/successful/unknown attempts cannot be reclaimed. Completion updates require matching claimed state and slot; duplicates cannot overwrite success. Execution time is checked after lookup and immediately before POST; the controller's scheduled timestamp never authorizes a late invocation. This new table has not been deployed; the candidate schema now includes `last_slot` from creation.

### Bounded retry state machine

- Absent → `claimed` → `dispatched`: permanent stop for that date.
- Absent → `claimed` → `dispatch_failed`: a received non-success HTTP response; only the next strictly later configured slot may return to `claimed`.
- `claimed` → `dispatch_unknown`: transport exception/lost response; conservatively stop for that date because acceptance cannot be disproved.
- While `claimed`, concurrent invocations no-op. A runtime crash retains the claim; no unsafe stale-lock takeover.
- After cutoff, no claim/POST, including retries. A claim acquired immediately before cutoff but finishing after it remains claimed without a POST.

At most three external attempts per date (one per increasing configured slot), never an inline retry loop. 08:03 rejection may retry at 08:13 and then 08:23 if rejected again; any success stops the sequence. Repeated invocation of the same slot cannot retry even after failure. Delayed/reordered slots cannot move `last_slot` backwards. Failure/unknown error text is normalized, never logged verbatim.

Worker never writes a canonical file. A concurrent GitHub fallback may produce redundant workflow dispatch/collection work, but cannot overwrite the canonical checkpoint: existing workflow concurrency plus Python create-only PUT without `sha` and 409/422 winner validation remain authoritative. Existing valid checkpoints reuse without refetch. A received rejection is classified as explicit failure; a provider could still have ambiguous server-side effects, so canonical create-only semantics remain the final safeguard. Bounded dispatch retries are not guaranteed delivery or hard real-time SLA.

## Logging / credential boundary

New subsystem logs only `subsystem`, `status`, `reason_code`, `reference_date`, nullable `workflow_run_id`, `timestamp`. Normalize errors via a closed allowlist. Credentials are runtime-only for a fixed workflow dispatch endpoint; GETs are public, no token/header/body/exception text is logged. A normal GitHub 204 returns no run ID; null is honest, not a manufactured identifier. Existing Morning logging/behavior is unchanged.

## Validation and release

Tests cover legal/missing and valid/no-op states, cutoff boundaries, removed or untrusted provenance, repeated/concurrent claims, late lookup/claim, failed POST, actual Worker routing and SQL claim result preservation, unchanged Morning routing, and Python conflict winner/reuse semantics. No live request or dispatch is part of tests. Commit, push, deployment and subsequent natural-window validation require separate approval. Daily Reference and Cloudflare direct Cron production proofs remain pending.

Initial candidate results: full Python suite 716 passed / 1 skipped (717 collected; GnuPG unavailable locally), JavaScript 13 passed. Bounded-retry revision adds first-failure/next-slot retry, success lockout, cutoff stop, concurrent active POST exclusion, same-slot replay exclusion and unknown-outcome tests, including actual Worker/DO routing. Updated results are recorded after re-running validation. Existing unrelated working-tree changes (including `src/intelligence/pipeline.py`) are preserved and outside this candidate. No commit, push or deployment performed.

Bounded-retry final validation: Python **716 passed, 1 skipped** (GnuPG), JavaScript **16 passed** including all Morning regressions. Direct in-memory SQLite execution of the actual UPSERT confirmed active exclusion, same-slot failure exclusion, later-slot retry and success lockout. Worker syntax and `git diff --check` passed. Capture contract, create-only/conflict validation, GitHub fallback schedule and Morning logic remain unchanged. Ready for commit review, not production-validated.
