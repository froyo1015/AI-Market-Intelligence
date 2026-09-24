"""Closed contracts for daily official reference observations and projections."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, time, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
from zoneinfo import ZoneInfo

VERSION = "daily_market_reference_v1"
CAPTURE_VERSION = "daily_reference_capture_v1"
MORNING_VERSION = "morning_daily_reference_v1"
ASSETS = ("US10Y", "EURUSD", "USDJPY", "GBPUSD")
DETAILS = {
    "US10Y": ("rates", "fed_h15_nominal_treasury_10y", "percent_per_annum", "America/New_York"),
    "EURUSD": ("fx", "ecb_usd_per_eur", "USD_per_EUR", "Europe/Berlin"),
    "USDJPY": ("fx", "ecb_jpy_per_eur_div_usd_per_eur", "JPY_per_USD", "Europe/Berlin"),
    "GBPUSD": ("fx", "ecb_usd_per_eur_div_gbp_per_eur", "USD_per_GBP", "Europe/Berlin"),
}
MAX_AGE_SECONDS = {"US10Y": 72 * 3600, "EURUSD": 48 * 3600,
                   "USDJPY": 48 * 3600, "GBPUSD": 48 * 3600}
PUBLIC_ASSET_KEYS = frozenset({
    "asset_id", "symbol", "asset_class", "series_id", "reference_value", "unit",
    "source", "source_url", "source_timestamp", "timestamp_precision",
    "reference_period", "timezone", "release_date", "retrieved_at", "freshness",
    "provenance", "public_use_status", "status", "message_zh", "context_zh",
})
PUBLIC_KEYS = frozenset({"version", "reference_kind", "generated_at", "status", "assets"})


def utc(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp required")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("aware timestamp required")
    return parsed.astimezone(timezone.utc)


def stamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_bytes(value: dict) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode()


def digest(value: dict) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _date(value: str) -> date:
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError("date precision required")
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("invalid date")
    return parsed


def context_for(key: str, value: str | None, period: str | None) -> str:
    if value is None or period is None:
        return "資料暫不可用。"
    if key == "US10Y":
        return f"美國 10 年期國債收益率的官方每日參考值為 {value}%（資料日期 {period}）。"
    name = {"EURUSD": "歐元兌美元", "USDJPY": "美元兌日圓", "GBPUSD": "英鎊兌美元"}[key]
    kind = "ECB 參考匯率" if key == "EURUSD" else "ECB 交叉參考匯率"
    return f"{name}的{kind}為 {value}（資料日期 {period}）。"


def validate(payload: dict, *, public: bool = False) -> None:
    if not isinstance(payload, dict) or set(payload) != PUBLIC_KEYS:
        raise ValueError("invalid reference envelope")
    if payload["version"] != VERSION or payload["reference_kind"] != "official_daily_reference":
        raise ValueError("invalid reference identity")
    generated = utc(payload["generated_at"])
    if not isinstance(payload["assets"], list) or any(not isinstance(a, dict) for a in payload["assets"]) or [a.get("asset_id") for a in payload["assets"]] != list(ASSETS):
        raise ValueError("invalid reference assets")
    states = []
    for asset in payload["assets"]:
        if set(asset) != PUBLIC_ASSET_KEYS or asset["symbol"] != asset["asset_id"]:
            raise ValueError("invalid reference fields")
        key = asset["asset_id"]
        if (asset["asset_class"], asset["series_id"], asset["unit"], asset["timezone"]) != DETAILS[key]:
            raise ValueError("reference series mismatch")
        if asset["public_use_status"] != "approved_with_attribution":
            raise ValueError("public permission missing")
        if asset["timestamp_precision"] != "date" or asset["status"] not in {"available", "stale", "unavailable"}:
            raise ValueError("reference state invalid")
        if asset["freshness"].keys() != {"status", "age_seconds", "reason"}:
            raise ValueError("freshness fields invalid")
        if asset["freshness"]["status"] not in {"current", "stale", "unavailable"}:
            raise ValueError("freshness status invalid")
        expected_reason = {"available": "daily_reference_within_limit",
                           "stale": "older_than_daily_reference_limit",
                           "unavailable": "official_source_unavailable_or_invalid"}[asset["status"]]
        if asset["freshness"]["reason"] != expected_reason:
            raise ValueError("freshness reason invalid")
        if not isinstance(asset["message_zh"], str) or not asset["message_zh"]:
            raise ValueError("missing Chinese status")
        if asset["message_zh"] != {"available": "等待下一次官方更新",
                                       "stale": "資料時間較舊",
                                       "unavailable": "資料暫不可用"}[asset["status"]]:
            raise ValueError("invalid Chinese status")
        if asset["context_zh"] != context_for(key, asset["reference_value"], asset["reference_period"]):
            raise ValueError("unsupported reference context")
        if key == "US10Y":
            if asset["source"] != "Federal Reserve Board / U.S. Treasury" or asset["source_url"] != "https://www.federalreserve.gov/releases/h15/":
                raise ValueError("source mismatch")
        elif asset["source"] != "European Central Bank" or asset["source_url"] != "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml":
            raise ValueError("source mismatch")
        if not isinstance(asset["provenance"], dict) or set(asset["provenance"]) != {
            "attribution", "publisher", "source_url", "terms_url", "terms_reviewed_at",
            "source_record_sha256", "formula",
            "input_rates", "input_series"
        } or not asset["provenance"].get("attribution"):
            raise ValueError("provenance missing")
        expected_terms = ("https://www.federalreserve.gov/disclaimer.htm" if key == "US10Y" else
                          "https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html")
        if asset["provenance"]["terms_url"] != expected_terms or asset["provenance"]["terms_reviewed_at"] != "2026-09-23":
            raise ValueError("source reuse policy missing")
        expected_inputs = {"USDJPY": ["ecb_jpy_per_eur", "ecb_usd_per_eur"],
                           "GBPUSD": ["ecb_usd_per_eur", "ecb_gbp_per_eur"]}.get(key, [])
        if asset["provenance"]["input_series"] != expected_inputs:
            raise ValueError("provenance inputs invalid")
        expected_formula = {"USDJPY": "JPY/EUR ÷ USD/EUR", "GBPUSD": "USD/EUR ÷ GBP/EUR"}.get(key)
        if asset["provenance"].get("formula") != expected_formula:
            raise ValueError("cross-rate formula missing")
        if asset["provenance"].get("publisher") != asset["source"] or asset["provenance"].get("source_url") != asset["source_url"]:
            raise ValueError("provenance source mismatch")
        input_rates = asset["provenance"].get("input_rates")
        if not isinstance(input_rates, dict) or set(input_rates) != ({"USD", "JPY"} if key == "USDJPY" else
                                                                     {"USD", "GBP"} if key == "GBPUSD" else
                                                                     {"USD"} if key == "EURUSD" else set()):
            if asset["status"] != "unavailable" or input_rates != {}:
                raise ValueError("reference inputs missing")
        source_hash = asset["provenance"].get("source_record_sha256")
        if asset["status"] == "unavailable":
            if source_hash is not None:
                raise ValueError("unavailable source hash invalid")
        elif not isinstance(source_hash, str) or len(source_hash) != 64 or any(c not in "0123456789abcdef" for c in source_hash):
            raise ValueError("source hash missing")
        if asset["status"] == "unavailable":
            if any(asset[x] is not None for x in ("reference_value", "source_timestamp", "reference_period", "release_date", "retrieved_at")):
                raise ValueError("unavailable value leaked")
            if asset["freshness"]["status"] != "unavailable" or asset["freshness"]["age_seconds"] is not None:
                raise ValueError("unavailable freshness mismatch")
        else:
            try:
                value = Decimal(asset["reference_value"])
            except (InvalidOperation, TypeError):
                raise ValueError("invalid reference value") from None
            if not value.is_finite() or value <= 0:
                raise ValueError("invalid reference value")
            if key != "US10Y":
                try:
                    rates = {currency: Decimal(number) for currency, number in input_rates.items()}
                    if any(not number.is_finite() or number <= 0 for number in rates.values()):
                        raise ValueError("invalid input rate")
                    expected_value = (rates["USD"] if key == "EURUSD" else
                                      rates["JPY"] / rates["USD"] if key == "USDJPY" else
                                      rates["USD"] / rates["GBP"])
                    expected_value = expected_value.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_EVEN)
                except (InvalidOperation, ZeroDivisionError):
                    raise ValueError("invalid input rate") from None
                if value != expected_value:
                    raise ValueError("cross-rate value mismatch")
            period = _date(asset["reference_period"])
            if asset["source_timestamp"] != asset["reference_period"] or period > generated.date():
                raise ValueError("future or mismatched source date")
            if utc(asset["retrieved_at"]) > generated:
                raise ValueError("future retrieval")
            if asset["release_date"] is not None and _date(asset["release_date"]) < period:
                raise ValueError("release before observation")
            if (key == "US10Y") != (asset["release_date"] is not None):
                raise ValueError("release date required only for H15")
            age = asset["freshness"]["age_seconds"]
            if not isinstance(age, int) or age < 0:
                raise ValueError("invalid reference age")
            start = datetime.combine(period, time.min, ZoneInfo(asset["timezone"])).astimezone(timezone.utc)
            if age != int((generated - start).total_seconds()):
                raise ValueError("reference age mismatch")
            expected = "current" if asset["status"] == "available" else "stale"
            if asset["freshness"]["status"] != expected or (age <= MAX_AGE_SECONDS[key]) != (expected == "current"):
                raise ValueError("reference freshness mismatch")
        if public:
            serialized = canonical_bytes(asset).decode()
            if any(word in serialized.lower() for word in
                   ("raw_response", "authorization", "api_key", "access_token",
                    "/users/", "/home/", "receipt", "transport_metadata", "headers", "cookie")) or re.search(
                        r"(?:sk-|ghp_|Bearer\s+)[A-Za-z0-9_-]{10,}", serialized, re.IGNORECASE
                    ):
                raise ValueError("public reference contains private metadata")
        states.append(asset["status"])
    expected = ("available" if all(s == "available" for s in states) else
                "unavailable" if all(s == "unavailable" for s in states) else "partial")
    if payload["status"] != expected:
        raise ValueError("reference aggregation mismatch")


def project(payload: dict) -> dict:
    validate(payload)
    # Explicit key reconstruction prevents later internal fields from leaking.
    result = {k: payload[k] for k in PUBLIC_KEYS if k != "assets"}
    result["assets"] = [{k: a[k] for k in PUBLIC_ASSET_KEYS} for a in payload["assets"]]
    validate(result, public=True)
    return result
