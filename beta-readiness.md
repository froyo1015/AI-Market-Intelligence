# Phase 10.1 — Limited public beta readiness audit

Assessed: 2026-09-11 13:43 UTC. **beta_status: blocked**.
This is a read-only audit, not permission to enable production or invite users.

## Executive decision

The deployed legacy research service is running, but the current local beta
candidate cannot yet be certified for limited public users. Two blocking gaps:

1. Release mismatch: latest live run uses `430fe66`; local HEAD is `ad2f008`,
   with later dashboard/readiness/UX changes still uncommitted and undeployed.
   Passing local tests do not validate the website users currently receive.
2. Mobile verification missing: CSS/DOM checks pass, but no browser executable
   was available for actual viewport, overflow and long-reference/badge QA.

## Findings

| Area | Evidence / outcome |
| --- | --- |
| System health | Latest 20 listed completed Daily Market Brief runs succeeded (20/20, Aug 24–Sep 11). Latest generation and Pages jobs succeeded; HTML/major artifacts HTTP 200. This is a bounded sample, not lifetime availability. |
| Pipeline completion | Latest run manifest is partial. Calendar, consolidation, signals, risk, daily intelligence and Top Intelligence include partial statuses. Workflow success is not complete evidence coverage. |
| Data reliability | All 10 market and 4 macro records report success. Observation times differ across assets; manifest current is evaluated at generation, not a synchronized live-feed guarantee. Stale/unavailable handling is covered locally. |
| Evidence integrity | Reference preservation and shadow receipt replay tests pass. Full deployed provenance replay was not performed; direct public evidence_bundle URL was unavailable, consistent with it not being a required public artifact. Do not infer missing internal evidence from that URL alone. |
| AI boundary | Latest evaluation is deterministic_fallback and passed deterministic renderer validation. Existing guards reject predictive/causal/trading language in regression tests. This run does not establish real LLM quality or prove absence of every unsupported statement. |
| Public security | Known secret/raw-response/internal-path scans of sampled deployed artifacts and local public files found no matches. Public export allowlist tests pass. Not a complete audit of every historical artifact, route, log or Git revision. |
| User experience | Local onboarding, navigation and unavailable states tested; live HTML lacks the new onboarding. Mobile visual verification remains unknown. |

Live sources: [latest workflow and deployment](https://github.com/froyo1015/AI-Market-Intelligence/actions/runs/34564035533),
[run manifest](https://froyo1015.github.io/AI-Market-Intelligence/data/run_manifest.json),
[AI evaluation](https://froyo1015.github.io/AI-Market-Intelligence/data/ai_brief_evaluation.json),
[market snapshot](https://froyo1015.github.io/AI-Market-Intelligence/data/market_snapshot.json),
[macro snapshot](https://froyo1015.github.io/AI-Market-Intelligence/data/macro_snapshot.json),
[Intelligence View](https://froyo1015.github.io/AI-Market-Intelligence/intelligence.html).
These links are mutable; the run ID identifies the sampled deployment.

## Conditions before inviting users

- Review/freeze an exact candidate SHA, deploy through the approved workflow,
  and rerun the audit against that same deployed version. Do not include the
  separately deferred opt-in production pipeline hook accidentally.
- Perform real mobile checks at narrow viewport sizes with long references,
  stale/unavailable/partial data and expanded audit sections.
- Document supported sources and partial-calendar limitations for beta users.
- Keep derivatives marked shadow and production-disabled. Verify a real encrypted
  restore before relying on its scheduled history; local GnuPG test is skipped.
- A fallback-only beta must explicitly say so. Before advertising grounded AI,
  validate actual provider output and citations on a controlled production trial.
- Recheck public exposure on the deployed candidate and inspect deployment
  inventory/logs; the present pattern scan is limited, not a universal guarantee.

## Machine-readable contract / policy

`beta_readiness.json` uses `beta_readiness_v1`, with timestamped checks across six
categories, local/production/mixed scope, findings and supporting evidence links.
The fixed check registry lives in `src/evaluation/beta_readiness.py`.

- ready: all required checks pass.
- conditional: no critical fail/unknown, but warnings/noncritical gaps remain.
- blocked: any critical fail or unknown (including mobile or release parity).

Validator checks complete coverage, field shapes, evidence presence and recomputes
the verdict. It does not authenticate findings or fetch live services. A passing
validator means a consistent audit contract, not proof the product is ready.
Missing test evidence cannot be converted into pass by changing beta_status.
production_enablement is always false; no verdict triggers any deployment.

Run: `.venv/bin/python -m src.evaluation.beta_readiness beta_readiness.json`.
Audit files are in repository root, not added to Pages/public artifact allowlists.

## Validation

Full suite: **471 passed, 1 skipped** (real GnuPG roundtrip; executable missing).
Six new policy tests cover ready fixtures, conditional, critical fail/unknown,
missing evidence and tampered status/enablement. Fixtures are not live claims.
No intelligence logic, AI prompt, ranking, regime, signals or ingestion changed.
No commit, push, workflow dispatch or production enablement performed.
