# Phase 11.4 — Verified Market Close Evidence

## Decision

**Existing saved Yahoo outputs cannot verify a final latest-session close.**
Keep the production gate and original freshness unchanged. Deliver a design
contract and executable examples only; no production validator, calendar
dependency, adapter modification, consumer integration, commit or deployment.

Fixed production evaluation: run `34847614658`, cutoff
`2026-09-14T13:11:30.000414Z`. A separate read-only Yahoo chart metadata inspection
was performed during this review; it is NOT inserted into that historical run.
No new API provider or credentials were used. No raw provider body was saved or
published in review artifacts.

## A. Meaning of verified_latest_session_close

This is a **price/session verification result**, not a freshness status. Preserve
source_timestamp, retrieved_at, generated_at, age_seconds and original freshness.

Require independently validated evidence for all six assertions:

1. A versioned venue-specific calendar includes the session, with known-at time,
   complete bounded coverage, applicable exceptions and retained authority refs.
2. Its close is at or before the evaluation cutoff (UTC, timezone-aware).
3. Instrument, listing venue, currency, regular-session interval and source bar
   date semantics match that session. SPY uses NYSE Arca, not simply NYSE-listed.
4. No later session in the complete calendar has closed by the cutoff.
5. A separate price attestation establishes an **unadjusted regular-session
   close**: exchange official close or a specifically reviewed vendor final-close
   policy. A vendor-derived result must be labeled as such, not exchange official.
6. Price source, finality attestation, receipt hash, availability time, calendar
   version and verification policy are traceable and replayable.

The project currently has **no approved Yahoo finality policy**. "Official-enough"
cannot mean "the value looks plausible", "after 16:00", "two polls agree", or
"matches Friday's date". Final prices may later be corrected; record revisions
forward-only with known-at times, not rewrite earlier replay facts.

`market-close-contract.json` is the machine-readable design specification, not
a deployed JSON Schema validator. Receipt hashes prove integrity of captured
inputs, not price truth. Raw receipts must remain outside public artifacts.

## B. Existing source audit

| Approach | What it proves | What it cannot prove / reliability | Replay and calendar implications |
|---|---|---|---|
| Current adapter + normalized output | successful daily history, last row label, adjusted value, ticker and source | `auto_adjust=True`, `actions=False`: value can be adjusted, not the actual auction close; finality/interval metadata discarded | saved snapshots deterministic; no holiday/early-close proof; index timezone retained only as timestamp |
| Existing Yahoo v8 chart metadata | declared symbol, venue, timezone, interval and current period boundaries | current period is not historical authoritative schedule or final-price certification; no finality flag found in inspected response | snapshot metadata required for PIT; live refetch can change; fixed offset alone fails DST |
| Raw chart quote.close vs adjclose | provider differentiates quote series and adjusted series | unadjusted field alone is still not an exchange-official finality attestation; current daily candle may be provisional | retain basis and revisions; no inference of publication time from bar label |
| Yahoo regularMarketTime/regularMarketPrice | provider's regular-market quote time/value | not proof of auction close or finalized daily candle; can be last trade | cannot attach today's metadata to a historical price |
| Existing asset_metadata + 11.3 prototype | timezone/session descriptions; supplied bounded fixture can select completed sessions | descriptions and fixture are not authoritative production calendar; prototype trusts synthetic finality input | deterministic supplied fixtures only; not general holiday/early-close coverage |
| exchange_calendars candidate | deterministic exchange schedules with holidays/special closes | not price evidence, not official exchange authority or proof of unexpected closure knowledge | pin release/calendar range/tzdata and archive schedules; review aliasing and exceptional closures |

Local inspection: installed yfinance implementation uses `/v8/finance/chart/...`,
stores `_history_metadata`, parses `exchangeTimezoneName`, and exposes history
metadata. The project adapter returns only its DataFrame. Neither
`exchange_calendars` nor `pandas_market_calendars` is installed or declared.
No dependency added.

Read-only SPY chart inspection succeeded on the endpoint already used by yfinance:
`https://query1.finance.yahoo.com/v8/finance/chart/SPY?range=5d&interval=1d`.
Observed allowlisted semantics: SPY / ETF, PCX / NYSEArca,
America/New_York, EDT, offset -14400, granularity 1d, pre/regular/post periods,
quote and adjclose arrays. No explicit finality flag in this sample. Absence of a
flag in one response is not proof that every Yahoo product lacks such data; it
is sufficient to reject claiming that this inspected path already certifies it.
The endpoint audit does not justify changing source APIs now.

Sources: [yfinance API reference](https://ranaroussi.github.io/yfinance/reference/index.html),
[exchange_calendars project](https://github.com/gerrymanoim/exchange_calendars),
[calendar aliases](https://github.com/gerrymanoim/exchange_calendars/blob/master/exchange_calendars/calendar_utils.py).
The inspected library aliases NASDAQ/XNAS and ARCX to XNYS: shared schedules must
not be mistaken for identical listing venues. Confirm supported Python version,
license and pinned version before proposing installation. Free access does not
by itself establish public redistribution rights; that remains separate review.

## C. Calendar authority design

A deterministic calendar is justified as a future session boundary dependency,
but not enough to resolve this phase's price-evidence blocker. Recommend evaluating
exchange_calendars against official NYSE and Nasdaq schedules before adoption.
Use an explicit instrument->venue->calendar mapping; never ticker-prefix guessing.

- Regular day: timestamped open/close with America/New_York timezone.
- Weekend / holiday: explicitly no session within a validated coverage range.
- Early close: special close overrides normal close; never assume 16:00.
- DST: date-specific timezone conversion; retain tzdata version, no constant offset.
- Preopen / postclose: derived from half-open [open,close) core intervals, not claims
  about all extended-hours venues.
- Previous completed session: max(close <= cutoff), including previous sessions
  outside the report date. A missing schedule boundary returns unverified.
- Exceptional closure: apply only an authority revision known by the replay cutoff.
  A calendar downloaded later must not manufacture historical knowledge.

[NYSE calendar](https://www.nyse.com/trade/hours-calendars) specifies regular core
hours and early closes; the November 27, 2026 replay uses 13:00 ET (18:00 UTC).
[NYSE auction information](https://www.nyse.com/trade/auctions) is separate from
calendar evidence. Calendar completion is never price finalization.

## D. Deterministic validator specification

See ordered rules in the JSON contract. Validate structure, finite price/currency,
identity, source refs and PIT ordering before eligibility. Resolve source date in
the declared exchange timezone, with explicit daily-label semantics; compare
interval start/end to expected regular session. Do not reinterpret midnight as
16:00 or add an invented interval. Missing timestamp semantics -> unverified.

Missing price/source failure -> unavailable. Proven older-session data ->
stale_source. Inconsistent/future/missing identity, time or finality ->
unverified_session_observation. Only all checks satisfied ->
verified_latest_session_close. Preserve reason codes and both evidence references.
Conflicting source closes remain separate records and unverified until a
documented resolution policy applies; do not average or silently prefer one.

During Friday open, Thursday can be the latest completed close; during Monday
open, Friday can still be the latest completed close. Neither is a current quote
or evidence for the unfinished day's direction. At the exact closing boundary,
the new session is complete but its final price may not yet be available: wait
for actual evidence rather than invent a grace period or finality assertion.

## E. Proposed consumer semantics (not activated)

Retain A today: >=6 canonical current assets. These are current under the existing
age contract, not necessarily live quotes. Separately report latest completed
session coverage.

Recommend B **only for a future explicitly daily research coverage gate**, after
price attestation and publication labels are approved: count distinct union of
current and verified latest-session assets, never double-count a symbol. This is
honest for a daily-close report, not for a live market-readiness gate. Always show
original freshness, session date/close, price basis/source and open-session state.
When open, label "previous completed session; not today's live quote". Unverified
or superseded observations do not count. No downstream signal/regime input
eligibility changes follow automatically from this coverage metric.

## F. Replay evidence and limitations

`tests/test_verified_market_close_design.py` is a **test-only design oracle**, using
the 11.3 offline prototype. Synthetic finality references are not real evidence.
Examples cover Friday open, exact close before receipt, after close, weekend,
Monday pre/open, holiday, early close/EST, stale source, timestamp mismatch,
adjusted price, absent finality and failed provider. Original stale status stays.

`market-close-replay-results.json` records expected/actual results. These examples
test decision semantics, not a complete production validator: attestation
authenticity, interval-start/schema enforcement, schedule completeness and real
vendor finality require future implementation/review. No synthetic examples enter
the fixed production count. No claim that source timestamps prove actual closes.

## G. Fixed production shadow comparison

| Metric | Before | Proposed shadow semantics |
|---|---|---|
| Current core | 5 | 5 |
| Verified latest-session core | 0 verified | 0 verified |
| Usable distinct core under B | 5 | 5 |
| Unverified equity candidates | 5 | 5 |
| Current macro / Top | 4 / 2 | 4 / 2 |
| Regime | unavailable, justified | unchanged |
| Risk monitor | partial | unchanged |
| Brief | substantive fallback; partial/stale | unchanged |
| Gate A / proposed B | FAIL | FAIL / FAIL |

The metadata audit discovered useful identity/session context but not sufficient
price-finality evidence. Do not manufacture the sixth qualifying asset. Preserve
approved Phase 11.2 presentation; stop for design review before implementation.
