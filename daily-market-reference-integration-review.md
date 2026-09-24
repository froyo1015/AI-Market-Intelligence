# Phase 13.3.3 — Integration review

Review candidate, 2026-09-23. No commit or deployment was performed.

## Implemented path

```text
Fed H.15 nominal US10Y + ECB daily reference XML
  → independent validation and date-precision normalization
  → src/output/daily_market_reference.json
  → closed public projection: docs/data/daily_market_reference_public.json

08:10 Asia/Taipei pre-cutoff capture workflow
  → create-only public-safe capture on morning-reports branch
  → 08:30 Morning Report workflow discovers capture
  → create-only sidecar bound to immutable Morning report_id
  → docs/data/morning_daily_reference_public.json
```

The new source layer is independent of the market-data/evidence/intelligence engine. It does not change Top Intelligence, regime, risk, briefs, AI prompts, calendar, derivatives or frontend. The existing `morning_report_public.json` contract remains unchanged. Its new sidecar holds the observed reference state and provenance for Morning context or future comparisons. This is a **dated daily reference**, not a live quote or Pulse.

The existing orchestration finishes and cleans the public data directory first. The workflow then binds the pre-cutoff Morning sidecar and generates the current daily reference projection. `src.daily_reference.public_validate` checks each new public artifact before the existing Pages upload. The canonical run manifest continues to describe the existing intelligence pipeline, not these two later sidecars; their checkpoint hashes and validators are separate. A follow-up product phase would need explicit manifest registration if this data becomes an intelligence input.

## Source and rights boundary

- H.15 identifies the Treasury nominal constant-maturity row, with **release date separate from observation date**. The inspected official release dated 2026-09-22 showed the latest data date 2026-09-21. [Official release](https://www.federalreserve.gov/releases/h15/)
- ECB provides USD, JPY and GBP per EUR with one common reference date. USDJPY/GBPUSD carry formulas and exact input rates; results are rounded to eight decimal places. [ECB reference XML](https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml)
- Board and ECB reuse/attribution policy are linked in the contract. Public projection has a closed field list and normalized failure reasons. HTTPS certificate verification remains enabled; the installed `requests` client and CA bundle resolved a local platform trust-store issue without weakening TLS.
- Neither source guarantees a new observation every calendar day. Status uses source date and the conservative stated thresholds. The source date stays visible, and retrieval never makes an old observation recent.

## Observed live run in this workspace

At 2026-09-23T13:19Z, both official endpoints returned validated data. The generated artifact reports `available` for all four:

| Asset | Reference value | Source observation date | Release date | Meaning |
|---|---:|---|---|---|
| US10Y | 4.96 | 2026-09-21 | 2026-09-22 | H.15 nominal 10-year yield, percent per annum |
| EURUSD | 1.1463 | 2026-09-22 | date not supplied | ECB USD/EUR reference |
| USDJPY | 157.17525953 | 2026-09-22 | date not supplied | ECB cross calculation |
| GBPUSD | 1.33632548 | 2026-09-22 | date not supplied | ECB cross calculation |

Values above are a one-time source verification, not a historical 08:30 capture and not a live trading quote. The concrete artifacts in `src/output` and `docs/data` retain their actual generated_at and source metadata.

## Morning capture behavior

The existing workflow starts at 08:30 Taipei, after the cutoff. A separate 08:10 daily capture is therefore required to prove what was available before the Morning baseline. A delayed capture finishing after 08:30 is rejected. It may be partial if an official source fails; a valid partial capture is immutable for that day. An all-unavailable response creates no baseline. After the Morning Report checkpoint exists, its sidecar is created only from that same-date pre-cutoff capture and the validated report ID. Retries restore the exact existing bytes; removal/corruption fails closed. The next date has a distinct archive key.

There is no retroactive Morning asset baseline for 2026-09-23. This workspace generated the ordinary daily reference artifact after the cutoff, and correctly did not bind it as the Morning snapshot. The source capture workflow and GitHub branch writes have not run in production, so cross-run behavior is verified only with offline GitHub API tests.

## Test and review result

- Official-format parsing: normal ECB/H.15, H.15 nominal versus inflation-indexed row, future/duplicate/malformed data, unavailable/stale isolation.
- Contract: exact four assets, units, source/date precision, citation/formula/operand preservation, cross-rate recomputation, age consistency, public allowlist and secret/path rejection.
- Capture: cutoff, same-day byte-identical reuse, missing source, origin/provenance checks, corruption and deleted-file history, next-date key, Morning report binding.
- Existing Morning checkpoint and orchestration tests remain passing. Full Python suite and `git diff --check` are part of final validation.

## Remaining operational limits

1. GitHub scheduled jobs can start late; 08:10 is a target, and late completion intentionally yields no Morning sidecar. The Morning Report itself continues.
2. H.15 HTML is a structured official page, yet its markup can change. Such a change produces an unavailable US10Y row; there is no Yahoo fallback.
3. The public projection's source hash is an integrity reference to response bytes, not a claim of official signature or price correctness. The raw response is never published.
4. These daily references do not satisfy hourly Market Pulse or establish earlier historical Morning captures. No frontend presentation of the new reference file was added in this phase.
5. Public Pages deployment of this candidate has not occurred. A production run must validate source reachability, checkpoint creation/restore and published byte hashes after review.
