# Phase 8.1 — Daily shadow scheduler

Independent `derivatives_shadow.yml` runs at 01:15 UTC daily, plus manual
dispatch. It never invokes production orchestration or alters its cadence.
Existing bounded public Binance adapters collect funding and OI independently.
Provider failure wrappers remain validated unavailable observations. Programming
errors/invalid wrappers fail closed instead of inventing unavailable evidence.

Order: tests → restore encrypted checkpoint → replay history → collect funding
and OI → validate/append immutable archive → rebuild deduplicated fact index →
readiness → encrypt checkpoint → upload only ciphertext.

`scheduler.run` consumes existing local canonical daily/upstream artifacts as
opaque validated context; their timestamps are not refreshed. This phase does
not run market/AI modules. If these inputs are invalid, collection stops before
network access. All generated output lives under outputs/shadow/derivatives.

Deduplication is by consolidated evidence ID (instrument/venue/metric/value/
timestamp/definition), not retrieval time. The index has one fact entry with
all source observation and archive references. Immutable receipts remain in
each capture snapshot; deduplication does not erase provenance. Missing metrics
and days remain missing. Existing readiness rules are unchanged.

## Deployment preparation

Set GitHub Secret `DERIVATIVES_ARCHIVE_PASSPHRASE` to a strong random secret of
at least 32 characters. Never print it or place it in a command argument.
First manual dispatch uses bootstrap=true only when no previous checkpoint
exists. Later runs require checkpoint recovery and authenticated decryption.
Missing/expired checkpoint, missing secret or invalid replay blocks the run.
No silent reset; retain a separate encrypted backup before the 30-day Actions
artifact expiry. Every new checkpoint carries the whole cold+active archive.
Changing the passphrase requires a separately managed re-encryption migration.

GnuPG AES256 symmetric encryption (integrity-protected OpenPGP) protects raw
receipts before Actions upload. Passphrase is fed on stdin; raw provider bodies
never appear in upload allowlists/logs. GitHub Actions artifact access is not
treated as a private-vault guarantee. Restore selects the latest checkpoint
from this workflow on the default branch; API failures abort. All workflow
runs share one concurrency group without cancellation.

See [GitHub artifact API](https://docs.github.com/en/rest/actions/artifacts) for
cross-run discovery and download. Artifacts are finite-retention checkpoints,
not a permanent storage SLA. Schedule execution may be delayed by GitHub.
Workflow must be reviewed, committed and pushed before it can actually run;
no remote activation is performed during this implementation.

Tests are offline adapter-shaped fixtures, not real accumulated days. Readiness
passing remains a review result: production_enabled=false in every output.
