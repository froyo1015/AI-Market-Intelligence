"""Generate the four official daily references and their safe public projection."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, time, timezone
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from pathlib import Path
from zoneinfo import ZoneInfo

from requests.exceptions import RequestException

from .model import ASSETS, DETAILS, MAX_AGE_SECONDS, VERSION, canonical_bytes, context_for, project, stamp, validate
from .sources import ECB_URL, H15_URL, SourceError, fetch, parse_ecb, parse_h15

ATTRIBUTION = {
    "US10Y": "Federal Reserve Board H.15; U.S. Treasury nominal 10-year constant-maturity yield",
    "EURUSD": "European Central Bank reference rates",
    "USDJPY": "European Central Bank reference rates; calculated cross rate",
    "GBPUSD": "European Central Bank reference rates; calculated cross rate",
}


def _number(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_EVEN).normalize(), "f")


def _asset(key: str, source_record: dict | None, value: Decimal | None,
           retrieved_at: str | None, generated_at: datetime, reason: str) -> dict:
    asset_class, series, unit, zone = DETAILS[key]
    is_h15 = key == "US10Y"
    source = "Federal Reserve Board / U.S. Treasury" if is_h15 else "European Central Bank"
    url = H15_URL if is_h15 else ECB_URL
    formula = ("JPY/EUR ÷ USD/EUR" if key == "USDJPY" else
               "USD/EUR ÷ GBP/EUR" if key == "GBPUSD" else None)
    rates = source_record["rates"] if source_record and not is_h15 else {}
    input_rates = ({"USD": _number(rates["USD"]), "JPY": _number(rates["JPY"])} if rates and key == "USDJPY" else
                   {"USD": _number(rates["USD"]), "GBP": _number(rates["GBP"])} if rates and key == "GBPUSD" else
                   {"USD": _number(rates["USD"])} if rates and key == "EURUSD" else {})
    provenance = dict(attribution=ATTRIBUTION[key], publisher=source, source_url=url,
                      terms_url=("https://www.federalreserve.gov/disclaimer.htm" if is_h15 else
                                 "https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html"),
                      terms_reviewed_at="2026-09-23",
                      source_record_sha256=source_record["sha256"] if source_record else None,
                      formula=formula, input_rates=input_rates,
                      input_series=(["ecb_jpy_per_eur", "ecb_usd_per_eur"] if key == "USDJPY" else
                                    ["ecb_usd_per_eur", "ecb_gbp_per_eur"] if key == "GBPUSD" else []))
    period = source_record["period"] if source_record else None
    if source_record and value is not None:
        start = datetime.combine(datetime.fromisoformat(period).date(), time.min,
                                 ZoneInfo(zone)).astimezone(timezone.utc)
        age = int((generated_at - start).total_seconds())
        if age < 0:
            raise SourceError("future_reference_period")
        current = age <= MAX_AGE_SECONDS[key]
        status = "available" if current else "stale"
        freshness = dict(status="current" if current else "stale", age_seconds=age,
                         reason="daily_reference_within_limit" if current else "older_than_daily_reference_limit")
        message = "等待下一次官方更新" if current else "資料時間較舊"
    else:
        value = None
        status = "unavailable"
        freshness = dict(status="unavailable", age_seconds=None, reason=reason)
        message = "資料暫不可用"
    shown_value = _number(value) if value is not None else None
    return dict(asset_id=key, symbol=key, asset_class=asset_class, series_id=series,
                reference_value=shown_value, unit=unit,
                source=source, source_url=url, source_timestamp=period,
                timestamp_precision="date", reference_period=period, timezone=zone,
                release_date=source_record.get("release_date") if source_record else None,
                retrieved_at=retrieved_at if source_record else None, freshness=freshness,
                provenance=provenance, public_use_status="approved_with_attribution",
                status=status, message_zh=message,
                context_zh=context_for(key, shown_value, period))


def collect(*, now: datetime | None = None, fetcher=fetch) -> dict:
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    records = {}
    retrieved = {}
    failures = {}
    for name, url, parser in (("h15", H15_URL, parse_h15), ("ecb", ECB_URL, parse_ecb)):
        try:
            body = fetcher(url)
            received = datetime.now(timezone.utc) if now is None else current
            records[name] = parser(body, received)
            retrieved[name] = stamp(received)
        except (RequestException, TimeoutError, OSError, SourceError, UnicodeError, ValueError):
            failures[name] = "official_source_unavailable_or_invalid"
    generated = datetime.now(timezone.utc) if now is None else current
    ecb = records.get("ecb")
    h15 = records.get("h15")
    values = {}
    if ecb:
        rates = ecb["rates"]
        with localcontext() as decimal_context:
            decimal_context.prec = 28
            values = {"EURUSD": rates["USD"],
                      "USDJPY": rates["JPY"] / rates["USD"],
                      "GBPUSD": rates["USD"] / rates["GBP"]}
    assets = [
        _asset(key, h15 if key == "US10Y" else ecb,
               h15["value"] if h15 and key == "US10Y" else values.get(key),
               retrieved.get("h15" if key == "US10Y" else "ecb"), generated,
               failures.get("h15" if key == "US10Y" else "ecb", "official_source_unavailable_or_invalid"))
        for key in ASSETS
    ]
    states = [a["status"] for a in assets]
    status = ("available" if all(s == "available" for s in states) else
              "unavailable" if all(s == "unavailable" for s in states) else "partial")
    result = dict(version=VERSION, reference_kind="official_daily_reference",
                  generated_at=stamp(generated), status=status, assets=assets)
    validate(result)
    return result


def run(*, canonical_path: Path, public_path: Path, now: datetime | None = None,
        fetcher=fetch) -> dict:
    # An interrupted retry must not leave yesterday's public projection in place.
    canonical_path.unlink(missing_ok=True)
    public_path.unlink(missing_ok=True)
    result = collect(now=now, fetcher=fetcher)
    public = project(result)
    canonical_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.parent.mkdir(parents=True, exist_ok=True)
    canonical_path.write_bytes(canonical_bytes(result))
    public_path.write_bytes(canonical_bytes(public))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical-out", type=Path, default=Path("src/output/daily_market_reference.json"))
    parser.add_argument("--public-out", type=Path, default=Path("docs/data/daily_market_reference_public.json"))
    args = parser.parse_args()
    result = run(canonical_path=args.canonical_out, public_path=args.public_out)
    print(json.dumps({"status": result["status"], "assets": {a["asset_id"]: a["status"] for a in result["assets"]}}, sort_keys=True))


if __name__ == "__main__":
    main()
