"""Bounded OKX public USDT perpetual observations; private shadow only."""

import base64
import re
from decimal import Decimal

from . import binance_funding as shared
from .production_validator import validate_output, milliseconds
from .provider_security import FailureCode
from .validator import require

PROVIDER = "okx"
SYMBOLS = {"BTC-USDT-SWAP": "bitcoin", "ETH-USDT-SWAP": "ethereum"}
REFS = {s: "instrument:okx-" + s.lower() + "@1" for s in SYMBOLS}
PROVIDER_SPEC = (PROVIDER, "source:okx", "OKX", "venue:okx", SYMBOLS,
                 "instrument:okx-", "derivatives:observation:okx-")


def endpoints(metric):
    result = {}
    for s in SYMBOLS:
        result["metadata-" + s] = "/api/v5/public/instruments"
        if metric == "funding_rate":
            result["schedule-" + s] = "/api/v5/public/funding-rate"
        result[s] = "/api/v5/public/" + ("funding-rate-history" if metric == "funding_rate" else "open-interest")
    return result


class FundingTransport(shared.PublicTransport):
    host = "https://www.okx.com"
    endpoints = endpoints("funding_rate")

    def query(self, name, cutoff):
        if name.startswith("metadata-"):
            return {"instType": "SWAP", "instId": name[len("metadata-"):]}
        if name.startswith("schedule-"):
            return {"instId": name[len("schedule-"):]}
        if self.endpoints[name].endswith("open-interest"):
            return {"instType": "SWAP", "instId": name}
        return {"instId": name, "limit": "10"}


class OITransport(FundingTransport):
    endpoints = endpoints("open_interest")


def timestamp(value):
    require(isinstance(value, str) and re.fullmatch(r"[0-9]{13}", value), "invalid native milliseconds")
    return int(value)


def rows(document):
    require(isinstance(document, dict) and document.get("code") == "0"
            and isinstance(document.get("data"), list), "invalid OKX response")
    return document["data"]


def single(document, symbol):
    data = rows(document)
    require(len(data) == 1 and isinstance(data[0], dict) and data[0].get("instId") == symbol,
            "ambiguous OKX instrument")
    return data[0]


def normalize(symbol, documents, cutoff, metric):
    meta = single(documents["metadata-" + symbol], symbol)
    base = symbol.split("-")[0]
    require(meta.get("instType") == "SWAP" and meta.get("ctType") == "linear"
            and meta.get("settleCcy") == "USDT" and meta.get("uly") == base + "-USDT"
            and meta.get("ctValCcy") == base and meta.get("state") == "live",
            "wrong OKX contract")
    require(Decimal(shared.canonical(meta.get("ctVal"))) > 0, "invalid contract value")
    # Retain native definition instead of inventing a cross-venue conversion.
    unit_metadata = {k: meta.get(k) for k in ("ctVal", "ctMult", "ctValCcy", "ctType", "settleCcy")}
    hours, extra = None, {"unit_metadata": unit_metadata}
    if metric == "funding_rate":
        data = rows(documents[symbol])
        require(2 <= len(data) <= 10, "insufficient settlements")
        values = {}
        for row in data:
            require(isinstance(row, dict) and row.get("instId") == symbol and row.get("instType") == "SWAP",
                    "wrong funding instrument")
            t = timestamp(row.get("fundingTime"))
            require(t <= cutoff, "future settlement")
            value = shared.canonical(row.get("realizedRate"))
            require(t not in values or values[t] == value, "conflicting settlements")
            values[t] = value
        times = sorted(values)
        require(len(times) >= 2, "insufficient distinct settlements")
        interval_ms = times[-1] - times[-2]
        require(3600000 <= interval_ms <= 86400000 and interval_ms % 3600000 == 0,
                "invalid historical settlement interval")
        hours = interval_ms // 3600000
        t, value = times[-1], values[times[-1]]
        schedule = single(documents["schedule-" + symbol], symbol)
        funding_time = timestamp(schedule.get("fundingTime"))
        next_time = timestamp(schedule.get("nextFundingTime"))
        require(funding_time < next_time and 3600000 <= next_time - funding_time <= 86400000,
                "invalid prospective funding schedule")
        extra.update(value_field="realizedRate", timestamp_semantics="settlement_time",
                     previous_settlement_time=times[-2], next_schedule={
                         "funding_time_ms": funding_time, "next_funding_time_ms": next_time,
                         "interval_seconds": (next_time - funding_time) // 1000,
                         "applies_to_settled_observation": False})
    else:
        row = single(documents[symbol], symbol)
        require(row.get("instType") == "SWAP", "wrong OI type")
        t, value = timestamp(row.get("ts")), shared.canonical(row.get("oi"))
        require(t <= cutoff and Decimal(value) >= 0, "invalid OI observation")
        for key in ("oiCcy", "oiUsd"):
            extra[key] = shared.canonical(row.get(key))
            require(Decimal(extra[key]) >= 0, "invalid OI denomination")
        extra.update(value_field="oi", timestamp_semantics="provider_data_return_time",
                     native_unit="contracts", conversion_applied=False)
    definition = {"venue_id": "venue:okx", "native_symbol": symbol, "instrument_type": "perpetual",
                  "base_asset_id": "asset:" + SYMBOLS[symbol], "quote_asset_id": "asset:usdt",
                  "settlement_asset_id": "asset:usdt", "underlying_asset_id": "asset:" + SYMBOLS[symbol],
                  "oi_unit": "contracts", "counting_basis": "single_side",
                  "funding_interval_seconds": hours * 3600 if hours else None,
                  "funding_rate_kind": "settled", "funding_sign_convention": "positive_long_pays_short",
                  "effective_from": shared.utc_ms(t), "effective_to": shared.utc_ms(t + 1)}
    return definition, {"metric": metric, "symbol": symbol, "value": value, "time": t,
                        "provider_metadata": extra}


def assemble(run_id, started, evaluated, captures, failures, metric):
    require(metric in ("funding_rate", "open_interest"), "unsupported OKX metric")
    deps = lambda s: ("metadata-" + s,) + (("schedule-" + s,) if metric == "funding_rate" else ())
    spec = (endpoints(metric), lambda s, docs, cutoff: normalize(s, docs, cutoff, metric), deps,
            metric, "okx_" + metric + "_shadow_v1", "okx-" + metric + "-normalization-v1",
            "settled-realized-history-interval" if metric == "funding_rate" else "native-contract-count-no-conversion")
    # as-of means acquisition completion, not request start. Receipt timestamps
    # still bound each observation; nothing is backdated to the start of a run.
    return shared.assemble(run_id, evaluated, evaluated, captures, failures, spec=spec,
                           provider_spec=PROVIDER_SPEC, collection_started_at=started)


def validate_adapter_artifact(artifact):
    contracts = {"okx_funding_rate_shadow_v1": "funding_rate", "okx_open_interest_shadow_v1": "open_interest"}
    metric = contracts.get(artifact.get("schema_contract"))
    require(metric is not None, "unsupported OKX contract")
    expected = assemble(artifact["run_id"], artifact["collection_started_at"], artifact["evaluation_cutoff"],
                        artifact["captures"], artifact["fetch_failures"], metric)
    require(artifact == expected, "OKX normalization bridge mismatch")
    raw = {p: base64.b64decode(b, validate=True) for p, b in artifact["normalized_bytes"].items()}
    return validate_output(artifact["observation_output"], raw)


class OKXFundingAdapter(shared.BinanceFundingAdapter):
    provider_id = PROVIDER
    instrument_refs = REFS
    endpoints = endpoints("funding_rate")
    transport_type = FundingTransport

    def response_failure(self, parsed):
        if not isinstance(parsed, dict):
            return FailureCode.INVALID_RESPONSE
        code = parsed.get("code")
        if code == "0" and isinstance(parsed.get("data"), list):
            return None
        if code in ("50011", "50040"):
            return FailureCode.RATE_LIMITED
        if code in ("50119", "50120", "50035"):
            return FailureCode.ACCESS_DENIED
        return FailureCode.PROVIDER_ERROR if code in ("50001", "50004", "50013", "50026") else FailureCode.INVALID_RESPONSE

    def build(self, *args):
        return assemble(*args, self.metric)

    validate = staticmethod(validate_adapter_artifact)


class OKXOpenInterestAdapter(OKXFundingAdapter):
    metric = "open_interest"
    endpoints = endpoints("open_interest")
    transport_type = OITransport
