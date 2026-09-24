# Phase 14.1.1 — Derivatives provider recovery

Implementation candidate: native OKX funding/OI, explicit venue selection, existing observation/evidence/archive contracts. Live GitHub Actions results will be recorded below. No public product enablement.

Initial diagnostic run `36015024779` on `c79f1abb6b73c33b1ae244e24fb91afe0d2a2852` successfully restored the latest two-entry checkpoint, but `www.okx.com` was classified access_denied. Subsequent inspection of the official v5 **Production Trading Services** documentation established that the designated REST host is now `https://openapi.okx.com`. The adapter was corrected to this one documented host before recovery trials. No regional endpoint, proxy or host-rotation fallback is used. The initial failure is retained and is not counted as a successful collection trial.

## Minimum architecture changes

The old adapter boundary was nominally neutral, but collection, evidence coverage and shadow evaluation assumed Binance instrument IDs. A closed provider registry now validates the matching provider/metric contract and determines venue-specific coverage. Binance replay retains its original normalized representation. OKX wrappers carry their collection start separately; snapshot cutoff is acquisition completion so current OI is not backdated to request start. Every measurement must precede its receipt capture and as-of cutoff.

The existing transport budget, denial circuit breaker, receipt hashing, observation validator, evidence fact identity, archive append/replay and GPG sealing are reused. The canonical schemas and archive format are unchanged. A single bundle may not mix venues. No statistical aggregation, thresholds or directional interpretation is added.

One real discovery defect was found: prior checkpoint `10795666983` was created at 07:28:51Z and `10795204597` at 07:32:49Z on 2026-09-24. Descending ID would pick the older checkpoint. Discovery now sorts creation timestamps, then verifies successful workflow, repository and branch before restoring. Storage itself is unchanged.

## Data semantics

Funding uses OKX history `realizedRate`, millisecond settlement `fundingTime`, and the actual interval between the latest two settlements. Predicted `fundingRate` is rejected as a substitute. Prospective `fundingTime/nextFundingTime` is retained separately in private normalization metadata. A missing or malformed required field makes only that symbol unavailable unless the provider denies access.

OI uses OKX `oi` in **contracts**, with private `oiCcy`, `oiUsd`, contract value/currency/multiplier metadata. Its `ts` is a data-return timestamp, not an exchange execution timestamp. No Binance base-quantity conversion is inferred. BTC/ETH refer only to OKX USDT-settled linear perpetuals.

Official definitions: [funding history](https://www.okx.com/docs-v5/en/#public-data-rest-api-get-funding-rate-history), [open interest](https://www.okx.com/docs-v5/en/#public-data-rest-api-get-open-interest). Historical funding is documented up to three months; current OI is a snapshot. Polling does not create full historical OI coverage.

## CCXT evaluation

Evaluate only OKX, Binance USD-M and Bybit. All expose funding/history and OI through documented CCXT methods; actual availability must be checked per exchange/version. CCXT-OKX is the same source, not redundancy. Bybit could provide venue redundancy but is not approved or live-tested; rights/access must pass independently.

CCXT supplies unified millisecond timestamps and symbol IDs, but applications still need native instrument ID, venue, settlement currency, linear/inverse type, `contractSize`, interval, settled-versus-projected funding, OI amount-versus-notional definitions and original source field. Floating-point normalization and raw `info` require care. Do not install it merely to wrap two existing GET adapters, and do not assume its unified funding field means realized settlement. Use exchange-specific raw fields with private receipts if a client adapter is later added.

Direct review of [CCXT's OKX implementation](https://github.com/ccxt/ccxt/blob/master/python/ccxt/okx.py) on 2026-09-24 confirms `fetch_funding_rate_history` selects `realizedRate` and integer fundingTime without second rounding. Its optional automatic pagination uses an `8h` interval, so leave pagination off and validate actual settlement intervals. `parse_open_interest` maps `oi` to openInterestAmount, `oiUsd` to openInterestValue and retains `oiCcy` separately; the unified amount is not automatically coin quantity. Preserve native decimal strings instead of relying on a float roundtrip.

## HKUDS/Vibe-Trading reference audit

Reviewed main commit `a65427a3d587e43cd5c7541948b36524e8fd2f12` using read-only GitHub source access:

- `agent/backtest/loaders/okx.py`: bounded requests/retries, business-code checks. Useful pattern; its optional proxy configuration is not adopted.
- `agent/backtest/loaders/ccxt_loader.py`: bounded funding-history pagination and explicit instrument handling. Its funding timestamp `.round("s")`, fixed 00/08/16 settlement schedule and zero filling do not fit our millisecond/PIT evidence contract and are not reused.
- `agent/src/market_data.py` and `agent/src/tools/market_data_tool.py`: served-source provenance and bounded fallback are useful. The broad OHLCV fallback chain is not a derivatives venue-equivalence policy.
- `agent/src/skills/okx-market/references/合约行情/历史资金费率.md`: describes both fields, but example aggregates `fundingRate`; this adapter explicitly uses `realizedRate` instead.
- `agent/src/skills/okx-market/references/合约行情/持仓量.md`: endpoint/field reference only. No trend-continuation, crowded-position or trading rule is copied.

[Reference repository](https://github.com/HKUDS/Vibe-Trading/tree/a65427a3d587e43cd5c7541948b36524e8fd2f12). No third-party source was modified.

## Historical accumulation and limits

Each successful run contributes at most four observations: BTC/ETH latest settled funding and BTC/ETH current OI. Same settlement revisits are deduplicated as evidence facts while receipts remain traceable; a new OI timestamp is a new fact. Repeated same-day runs do not add independent history days. Provider switches start separate venue series and must be calibrated separately.

The existing daily cadence would yield at most four selected observations/day (about 120 run-observations over 30 days), not every funding settlement or all hourly OI. Byte growth depends on private captured payload sizes. Missing days remain gaps, unsuccessful runs remain archived, and no interpolation or retroactive PIT reconstruction is allowed. Current seven-day operational readiness is not a statistical calibration requirement. No percentile threshold is defined.

Scheduled provider remains Binance while OKX is selected only for controlled recovery runs. See [fallback design](derivatives-source-fallback-design.md) and [rights gate](derivatives-rights-gate-v2.md).
