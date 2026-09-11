# Phase 9.1 — Research dashboard presentation

Presentation-only changes to the existing static shell and JS. No new endpoints,
artifact contracts, source adapters, publication allowlists or decision logic.

- Daily research status banner uses existing recorded availability/freshness.
- Last update age is explicitly artifact generation age, not source freshness.
  Older-than-24h snapshots get a display warning; upstream freshness is not
  overwritten. Missing/invalid/future timestamps do not appear current.
- In-page navigation keeps brief, priorities, context, risks and audit reachable.
- Top Intelligence keeps upstream order/headlines/why/monitor/score intact.
  Explicit "Why this matters" and "Monitor next" labels explain the existing
  fields; no new market explanations are generated.
- Evidence groups use readable field labels and individual monospaced IDs;
  no references are removed, shortened or turned into invented links.
- Derivatives remains a separate shadow research section with visible freshness
  badges, readiness and production-disabled disclosure. Not used for AI decisions.

All artifact text is inserted with textContent/DOM APIs, never HTML parsing.
Existing CSP and safe Markdown handling remain unchanged. Empty states remain
visible rather than blank cards. This is a local implementation, not deployment.
