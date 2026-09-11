# Phase 8.2 — Read-only derivatives shadow view

Existing plain HTML/JS Intelligence View gains a section after Market Overview.
No intelligence input or AI prompt changes. Labels: Shadow Validated; Not used
for AI decisions. Missing/invalid data shows unavailable; stale facts remain
visible as historical measurements, never current intelligence.

Private archive → full receipt replay → D-6 context consistency check → explicit
public projection → docs/derivatives-shadow.json → read-only DOM text nodes.
The public contract contains ONLY: schema, generation time, validation status,
four BTC/ETH funding/OI measurements (value, unit, timestamp, freshness,
freshness TTL, evidence quality, provenance status), and readiness counts,
production_enabled=false and normalized blocking reasons. No receipt IDs,
raw responses, capture hashes, transport metadata or secrets are copied.

Readiness is recalculated from the archive at export time, not supplied as a
trusted arbitrary document. Conflicting newest measurements are unavailable.
No records or invalid replay fail closed. Browser re-ages freshness using source
timestamp/TTL and identifies old readiness snapshots, so a checked-in snapshot
does not claim to remain current indefinitely.

Exporter CLI: `python -m src.shadow.derivatives.dashboard --archive PATH --as-of
MILLISECOND_UTC_TIMESTAMP --output docs/derivatives-shadow.json`.
The default output is the Pages root; explicit paths are for offline testing.
Public validator uses a closed recursive contract. Pages publication revalidates
the file and removes invalid payloads before deployment; no raw archive folder
is added to the allowlist.

This review exports EXISTING archived observations only. It does not collect new
data or change shadow scheduling, and does not activate a cross-workflow public
snapshot refresh. Until a separate refresh handoff is approved, this is a static
dated snapshot; missing files do not interrupt other page sections. No remote
deploy/commit is performed. The UI's quality score is evidence quality, not
directional confidence or a trading assessment.
