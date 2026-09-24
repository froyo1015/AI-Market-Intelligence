# Phase 14.1.1 — Derivatives provider recovery

Implemented native OKX funding/OI, explicit venue selection and reuse of existing observation/evidence/archive contracts. Two live GitHub Actions results are recorded below. No public product enablement.

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

## Live result — 2026-09-24

**Provider collection blocked; archive continuity ready; public product blocked.** The requested minimum of four valid non-Binance observations was not met. Both controlled runs completed the workflow safely, but neither acquired market measurements. The second run used the current documented REST host and got HTTP 403 at instrument metadata. Do not interpret workflow success as source success.

| Run | Commit | REST host | Collection | Archive entries |
| --- | --- | --- | --- | --- |
| [36015024779](https://github.com/froyo1015/AI-Market-Intelligence/actions/runs/36015024779) | `c79f1abb6b73c33b1ae244e24fb91afe0d2a2852` | www.okx.com | access_denied; exact HTTP not logged by initial candidate | 2 → 3 |
| [36015604555](https://github.com/froyo1015/AI-Market-Intelligence/actions/runs/36015604555) | `e590491126a63c6e32db14294b123318664b2be5` | openapi.okx.com | HTTP 403, access_denied | 3 → 4 |

The second run restored checkpoint artifact `10813798563` from the first. Its full `before_entry_hashes` list exactly equals the first run's `after_entry_hashes`. All prior hashes remain in the second after-list; each run added one distinct entry. The final archive has four same-day operational records (including Phase 14.1), **zero market facts**, and one observed UTC date. This proves failure-record continuity, not successful market-history accumulation. There is no fabricated observation or duplicated market fact; live deduplication of successful measurements remains unproven (fixtures pass).

Both funding and OI adapters encountered 403 on `metadata-BTC-USDT-SWAP`; each circuit breaker skipped later metric/ETH requests. Therefore all four metric statuses are unavailable, source/retrieval observation timestamps absent, and freshness unavailable. Do not report the funding-history or OI endpoints themselves as having returned 403: they were not reached. Funding/OI normalization, source timestamp semantics and receipt preservation are fixture-validated but cannot yet be confirmed with successful Actions measurements.

Encrypted checkpoint bytes grew from 106,708 to 142,126 (+35,418), primarily storing run/evidence context and failure records. These are not successful-data storage estimates. Both are PGP-encrypted; plaintext was not downloaded. Both operational proof and public projection pass their closed validators. All four public values are null, `production_enabled=false`, and no UI/Pages publication was added. Artifact hashes and exact proof are in [okx-live-validation.json](okx-live-validation.json).

## Validation and remaining boundary

Final full local Python suite: **691 passed, 1 skipped**, with the existing urllib3/LibreSSL environment warning. The skip is local GnuPG availability. Both live Actions runs passed their full tracked test suite and real GnuPG restore/seal steps. Workflow YAML, diff checks, downloaded file hashes, report consistency and closed public-artifact safety checks pass. Real cryptography ran in Actions despite the local skip.

No region/proxy rotation or access-control bypass was attempted. CCXT wrapping OKX or Binance would retain the same venue restrictions. Bybit remains documentation-only and has unresolved product rights; no approved third venue was added. Stop here for review rather than claim source recovery. A next authorized source or execution route must resolve both access and the intended-use rights independently. Historical calibration and public product readiness remain blocked.

GitHub emitted non-fatal notices about Node 20 actions being run on Node 24 and a future ubuntu-latest image migration. Updating action versions is outside this recovery result; the tested runs succeeded.
