# Phase D-1 — Binance funding adapter v1

Standalone shadow adapter for BTCUSDT and ETHUSDT USD-M perpetuals only. No
production integration, evidence bundle, intelligence, UI or notification changes.
No API key is required or read; `SecretAccess` is deliberately unused. Tests
use artificial official-shaped responses, not claims of successful live access.

## Endpoints and semantics

Fixed host `https://fapi.binance.com`, GET only: exchangeInfo, fundingInfo and
fundingRate. History query is bounded to the preceding 72 hours, limit 1000,
ending at the frozen requested cutoff. Select the latest settled regular funding
record; preserve every original response byte, native timestamp and decimal text.
Reject conflicting duplicates, wrong symbols/types and future observations.

Official funding history defines millisecond fundingTime and fundingRate;
fundingInfo reports adjusted intervals and shares the documented 500/5min/IP
budget with funding history. See [official market-data contracts](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data).
For symbols absent from fundingInfo, use the documented default eight hours,
and always require the final two settlements to agree with the selected interval.
An interval mismatch is unavailable, not guessed. This conservative check can
reject a valid settlement during interval transitions. See
[Binance funding interval policy](https://www.binance.com/en/support/faq/detail/360033525031).

## Bridge and provenance

The existing production validator expects an explicit normalized definition and
metric fields, not native exchange JSON. `binance_funding_shadow_v1` therefore
wraps (1) original captures encoded losslessly in base64 with SHA-256, endpoint
and capture time, (2) versioned normalization receipts linking all three inputs,
(3) normalized receipt bytes and (4) the existing observation output contract.
`validate_adapter_artifact` reconstructs the complete bridge from original
captures and compares it before invoking the existing production validator.
Never validate only the inner output as proof of Binance provenance.

Native decimal trailing zeros are normalized exactly; timestamp milliseconds
are never truncated. Instrument IDs remain venue+symbol-specific; observation
IDs remain venue+symbol+settlement-specific. Immutable revision tokens are
content-derived positive integers, not chronological counters. A changed
capture/generation creates a revision, not a new logical fact. No cross-run
first-seen store or correction history is implemented; captures support only
their actual evaluation cutoff, not retroactive knowledge.

Definitions are bounded to the observed settlement's one-millisecond identity
window, not asserted valid for the whole contract history. Metadata known_at
includes exchangeInfo, fundingInfo and funding history receipt times. OI fields
in the shared definition are reserved defaults for this funding-only mapping;
they do not authorize OI collection or interpretation.

## Failure and security behavior

Bad BTC data does not discard valid ETH data. Metadata failure makes dependent
symbols unavailable. HTTP 401/403/451, redirects and rate bans stop the provider
without bypass or retry. Rate limits are not retried in the same run, which
avoids retrying before Retry-After. Timeouts/network/5xx retry at most once.
20 attempts, one request/second, 120-second overall budget and 10-second socket
timeout; response bodies cap at 2 MiB. Elapsed deadlines are checked between
reads/calls; a blocking socket operation may last until its timeout. No proxy
environment, cookies, auth headers, arbitrary host or redirects are used.

Error bodies are neither read nor logged. Application error objects are discarded.
No raw exception strings enter artifacts. Original successful public responses
remain private within the shadow wrapper; base64 is encoding, NOT redaction or
encryption. The public artifact validator rejects this entire artifact type.
The adapter never reads local secrets, but cannot certify that a remote public
response contains no sensitive third-party text. No shadow captures are published.

Outer status is available for two successful funding observations, partial for
one, unavailable for none. This differs from inner five-family coverage, which
remains partial even on success. When metadata is unavailable, the inner registry
stays empty rather than fabricating instruments; outer symbol_status explicitly
retains both requested symbols. A failed provider still produces a valid shadow
artifact with no fake observations.

## Run and review

Offline tests:

```sh
.venv/bin/python -m pytest tests/test_binance_funding_adapter.py
.venv/bin/python -m pytest
```

Manual live invocation (network access required; not scheduled):

```sh
.venv/bin/python -m src.shadow.derivatives.binance_funding --run-id funding-review-001
```

Writes only `outputs/shadow/derivatives/<run_id>/binance_funding_observations.json`.
Run IDs cannot contain paths; existing run directories are not overwritten;
publication uses a private run directory and atomic final rename. It creates no
new production CLI registration or workflow. This implementation was tested
offline; geographic access, redistribution terms and live API behavior remain
operational review gates. No live request or deployment is implied by tests.
