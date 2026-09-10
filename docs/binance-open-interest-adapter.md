# Phase D-2 — Binance open interest shadow adapter

BTCUSDT and ETHUSDT USD-M perpetuals only. No production registration, evidence
bundle, intelligence, brief, UI, Telegram or deployment changes.

## Scope and units

Use public `GET /futures/data/openInterestHist` with `period=1h`, last 24 hours,
limit 30 and endTime at the frozen run-start cutoff. Select the latest returned
sample at/before that cutoff. This is sampled OI, not a streaming/current-tick
promise. Metadata comes from exchangeInfo; no fundingInfo request is required.
The official endpoint distinguishes `sumOpenInterest` from `sumOpenInterestValue`
and specifies millisecond period-end timestamps; see
[Binance OI statistics](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data).

Explicit versioned mapping `oi-1h-base-quantity-single-side-v1`:

| Provider field / instrument | Canonical meaning |
| --- | --- |
| BTCUSDT sumOpenInterest | native BTC quantity, unit=base_asset, base=asset:bitcoin |
| ETHUSDT sumOpenInterest | native ETH quantity, unit=base_asset, base=asset:ethereum |
| sumOpenInterestValue | Quote-notional field, retained in raw bytes only; never substituted for quantity |
| timestamp | native epoch milliseconds, no rounding/truncation |

The adapter retains the provider quantity without multiplying/dividing by two;
`single_side` denotes outstanding contracts once, not a long/short classification.
This is a source-definition mapping for these two linear instruments, not a unit
deduced from value magnitude or automatically generalized to inverse/other contracts.
The endpoint response does not carry a unit enum: the mapping is explicitly
versioned, with live/provider semantic review still required before promotion.
Metadata must match PERPETUAL, the expected BTC/ETH base, and USDT quote/margin;
inconsistent definitions fail closed. No currency conversion, funding inference,
positioning-change computation or market-wide aggregation occurs.

Reject missing/nonfinite/negative quantities, fractional/string/bool timestamps,
future or outside-request-window timestamps, wrong symbols, conflicting duplicate
timestamps and malformed payloads. Measured zero is valid; missing OI is never
zero. Freshness uses the existing 7200-second threshold. Stale source facts remain
stale, even when freshly retrieved. Selection is deterministic under input order.

## Existing boundaries reused

The funding adapter's bounded transport/collector and shadow receipt assembly
now expose explicit strategy hooks. Funding defaults and artifact output remain
unchanged; its existing tests are retained. OI uses a separate metric, endpoint
allowlist, normalization rule and wrapper `binance_oi_shadow_v1`. There are no
global monkeypatches, synthetic funding rows or schema workarounds.

The original-byte captures, hashes and metadata/measurement normalization
receipts are replayed by `validate_adapter_artifact`, then checked with the
existing production observation validator. Venue/instrument IDs are the same
logical namespace as funding; OI observation IDs explicitly include `oi` to avoid
collisions at identical timestamps. Revisions are pinned and content-derived.
No persistent cross-run first-seen history is introduced.

Raw capture timestamps for both metadata and OI feed known_at; normalized source
timestamps remain untouched. All raw/public schema separation and PIT limitations
of D-1 apply. Funding fields required by the shared definition are inactive
placeholders with funding_interval_seconds=null, never evidence of a funding event.

## Failure/security and artifact behavior

BTC failure does not discard ETH. Shared metadata failure makes dependent
symbols unavailable. Retry at most once for transient errors; 20-attempt/
120-second run budgets and one-request-per-second pacing are reused. Rate-limit,
access-denial and authentication responses stop the provider without bypass.
Neither API keys nor environment secrets are read. Error bodies/exception text
are not logged or written. No raw response is published: successful bytes are
private within the shadow wrapper, rejected by the public artifact validator.

Outer status covers the two requested OI cells; inner five-family coverage is
partial even when both succeed. If instrument metadata is unavailable, outer
symbol_status retains both symbols and inner instruments stay empty rather than
being fabricated. Provider failure still yields a valid unavailable artifact.

```sh
.venv/bin/python -m pytest tests/test_binance_open_interest.py tests/test_binance_funding_adapter.py
.venv/bin/python -m pytest
```

Future explicit manual live invocation:

```sh
.venv/bin/python -m src.shadow.derivatives.binance_open_interest --run-id oi-review-001
```

Writes only `outputs/shadow/derivatives/<run_id>/binance_oi_observations.json` via
the existing private, exclusive run directory and atomic writer. Existing run
directories are never overwritten. No live request was made during this phase;
tests use offline provider-shaped data. Stop for review before live validation.
