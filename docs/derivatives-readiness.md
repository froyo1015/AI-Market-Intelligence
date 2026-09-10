# D-7 — Shadow readiness gate v1

Readiness is a deterministic review recommendation, never production permission.
`production_enabled` is always false. No scheduler, consumers, AI or publication
configuration is changed.

## Inputs and policy

Supply history as a JSON list of `{bundle, context}` snapshots (the original
D-3 bundle and D-5-B daily context), plus an explicit millisecond UTC `as_of`.
Recompute D-6 evaluations rather than trusting saved metric values. Record
input hashes, cutoff and check outcomes, not raw input records.

Initial conservative policy `derivatives-shadow-readiness-v1`:

- Require all seven UTC dates ending on as_of's UTC date; at least one distinct
  sample per date. Last sample must be no older than 24 hours.
- Exact duplicate pairs count once. Reusing the same bundle hash under changed
  context cutoffs cannot count as additional history. Future-dated, conflicting
  same-cutoff and malformed entries block readiness, not silently disappear.
- Older samples are counted as outside-window and do not affect current gate.
- Every in-window sample must have valid D-6 consistency checks, 100% provenance
  completeness, all four BTC/ETH funding/OI slots present and current, and
  eligible current facts covering all four slots. No averaging away outages.
- Inspect derivatives-only payloads for prohibited interpretation/credential/raw
  transport fields; current record keys are closed to the D-4 contract.
- A synthetic flag or invalid source chain fails existing D-6 validation.

These are review thresholds, not an SLA or a claim that seven days establishes
long-term reliability. Tests use offline generated provider-shaped records;
passing test fixtures are not production observation history.

## Output: derivatives_readiness_v1

`evaluated_at`, `policy_id`, `status` (passing / insufficient_history / blocked),
`production_enabled=false`, `checks` (history, availability, freshness,
provenance, coverage, safety, input_integrity), `history` (counts and dates),
and hash-linked per-sample evaluations. Safety/data failures take precedence
over insufficient history. Empty history alone is insufficient_history.

Freshness is measured at each historical sample's cutoff, with a separate latest
sample age check; it is not re-aged to today. Availability is observed snapshot
availability, not continuous uptime. Completeness depends on the submitted
archive: this gate cannot detect an intentionally omitted run or authenticate
provider receipts without original archived responses. D-6 consistency checks
do not replace upstream validation or independent security review. The safety
field screen is defense-in-depth, not a universal secret detector.

## CLI

`python -m src.shadow.derivatives.readiness --history PATH --as-of TIMESTAMP
--output outputs/shadow/derivatives/NEW_RUN/derivatives_readiness.json`

Writes exclusively to shadow using the existing no-overwrite path guard.
Invalid history root/timestamp fails without output; invalid entries produce
blocked review artifacts with normalized errors. No network calls.
