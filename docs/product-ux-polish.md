# Phase 9.3 — Product UX polish

Presentation only. The Intelligence landing header explains the evidence-first
Data → Evidence → Intelligence flow, AI writer role, and limits. No performance,
prediction or investment advice claims. Product navigation links existing report
sections without removing market pages or artifacts.

Onboarding explains reading order, freshness, validation and shadow meaning.
Missing report does not assert a known first run: that cannot be established
from current artifacts. The hint explicitly allows first run OR missing artifact.
Partial, stale and missing optional modules get contextual text without changing
statuses or filling evidence gaps. No polling, fetching or new API is added.

Small-screen styles set shrinkable single-column cards, wrapping badges and
long reference IDs, flexible navigation and section headings. Keyboard skip link,
44px navigation targets, details/summary hints and reduced-motion behavior are
preserved. Rendering remains DOM text, never artifact HTML.

No contracts, allowlists, AI prompts, ranking, regime, signals, evidence rules,
derivatives ingestion or Telegram changes. Runtime UI flags are local view-model
state, not additions to artifact contracts. No commit or deployment in this review.

Verification: 465 tests passed, 1 GnuPG test skipped. Navigation targets, DOM
security, UI states and responsive CSS checks pass; generated Pages files match
their source. Real viewport/overflow testing could not run: the bundled
Playwright package has no installed Chromium executable, and Chrome/Edge are
not installed at their standard application paths. Pixel-level mobile layout
and absence of horizontal overflow therefore remain unverified in a browser.
