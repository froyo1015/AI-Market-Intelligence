# Phase 11.6 — Production Gate Integration Notes

## Scope

Review candidate only. No commit, push, live workflow, deployment or production
publication has occurred. Gate D runs after the canonical report and Web View have
been produced. It reads existing validated artifacts and performs no fetch, market
calculation, ranking, Regime decision, AI prompting or derivatives processing.
The policy contract is promoted to `production_reporting` with integration status
`review_candidate`; this describes intended runtime behavior after approval, not
an assertion that the uncommitted candidate is already deployed.

## Execution

The orchestration order adds `minimum_useful_gate` as the final module. Its hard
dependencies include market/macro data, consolidated evidence, signals, Regime,
Risk, daily/Top intelligence, deterministic brief, grounded brief and generated
Web View. Missing hard dependencies block the gate rather than manufacturing a
usefulness result.

The production-safe wrapper validates the canonical evidence-to-brief chain again,
then validates shared freshness metadata. Only market records with both provider
success and item-level `current` count. Top items require validated/current fields
and current scoped freshness. Macro is counted separately. The daily deterministic
brief must still match the deterministic renderer and contain current Top facts.

The evaluator writes `minimum_useful_status.json` atomically to the private output
and the approved public `docs/data` projection. It contains no raw observations,
provider responses, receipts, prompts, secrets or internal filesystem paths.
Verified latest-session count is closed to exactly zero in this policy version.

## Manifest

Run manifest schema advances from 1.0 to 1.1 and adds a separate
`product_usefulness` summary with policy ID, artifact reference, system/product/
overall states, minimum_useful, evaluated_at and limitations. Existing run status,
freshness fields, module failures and warnings remain unchanged. The public JSON is
added to the explicit allowlist and workflow verification/artifact upload.

## Presentation

The existing research banner gains three text-only lines:

- 系統狀態
- 今日情報
- 已知限制

`overall_status=degraded` plus `minimum_useful=true` renders “可用，但資料不完整”.
It is never collapsed to false. Existing Data status, Freshness, Validation, Beta
notice and warnings remain visible. Missing/invalid gate JSON fails closed to
unavailable without breaking the rest of the page. Rendering uses `textContent`;
unknown limitation codes remain inert text and cannot inject HTML.

## Fixed snapshot replay

Replayed Phase 11.5 inputs from production run `34847614658` with the approved
Phase 11.2 deterministic brief. Result matches the approved semantics:

- system_health: healthy
- product_usefulness: useful
- overall_status: degraded
- minimum_useful: true
- current core: 5 across commodity/crypto/forex
- macro current: 4; Top current/validated: 2
- Regime: justified unavailable; Risk: partial/substantive
- provenance/freshness integrity: true
- limitations preserve deterministic fallback, missing equity, Regime unavailable,
  report partial and report stale

This was offline fixed-input validation only. It does not update production files.

## Failure behavior

Provenance or freshness validation failure makes system and product unusable.
Duplicate/non-current records cannot inflate coverage. Missing risk-asset class or
asset-class breadth fails useful status. A technically healthy pipeline may still
produce degraded/unusable content. Publication failure makes system unusable while
leaving the separately calculated product evidence state visible for diagnosis.

## Approval-stage production plan

After approval only: stage the Phase 11.2–11.6 approved files, commit, push, run the
live workflow, verify the gate artifact and manifest summary, await Pages, compare
public bytes, smoke-test desktop/mobile labels and scan the allowlisted archive for
secrets/raw responses/internal paths. Do not change code during that verification.
