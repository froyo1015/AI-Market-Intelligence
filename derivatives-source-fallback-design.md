# Phase 14.1.1 — Derivatives source routing and fallback

Only the existing shadow namespace participates. The canonical observation and evidence schemas, encrypted checkpoint format, archive append/replay implementation and production consumers remain unchanged.

## Provider boundary

`ProviderRequest → bounded HTTPS GET → private capture → deterministic normalization → ProductionObservation → existing evidence/archive`.

Binance USD-M remains registered. Add OKX linear USDT-settled `BTC-USDT-SWAP` and `ETH-USDT-SWAP`. CCXT is an evaluated client abstraction, not an independent venue or a way to evade an exchange denial. A future CCXT adapter must declare both client and actual venue and pass the same replay validator.

The run explicitly selects one venue for both metrics and both assets. Partial coverage stays partial; this recovery does not silently fill an OKX slot with Binance. Each source artifact and evidence identity includes provider/venue/native instrument. Different venues never share a history distribution or get averaged.

## Deterministic policy

For controlled validation select OKX explicitly. Scheduled default remains Binance until recovery/rights review. An approved future automatic route may try OKX first, then Binance only if the whole primary result is unavailable, then return unavailable. Partial primary results remain primary. CCXT/Bybit is not an enabled route; no approved third venue exists. An access-denied/rate-limit/authentication response stops that provider's requests with a fixed failure code. No proxies, host rotation, geo-routing, credentials or repeated access-denied retries.

Each route attempt must preserve failures and `served_provider`; a provider switch is a new venue series. Normalization/validation failures must never be presented as successful fallback. Per adapter: at most 20 requests including one transient retry, 1 request/second, 10-second request timeout, 120-second deadline, bounded response size.

Live review result: OKX's currently documented `openapi.okx.com` returned HTTP 403 on Actions run `36015604555`, while Binance previously returned access_denied. Consequently no automatic priority chain is approved on reliability evidence. `[OKX, Binance]` above is a proposal only; the enabled behavior remains explicit selection and an honest unavailable result. A CCXT wrapper of a denied venue is not a recovery route. No further same-host retries were run after the corrected-host denial.

## OKX mapping

Use public instruments, funding-rate-history, funding-rate and open-interest endpoints. Funding uses **realizedRate**, the most recent completed settlement, and its millisecond fundingTime; predicted fundingRate is never substituted. Adjacent settlements establish the observed historical interval. Current fundingTime/nextFundingTime is retained separately as future schedule metadata, never retroactively assigned to a settled observation.

OI uses `oi`, explicitly in **contracts**; preserve `oiCcy`, `oiUsd`, `ctVal`, `ctMult`, `ctValCcy`, `ctType` in private normalized receipt metadata. No conversion/averaging with Binance base-asset OI. The source `ts` is the provider's data-return time, not a trade timestamp. Acquisition finishes before the as-of snapshot cutoff; no timestamp may exceed its receipt capture or the cutoff. Preserve all milliseconds.

## Publication and continuity

Rights are fail-closed: publish only a closed operational proof and an unavailable metric projection until public display is approved. Values/raw responses/receipts remain inside the existing encrypted checkpoint; no Pages integration. `production_enabled=false` always.

Checkpoint discovery uses artifact creation time (IDs were demonstrably non-monotonic), trusted workflow/repository/branch and successful runs. This corrects discovery ordering without changing storage. Record before/after entry hashes and observation-identity hashes in operational proof to detect history loss. Repeated settled funding observations retain provenance but represent the same fact; OI with a new source timestamp is a new fact. Two runs do not establish two independent days.
