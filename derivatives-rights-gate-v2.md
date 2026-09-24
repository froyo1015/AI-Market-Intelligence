# Phase 14.1.1 — Derivatives source rights gate v2

Reviewed 2026-09-24. Scope: BTC/ETH perpetual funding and open interest. Technical recovery and a data licence are separate decisions. **Public product remains blocked.** No value, derived market description or raw receipt is released by this recovery workflow; only encrypted history and closed operational metadata are uploaded.

| Use | OKX public API | Binance USD-M API | CCXT using OKX / Binance / Bybit |
| --- | --- | --- | --- |
| API access | Documented unauthenticated public GET endpoints; regional domain rules apply | Documented public endpoints; prior Actions trial access_denied | Library reaches the same venue; cannot cure venue restrictions |
| Internal use | Personal/non-commercial account use is limited by agreement; this product's general research/analytics use is not affirmatively licensed | Applicable entity/product permission remains unclear | Inherits actual venue restrictions |
| Public raw display | blocked without written OKX permission | unclear; blocked by this gate | No independent CCXT data licence |
| Derived display | no safe exemption established; blocked for this product | unclear | Inherits underlying data terms |
| Redistribution/downloadable JSON | blocked without written permission | unclear | No bypass through normalized fields |
| Attribution | Source/venue retained for traceability; attribution alone does not authorize use | same; exact licence duty unresolved | Preserve venue plus client version; software attribution distinct from data rights |
| Commercial restrictions | Prior authorization required; analytics-platform/competing-data restrictions also apply | No permission established for intended product | Bybit's terms restrict repackaging/resale and commercial exploitation |
| Classification | **blocked** for public/product use; limited internal-use conditions are not a product licence | **unclear**, therefore public gate blocked | **blocked/unclear** according to venue; not approved fallback |

## Exact documents and implications

[OKX API Agreement](https://www.okx.com/help/okx-api-agreement), sections 9.2–9.4, restricts market data use and applies the restrictions to unauthenticated endpoints too. Public display/redistribution needs written consent. It also restricts competing analytics products and certain third-party AI uses. A two-run encrypted technical trial does not establish permission for continued product research, public metrics, or commercial deployment. Re-review written permission before expanding collection or use. No paid purchase is recommended by this review.

[OKX API documentation](https://www.okx.com/docs-v5/en/) documents access and field semantics, not a redistribution grant. Do not switch regional domains or proxies to evade a denial. The current trial uses only the normal documented public host.

[Binance general terms](https://www.binance.com/en/terms) and [official USD-M developer catalog](https://developers.binance.info/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data) do not establish an affirmative licence for this product's public raw metrics, derived text or downloads in this review. Do not transfer a historical Binance Vision dataset licence to live REST endpoints or assume a regional entity's terms apply universally.

[Bybit API terms](https://www.bybit.com/en/help-center/article/API-Terms) link the [API agreement PDF](https://www.bybit.com/common-static/compliance/legal/BYBIT/df1923006718fbba8ba70d7d762b9866.pdf). Clauses 6.7–6.9 restrict repackaging/reselling and commercial exploitation. Bybit is a documentation-only redundancy candidate, not live-tested or enabled here.

[CCXT manual](https://docs.ccxt.com/docs/manual) and [OKX methods](https://docs.ccxt.com/docs/exchanges/okx) describe a client library. Its software licence cannot grant exchange market-data rights. `info` is raw venue data and remains private; normalization does not remove its rights obligations.

## Enforced boundary

The scheduler withholds all four numerical measurements from the legacy public projection regardless of technical success. The new closed recovery proof carries provider, instrument, metric, timestamps, freshness and validation results, but excludes rates, quantities, raw responses, receipt content, headers and credentials. Only existing GPG-encrypted checkpoints hold replay data. The UI is not connected and `production_enabled=false` is unchanged.

Future publication needs a reviewed, per-provider/per-use rights grant. Current success cannot change this gate automatically. Wording must remain venue-scoped, e.g. `OKX BTC 永續合約資金費率`, never a claim about global BTC funding or total market OI.
