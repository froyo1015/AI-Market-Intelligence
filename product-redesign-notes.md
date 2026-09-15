# Phase 12.0 — Intelligence-first reading experience

Status: implementation candidate; visual QA passed. No commit or deployment.

## Information hierarchy

The primary reading flow is: 今日市場一句話 → 今日最重要的事 → 接下來要留意 → 市場環境 → 已知限制 → expandable evidence and technical report.

The summary uses a maximum of three short sentences. Selected stories retain their existing order. Only current, validated objects matched to the selected source object can supply current narrative facts. Daily change signs are translated directly; the story family, score and sample copy never determine direction. Unmatched, unsupported, stale and invalid records receive explicit limited-data copy instead of invented explanations. An unavailable regime gets a generic evidence limitation, not an invented timestamp-mismatch diagnosis.

## De-emphasized presentation

- Beta version details, system health, freshness ages and publication metadata move into the expandable report.
- Scores, raw identifiers, prices, dense cards, full AI/deterministic brief and old report comparisons remain below the primary reading experience.
- Short Chinese descriptions replace machine-oriented headlines in the reading section.
- The primary limitations section retains partial coverage, stale/unverified records, fallback mode and derivatives availability notices.

## Preserved audit information

The original report DOM, source names, timestamps, evidence IDs, scores, warnings, regime detail, prices, derivative status, safe Markdown report and provenance audit remain accessible inside the technical disclosure. Per-story evidence links open that disclosure and target the corresponding original Top Intelligence card.

No ranking, scoring, deduplication, source, prompt, freshness contract, evidence contract, Gate or regime processing changes are involved. The JavaScript reading projection is presentation-only. Unknown event representations are not converted into invented calendar notices.

## Product review

1. Thirty-second comprehension: passed at 1440, 390 and 375 pixels; concise summary and selected stories precede diagnostics.
2. Useful without prices: the primary flow contains observation text rather than price cards.
3. Understandable stories: supported daily direction and regime classification receive short Chinese descriptions; unfamiliar objects conservatively retain a limited-data notice.
4. Numbers support content: scores and detailed metrics are confined to the expandable report.
5. Auditability: original report and reference sections remain available.
6. Market-brief experience: narrow reading column, short paragraphs and restrained navigation replace the dashboard-first opening.

## Validation

JavaScript tests cover positive/negative/flat observations, prevention of direction inference from a story key, stale and invalid exclusion, absent source-object links, unsupported metrics, missing report, retained selection order, and prohibited language. Existing JavaScript tests also passed.

Browser QA used the Phase 11.7 deployed artifact as the BEFORE state and the same live data artifacts with the Phase 12.0 shell/script as the AFTER state. All three viewports passed. The first attempt found duplicate regime wording and mobile layout shift; both were corrected in presentation code. Final cumulative layout shift measured 0.0012 at 1440px, 0.0109 at 390px and 0.0109 at 375px. The technical disclosure opens, closes, links to the selected evidence card and remains free of horizontal overflow when fully expanded.
