"""Closed venue registry. Client wrappers never become market-data venues."""

from . import binance_funding, binance_open_interest, okx
from .validator import require

CONTRACTS = {
    "binance_funding_shadow_v1": ("binance_usdm", "funding_rate", binance_funding.validate_adapter_artifact),
    "binance_oi_shadow_v1": ("binance_usdm", "open_interest", binance_open_interest.validate_adapter_artifact),
    "okx_funding_rate_shadow_v1": ("okx", "funding_rate", okx.validate_adapter_artifact),
    "okx_open_interest_shadow_v1": ("okx", "open_interest", okx.validate_adapter_artifact),
}
VENUES = {
    "binance_usdm": {s: "instrument:binance-usdm-" + s.lower() for s in binance_funding.SYMBOLS},
    "okx": {s: "instrument:okx-" + s.lower() for s in okx.SYMBOLS},
}


def validate_source(artifact, metric):
    registration = CONTRACTS.get(artifact.get("schema_contract"))
    require(registration is not None, "unregistered provider contract")
    provider, registered_metric, validator = registration
    require(artifact.get("provider_id") == provider and registered_metric == metric,
            "provider/metric contract mismatch")
    require(validator(artifact).valid, "invalid source artifact")


def scope(artifacts):
    providers = {a["provider_id"] for a in artifacts}
    require(providers <= set(VENUES) and len(providers) <= 1, "mixed/unregistered venue scope")
    # Preserve exact legacy empty-bundle replay semantics.
    return VENUES[next(iter(providers)) if providers else "binance_usdm"]


def slots(artifacts):
    return {(instrument, metric) for instrument in scope(artifacts).values()
            for metric in ("funding_rate", "open_interest")}


def adapters(provider, run_id):
    require(provider in VENUES, "unregistered provider")
    classes = ((okx.OKXFundingAdapter, okx.OKXOpenInterestAdapter) if provider == "okx" else
               (binance_funding.BinanceFundingAdapter, binance_open_interest.BinanceOpenInterestAdapter))
    return tuple(cls(run_id + suffix) for cls, suffix in zip(classes, ("-funding", "-oi")))
