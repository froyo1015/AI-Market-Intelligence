# Phase 11.2 — Regime and Brief Usefulness

## Scope and decision

Review candidate only; no commit, deployment, API request or source refresh.
Baseline is the latest verified live production run `34847614658`, commit
`804731ea3faf05ea94a0af7b8492d4a076e5df95`, generated
`2026-09-14T13:11:30Z`. Replay evaluates at that original time, not today's time.
No regime, signal, ranking, dedup, prompt, contract or freshness threshold changes.

**Keep regime unavailable.** Existing evidence cannot justify a synchronized
current market classification. Improve the deterministic report's reading layer,
without manufacturing a classification or removing the audit record.

## A. Regime availability trace

Sources fetched all 14 symbols. Missing price records are not the bottleneck.
Evidence exists, but fetched successfully does not mean current observations.
Derived evidence keeps its 48h stale limit; signal alignment keeps its 36h gap;
regime input-artifact maximum age stays 24h, future skew stays 5 minutes.

| Dimension | Required signal inputs | UTC source timestamps | Eligibility / cause |
|---|---|---|---|
| equity (0.30) | SPY, QQQ | Sep 11 04:00 | stale_data; about 81.19h old |
| volatility (0.25) | SPY, QQQ, VIX | Sep 11 04:00 / Sep 14 05:00 | 73h gap; stale equity |
| crypto (0.20) | BTC, ETH | Sep 14 00:00 | eligible, about 13.19h old |
| dollar_yield (0.15) | DXY, US10Y | Sep 14 04:00 / 05:00 | eligible, 1h gap |
| cross_asset_alignment (0.10) | SPY, QQQ, BTC | Sep 11 04:00 / Sep 14 00:00 | 68h gap; stale equity |

Only 2 dimensions and weight 0.35 are eligible. Rules require at least 3,
weight >=0.65, and an equity or volatility anchor; neither anchor is available.
Even making synchronization more permissive would not make stale equity current.
Current crypto/dollar evidence alone cannot represent the whole market.

Classification: **correct safety behavior with incompatible available observation
times**. Weekend/session timing plausibly explains different bar dates, but these
artifacts do not establish matched economic observation windows. Midnight-style
daily bar labels are not proof of when a bar closed or became available. There is
no evidence that the 36h rule is the sole or incorrect blocker.

### Future session-aware design (not implemented)

An observation-window approach must retain original timestamps and document
instrument calendar/timezone, session identity, observation interval start/end,
bar finality, publication/availability and retrieval time. Select only records
available by the replay cut-off, never infer a later close from an earlier label.
Require deterministic common comparison windows and validated calendar versions
(including holidays/DST). No forward fill may turn an old price into a current
one. Align historical windows only as historical context, not current regime.
If no matched fresh windows exist, remain unavailable. Archived PIT records and
window semantics are prerequisites; current snapshots cannot prove them. Any
future contract/adapter change requires separate review. No safe regime fix or
threshold widening is justified here, so before/after regime is identical.

## B. Deterministic report

Before: Top blocks include scores, story keys and many references, immediately
followed by coverage tables/warnings/data windows. Regime, cross-asset observations
and stress appear later. Full report: 47,528 characters.

After: a concise Traditional Chinese reading layer precedes complete audit detail:

1. 今日市場重點 — existing Top order/headlines/explanations/monitor text, unchanged.
2. 市場環境 — existing classification or concise unavailable explanation.
3. 未來 24–48 小時風險 — existing events and observed stress, never predictions;
   no validated event is explicitly distinguished from no future risk.
4. 資料狀態 — report status/freshness and the stale-data limitation.
5. 證據與引用 — all original metadata, detailed Top blocks, coverage, warnings,
   regime dimensions, signals, risks, provenance catalogs and limitations.

Short main-content object IDs link to IDs in the complete detail. All original
reference strings, timestamps, warning text and source URLs remain. Original
English fact text is not paraphrased or translated into invented analysis.
Full report is now 48,769 characters: **reading order improved, not total size**.
The audit appendix intentionally remains verbose and repeats the structured Top
detail. Collapsing that appendix would be a separate UI concern, not this phase.

Before/after artifacts: `review/phase-11.2/before-brief.md` and
`review/phase-11.2/after-brief.md`. No production outputs overwritten.

## C. Minimum useful gate (audit only)

See `minimum-useful-intelligence-gate.json`; never used to change deployment.

| Criterion | Result | Evidence |
|---|---|---|
| >=6 current core assets | FAIL | 5: BTC, ETH, Gold, EURUSD, USDJPY; five equities stale |
| >=1 current macro | PASS | DXY, US10Y, VIX, WTI = 4 |
| >=2 current validated Top | PASS | dollar/yield pressure 68; BTC/ETH co-movement 61 |
| valid regime or justified unavailable | PASS | explicit 2/3, 0.35/0.65, missing anchor |
| meaningful risk / explicit no validated upcoming | PASS | 1 observed stress + 4 quality risks; 0 upcoming |
| substantive grounded brief | PASS | existing two stories precede diagnostics |

Overall **FAIL**, not forced to pass. Derivatives are excluded. Report still
partial/stale, and deterministic fallback remains active. Priority is to observe
the next naturally updated equity session, not to relabel weekend data current.

## Tests and boundaries

496 passed, 1 skipped (existing GnuPG environment limitation). Tests cover reading
order, determinism, non-mutation, empty/unavailable handling, full reference and
warning preservation, and renderer tamper rejection. Existing regime/freshness
tests remain unchanged. Replay passes deterministic renderer validation against
the original production daily/Top artifacts. No new providers, APIs or AI logic.
