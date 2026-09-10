"""BTC/ETH USD-M perpetual OI statistics; shadow-only, no keys or consumers."""

import argparse
import base64
from decimal import Decimal

from . import binance_funding as shared
from .production_validator import validate_output
from .provider_security import ProviderRequest, EnvironmentSecretAccess
from .validator import require

ENDPOINTS = {"exchange": "/fapi/v1/exchangeInfo", "BTCUSDT": "/futures/data/openInterestHist",
             "ETHUSDT": "/futures/data/openInterestHist"}


class OpenInterestTransport(shared.PublicTransport):
    endpoints = ENDPOINTS

    def query(self, name, cutoff):
        return {"symbol": name, "period": "1h", "startTime": max(0, cutoff - 24 * 3600000),
                "endTime": cutoff, "limit": 30} if name in shared.SYMBOLS else {}


def normalize(symbol, documents, cutoff):
    exchange = documents["exchange"]
    require(isinstance(exchange, dict) and isinstance(exchange.get("symbols"), list), "invalid exchange metadata")
    matches = [s for s in exchange["symbols"] if isinstance(s, dict) and s.get("symbol") == symbol]
    require(len(matches) == 1, "ambiguous instrument")
    meta = matches[0]
    require(meta.get("contractType") == "PERPETUAL" and meta.get("baseAsset") == symbol[:-4] and
            meta.get("quoteAsset") == meta.get("marginAsset") == "USDT", "wrong instrument/unit mapping")
    rows = documents[symbol]
    require(isinstance(rows, list) and 1 <= len(rows) <= 30, "empty/invalid OI history")
    values = {}
    for row in rows:
        require(isinstance(row, dict) and row.get("symbol") == symbol, "invalid OI symbol")
        t = row.get("timestamp")
        require(type(t) is int and max(0, cutoff - 24 * 3600000) <= t <= cutoff, "invalid OI timestamp")
        # Quantity, never sumOpenInterestValue (quote notional). No x2 or /2.
        value = shared.canonical(row.get("sumOpenInterest"))
        require(Decimal(value) >= 0, "negative OI")
        require(t not in values or values[t] == value, "conflicting OI records")
        values[t] = value
    t = max(values)
    definition = {"venue_id": "venue:binance-usdm", "native_symbol": symbol, "instrument_type": "perpetual",
                  "base_asset_id": "asset:" + shared.SYMBOLS[symbol], "quote_asset_id": "asset:usdt",
                  "settlement_asset_id": "asset:usdt", "underlying_asset_id": "asset:" + shared.SYMBOLS[symbol],
                  "oi_unit": "base_asset", "counting_basis": "single_side", "funding_interval_seconds": None,
                  "funding_rate_kind": "settled", "funding_sign_convention": "positive_long_pays_short",
                  "effective_from": shared.utc_ms(t), "effective_to": shared.utc_ms(t + 1)}
    return definition, {"metric": "open_interest", "symbol": symbol, "value": values[t], "time": t}


def assemble(*args):
    return shared.assemble(*args, spec=(ENDPOINTS, normalize, ("exchange",), "open_interest",
        "binance_oi_shadow_v1", "binance-oi-normalization-v1", "oi-1h-base-quantity-single-side-v1"))


def validate_adapter_artifact(a):
    expected = assemble(a["run_id"], a["requested_cutoff"], a["evaluation_cutoff"], a["captures"], a["fetch_failures"])
    require(a == expected, "OI normalization bridge mismatch")
    raw = {p: base64.b64decode(b, validate=True) for p, b in a["normalized_bytes"].items()}
    return validate_output(a["observation_output"], raw)


class BinanceOpenInterestAdapter(shared.BinanceFundingAdapter):
    metric = "open_interest"
    endpoints = ENDPOINTS
    transport_type = OpenInterestTransport
    build = staticmethod(assemble)
    validate = staticmethod(validate_adapter_artifact)


def write_shadow_artifact(artifact):
    return shared.write_shadow_artifact(artifact, validator=validate_adapter_artifact,
                                         filename="binance_oi_observations.json")


def main():
    parser = argparse.ArgumentParser(description="BTC/ETH OI statistics; internal shadow only")
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    adapter = BinanceOpenInterestAdapter(args.run_id)
    adapter.collect(ProviderRequest(shared.PROVIDER, tuple(shared.REFS.values()), ("open_interest",)),
                    EnvironmentSecretAccess(set()))
    write_shadow_artifact(adapter.artifact)
    print(adapter.artifact["status"])


if __name__ == "__main__":
    main()
