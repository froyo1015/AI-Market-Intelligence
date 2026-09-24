# Phase 13.3.3 — Daily Reference Market Layer

Status: implementation candidate for review. No hourly Market Pulse or frontend redesign.

## Scope and identity

Four reference series only: `US10Y` = Federal Reserve H.15 **nominal** Treasury 10-year constant-maturity yield in percent per annum; `EURUSD` = ECB USD per EUR; `USDJPY` = ECB JPY per EUR divided by USD per EUR; `GBPUSD` = ECB USD per EUR divided by GBP per EUR. The ECB pairs are reference calculations, not traded quotes. Series identity and formulas are versioned. Neither Yahoo nor a later rate feed can silently replace these values.

The permitted sources and attribution conditions are reviewed in [Phase 13.3.2](market-data-source-strategy.md). [Federal Reserve reuse policy](https://www.federalreserve.gov/disclaimer.htm), [H.15 release](https://www.federalreserve.gov/releases/h15/), [ECB reuse policy](https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html), [ECB rates](https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml). Source access is no guarantee of a current value.

## Canonical observation contract

`daily_market_reference_v1` is an object with `generated_at`, `status` (`available`, `partial`, `unavailable`), `reference_kind` = `official_daily_reference`, and exactly four `assets` in canonical order. Each asset has:

| Field | Meaning |
|---|---|
| `asset_id`, `symbol`, `asset_class`, `series_id` | Stable identity; cross-rates are separate derived reference series |
| `reference_value`, `unit` | Decimal-string value and explicit unit when source validates; null when unavailable |
| `source`, `source_url`, `source_timestamp`, `timestamp_precision` | Official publisher and original period date. `source_timestamp` is `YYYY-MM-DD` with `timestamp_precision=date`; the source does not claim an exact intraday observation instant |
| `reference_period`, `timezone`, `release_date` | Source period/date and Europe/Berlin (Frankfurt civil time) or America/New_York semantics. H.15 release date differs from observation date |
| `retrieved_at`, `freshness` | UTC first retrieval and `{status, age_seconds, reason}`; age is measured conservatively from start of source date, never recast as a live quote |
| `provenance` | Attribution, source and reuse-policy URLs/review date, methodology, source record hash, exact ECB input rates and formula for derived cross-rates |
| `public_use_status`, `status`, `message_zh`, `context_zh` | Permission decision, observation state, Chinese availability message and deterministic fact sentence with value/date |

Missing source creates an unavailable row with null value/date and normalized reason. Malformed or future-dated official data fails closed for that source. A valid ECB response may populate three FX pairs while H.15 is unavailable, and conversely.

`source_timestamp` remains a **date-precision string** rather than an invented midnight UTC price timestamp. `age_seconds` uses local source-date midnight only as a conservative lower bound for age; freshness never becomes “current live”. `current` here means recently published **daily reference**. Fixed conservative thresholds: ECB 48 hours, H.15 72 hours; older values are `stale` with their value and date retained. Missing value is `unavailable`. There is no weekend/holiday threshold relaxation. On official nonpublication days the user sees “等待下一次官方更新” or “資料時間較舊”; retrieved-at refresh alone does not reset age.

## Source parsing and validation

ECB XML must contain one dated cube and positive finite USD, JPY and GBP rates, with no duplicate currency. Same-date operands and documented formulas are required. Cross-rates are rounded to eight decimal places using half-even rounding, with exact input rates retained. The H.15 HTML table parser selects the `Treasury constant maturities` → `Nominal` → `10-year` row and its latest nonempty dated cell. It rejects ambiguous rows, missing/duplicate dates, future observation/release dates, and release dates earlier than the selected observation; an `n.a.` cell is skipped while preserving the older source date. Its page is an official publication but an HTML layout change can make the adapter unavailable. HTTPS certificate verification stays enabled in production. Raw HTML/XML, headers and transport diagnostics never enter artifacts.

The collectors use independent request timeouts and failure isolation. No alternate provider, synthetic rate or retroactive reconstruction is permitted. A source URL is persisted for audit; raw response bytes are reduced to a SHA-256 provenance digest, not published.

## Public projection

`daily_market_reference.json` is the canonical validated artifact in `src/output`. `daily_market_reference_public.json` is the allowlisted projection in `docs/data`. Both currently contain four publicly permitted series values, but the projection removes internal validation and transport details, keeps attribution/formulas/date precision and is validated independently. Public file entries have fixed keys. `docs/data` publication must explicitly allowlist this new file; arbitrary files do not become publishable by sitting there.

The output includes short Chinese facts such as “美國 10 年期國債收益率的官方每日參考值為 4.96%（資料日期 2026-09-21）。” It does not change the existing Market Snapshot, Top Intelligence, AI prompt, rankings or Minimum Useful Gate. A future sentence may say “歐元兌美元較上一個**相同 ECB 參考序列**時點走弱” only after a separately validated comparable previous reference exists. “美國 10 年期國債收益率維持高位” requires an explicit historical basis and is not emitted merely from one value. No buy/sell/long/short vocabulary.

## Morning Report baseline

The existing Morning Report is fixed to 08:30 Asia/Taipei. Its production run starts at that time, so an on-demand fetch in that run cannot honestly be an 08:30 known-before-cutoff observation. A separate once-daily **pre-cutoff capture** is scheduled at 08:10 Taipei. A new capture may start only between 08:00 and 08:30 Taipei, preventing a delayed previous-day schedule from creating a next-day 00:05 baseline. It records the actual `captured_at`; only a completed validated capture with `captured_at <= 08:30` may be linked to that day's Morning Report. A delayed scheduled run after cutoff fails closed. The capture is a create-only dated public-safe checkpoint on the existing `morning-reports` branch, and a distinct create-only Morning sidecar binds it to the Morning `report_id`. The existing Morning checkpoint is unchanged. The published sidecar has no values if no valid pre-cutoff capture exists. Same-day later runs restore the winner byte-for-byte; next day uses a new date. This is a public branch and stores only the approved projection. Existing historical 08:30 baselines cannot be reconstructed.

The capture and sidecar both verify creator repository, main branch, workflow, SHA, file hash and single-create commit history. A rights or provenance failure suppresses publication. Actions artifacts are backups only, never the immutable date lock. The source date may be older than the capture date; this remains visible.

## Failure semantics and rollout

The daily source layer may be partial or unavailable without failing the existing intelligence pipeline. The Morning Report remains usable if reference capture is absent; its new sidecar is unavailable and must not invent a baseline. No per-user calls, no paid API, no new calendar/derivatives/AI logic. This phase stops before production deployment. A live workflow and checkpoint creation still need post-approval observation.
