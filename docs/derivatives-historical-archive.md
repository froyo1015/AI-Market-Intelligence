# Phase 8.0 — Private shadow history

An append-only archive stores validated funding/OI adapter wrappers, including
their original capture bytes, normalization receipts, provenance and millisecond
timestamps. These are PRIVATE replay inputs, never deployment artifacts. Raw
captures already admitted by the provider boundary remain subject to that
boundary; do not place arbitrary credential-bearing requests in the archive.

Each `derivatives_archive_entry_v1` stores a deterministic entry hash, observation
cutoff, separate archived_at receipt time, original four v1 upstream artifacts,
canonical daily object, derivatives bundle and daily context. Replay revalidates
adapter receipts via consolidation and reconstructs the context with the frozen
daily validator. Re-archiving cannot rewrite source timestamps or known_at.
Late collection is not relabeled as historical availability; archived_at must
be at or after cutoff. Test fixtures are not live historical evidence.

Entries are immutable, hash-addressed, grouped by cutoff UTC date, written with
private permissions and atomic no-clobber publication. Identical entry retries
are idempotent. Multiple attempts/day are preserved; unavailable validated
provider wrappers are archived too. No fabricated records for missing days.
Malformed input is rejected before writing. Archive corruption fails the history
reader closed rather than silently discarding failed days.

Retention v1 uses a 30-UTC-day active window (minimum seven). Older entries remain
in cold archive; there is NO deletion. Readiness uses the active set and retains
the existing seven-day rules. Inventory reports cold/active counts and missing
UTC dates. This avoids losing PIT/receipts while leaving physical deletion and
remote storage lifecycle for a separately approved policy. Local files alone
are not durable across ephemeral Actions runners: no scheduler or artifact-upload
policy is enabled in this phase.

CLI:

`python -m src.shadow.derivatives.archive append --input request.json --archive
outputs/shadow/derivatives/history`

Request fields: funding (wrapper list), oi (wrapper list), daily (canonical
object), upstream (four-element list: evidence, signals, regime, risk), cutoff,
archived_at. All timestamps are UTC with milliseconds.

`python -m src.shadow.derivatives.archive readiness --archive
outputs/shadow/derivatives/history --as-of TIMESTAMP --output
outputs/shadow/derivatives/NEW_RUN/derivatives_readiness.json`

No fetching, production consumers, prompts, ranking, signals, UI or Telegram.
Readiness output contains only existing gate metadata plus archive inventory,
not archived provider bodies. History only counts entries archived by as_of.
