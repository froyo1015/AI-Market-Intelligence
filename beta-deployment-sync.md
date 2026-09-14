# Phase 10.1.1 — Beta candidate deployment validation

Validated 2026-09-12. Scope: deployment parity and Chrome presentation only.

- deployed_version: `df01ee67902f521ced9d0e703a45a0a760032f87`
- mobile_validation_status: `passed`
- beta_status: `conditional`; no automatic production enablement.
- [Intelligence View](https://froyo1015.github.io/AI-Market-Intelligence/intelligence.html)
- [Manual deployment](https://github.com/froyo1015/AI-Market-Intelligence/actions/runs/34607281953): succeeded.
- [Latest same-commit deployment](https://github.com/froyo1015/AI-Market-Intelligence/actions/runs/34673945933): succeeded.

## Deployment and cache evidence

Candidate UX commit: `4232f9f`; deployment wiring correction: `df01ee6`.
The first run failed because cross-run artifact downloads omitted source run IDs.
The fix supplies the discovered source run ID for previous-report, shadow public
projection and shadow checkpoint downloads. No intelligence computation changed.

Public HTML and JS equal the committed candidate and deployment artifact bytes.
Normal and cache-busting requests return identical SHA-256 values:

| File | SHA-256 |
| --- | --- |
| intelligence.html | 8b907bb5f69b801e3dfec90b8a41f6c8ef0d51f161480def0c10f8970f4b241c |
| assets/intelligence.js | f966c1d2f0ecdf11e58dbff9bef028c038c187a50186efc4de40dc4c39ab138a |
| data/run_manifest.json | 4bc9c5755437ae6f9f61ffc78a8fc228ccdb20dd9d8a14f0220bab617265d248 |
| data/daily_intelligence.json | 88ddd02c591f8b5d39d2b715243dc14458b04520718ed74835d14c1fd196f1a7 |
| data/ai_market_brief.md | 86ff83e920ef9fc59ca7b56e56671bd2b4b5c559c7d51dcf761b5a0e5b835c03 |

Generated files match the latest Pages artifact, not yesterday's manual-run data.
Manifest: `run_20260912T044836Z_orchestration_036867c77e2c`, generated at
`2026-09-12T04:48:39.994368Z`, status `partial`.
No stale cache detected on sampled URLs; this is not a guarantee across all CDN edges.

## Browser QA

Real Chrome for Testing 151.0.7922.34, headless browser, live public page.

| Viewport | Document width | Derivatives columns | Result |
| --- | --- | --- | --- |
| 1440 | 1440 | 559px / 559px | pass |
| 375 | 375 | 317px | pass |
| 390 | 390 | 332px | pass |
| 768 | 768 | 686px | pass |

All audit details expanded: 122 reference entries, zero page errors; 500-character
evidence-ID stress test caused no horizontal overflow at all four widths.
Mobile badge overflow count: zero. AI Brief, Executive Summary/Daily Report,
Evidence Trail and Derivatives Shadow render. Mobile screenshots inspected;
shadow unavailable message and production-disabled warning remain visible.
Screenshots retained locally under `/private/tmp/live-beta-*.png` and
`/private/tmp/live-section-*.png`; these paths are audit notes, not public artifacts.
This does not certify Safari, native devices or every possible data combination.

## Tests and remaining conditions

Isolated candidate suite: 451 passed, 1 skipped (local GnuPG executable absent).
Deployment CI test step passed. Follow-up readiness/download regression tests:
7 passed. `git diff --check` passed.

Live report remains partial; AI Brief is explicitly deterministic fallback.
Derivatives public projection is unavailable, correctly rendered without fabricated
measurements. No production derivative enablement or AI-quality certification.
Only release_parity and mobile_readiness audit findings were replaced; other
historical findings require their own review. No AI prompt, ranking, regime,
signals, derivative computation, Telegram or scheduler cadence changes.
Readiness updates are left uncommitted for review; deferred pipeline edits excluded.
