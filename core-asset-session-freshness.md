# Phase 11.3 — Core Asset Freshness & Market Session Semantics

## Decision / evaluation boundary

Do not change the production freshness clock or Minimum Useful Intelligence gate.
Introduce only an **offline evaluation prototype**, not a production enrichment.
Latest-session recency and data freshness are separate facts. A daily adjusted
Yahoo bar is not an official exchange close or live quote merely because its date
matches the last trading day. Existing artifacts lack explicit finality, interval
end and availability attestations, so production latest-session status is unknown.

Baseline remains verified live run `34847614658`, commit `804731e`, report time
2026-09-14T13:11:30.000414Z (Monday 09:11:30 New York). This is a saved-run audit,
not a September 15 live refresh. Core ages below are measured at market artifact
generation 13:11:26.216983Z; they are four seconds older at report composition.

## A. Every core asset

All rows: retrieved_at = **2026-09-14T13:11:26.216983Z**, propagated from the
adapter artifact. This is not a separately measured per-symbol receipt time.
The core contract has the same 48h elapsed-time limit for all ten records.

| Symbol | Class | Source timestamp UTC | Age hours | Session at report time | Freshness | Reason |
|---|---|---|---:|---|---|---|
| SPY | equity ETF | 2026-09-11 04:00 | 81.191 | before core open | stale | >48h |
| QQQ | equity ETF | 2026-09-11 04:00 | 81.191 | before core open | stale | >48h |
| NVDA | equity | 2026-09-11 04:00 | 81.191 | before core open | stale | >48h |
| AAPL | equity | 2026-09-11 04:00 | 81.191 | before core open | stale | >48h |
| TSLA | equity | 2026-09-11 04:00 | 81.191 | before core open | stale | >48h |
| BTC-USD | crypto | 2026-09-14 00:00 | 13.191 | 24/7 convention | current | <=48h |
| ETH-USD | crypto | 2026-09-14 00:00 | 13.191 | 24/7 convention | current | <=48h |
| GOLD | gold futures | 2026-09-14 04:00 | 9.191 | weekday; exact venue state unverified | current | <=48h |
| EURUSD | OTC FX | 2026-09-13 23:00 | 14.191 | weekday indicative session; no central exchange | current | <=48h |
| USDJPY | OTC FX | 2026-09-13 23:00 | 14.191 | weekday indicative session; no central exchange | current | <=48h |

Exactly five current: BTC, ETH, GOLD, EURUSD, USDJPY. SPY is an illustrative sixth
candidate, not a new ranking choice; all five equities have the same blocker.
Even if Friday was the latest completed core session, date labels alone cannot
attest a finalized close. Extended-hours trading is not claimed to be closed.
Do not silently substitute macro instruments into the core denominator.

## B. Existing session audit

`src/models/freshness_schema.py` uses elapsed UTC seconds: core 48h, macro adapter
120h, derived evidence 48h. There is no exchange-calendar pause in that clock.
`asset_metadata.py` describes sessions and legacy presentation thresholds (e.g.
equity 36/120h), but does not provide a verified calendar or replace the canonical
48h evidence contract. Crypto, FX and futures therefore share the core age test;
macro has a different duration, not session awareness. Daily history is requested
with `interval=1d`; timestamps are explicitly described as provider bar labels.

During open, overnight, weekends, holidays, preopen and postclose the same age
arithmetic runs. Thus it can call an old Friday label stale on Sunday, and can
call yesterday's daily bar current during today's open. **current never promises
live streaming**. Source failure is a separate status, not inferred from age.

Distinctions to preserve:

- Newer finalized session expected but absent: `superseded_session` (possible
  delayed source, not proof of a transport failure).
- Closed core session plus proven latest finalized close: `latest_validated_close`.
- Open session with previous close: `prior_close_during_open`, historical context.
- Source failure/unavailable: `unavailable`, never rescued by calendar matching.
- Provider delay/finality unknown: `unknown`; no invented grace interval.

Official reference: [NYSE hours and calendars](https://www.nyse.com/trade/hours-calendars)
lists core hours 09:30–16:00 ET; its
[2026 calendar](https://www.nyse.com/publicdocs/nyse/ICE_NYSE_2026_Yearly_Trading_Calendar.pdf)
is the reference for the September replay schedule including Labor Day.
The prototype's calendar is a bounded test fixture, not a production calendar
service. Futures maintenance, FX conventions, index publication and exchange
early closures require their own versioned schedules; no universal US calendar
is applied to them. Source reliability/finality is not conferred by the calendar.

## C. Independent session-recency contract

`src/evaluation/session_recency.py` accepts an observation and explicit bounded
schedule. It preserves every input field, including original freshness, age,
source timestamp, retrieved_at, generated_at, identity and provenance. It adds:

- session_state: open / closed / unknown (core session only)
- session_recency: latest_validated_close / prior_close_during_open /
  superseded_session / unavailable / unknown
- latest_session_id; calendar_version and calendar_source when valid
- usable_as_current: always false; this prototype cannot grant current eligibility

For latest-close eligibility require explicit session_id, interval_end,
finality=`validated_final_close`, finality_reference and available_at. Finality
attestation must come from a validated boundary; arbitrary caller assertions are
not production evidence. Enforce close <= availability <= retrieval <= cut-off.
Never move source_timestamp to close time or use retrieval to reset age.
Schedule needs source, version, known_at <= cut-off, bounded validity and complete
non-overlapping sessions including the predecessor. Completeness and calendar
authority are trusted fixture preconditions, not proven by this prototype; this
is a further reason it is not wired to production. Unknown bounds/future calendar
knowledge and missing finality fail closed. No system clock is consulted.

## D. Consumer decision

Keep the current gate: >=6 **canonical current** core assets (not necessarily live
quotes). A possible separate future "daily-close context coverage" gate could
count a disjoint set of current plus verified latest-session closes while markets
are closed, with visible labels. That is a different product claim requiring
review, provenance/finality evidence and presentation support. It cannot be used
to satisfy the current gate, activate regime inputs, or imply synchronized times.
No ranking, regime, signal, evidence truth or UI contract is changed here.

## E. Replay scenarios

`session-freshness-scenarios.json` contains explicit synthetic observations,
schedule and evaluator outputs. Tests cover Friday open, after close, Saturday,
Sunday, Monday preopen, exact open boundary, Labor Day, stale open-session source,
and immediate close before the new close has arrived. Additional tests reject
future source/retrieval/availability, missing finality and future calendar knowledge.
Every scenario preserves the original stale flag, even when recency is latest.
It never fills a newer session, invents a quote or promotes an open-session stale
source. This is not a claim of live session validation across every instrument.

## F. Before/after (original production evaluation time)

| Metric | Before | After audit |
|---|---|---|
| Current core | 5 | 5 |
| Verified latest-session core | not measured | 0 verified; 5 equity candidates unknown |
| Current macro | 4 | 4 |
| Current validated Top | 2 | 2 |
| Regime | unavailable, justified | unchanged |
| Risk monitor | partial, 1 stress + 4 quality risks | unchanged |
| Brief usefulness | substantive after approved 11.2 ordering | unchanged |
| Overall gate | FAIL (5/6 core) | FAIL |

Updated `minimum-useful-intelligence-gate.json` preserves all original criteria and
adds session_review counts. No new fetch, production integration, commit or deploy.
Resolution is truthful separation of concepts, not promotion of unproven closes.
Next review can authorize final-bar/session provenance acquisition using existing
sources; simply waiting for a new daily bar can also change the original gate's
count without changing any policy. Neither outcome is assumed here.
