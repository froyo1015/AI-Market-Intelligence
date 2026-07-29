from __future__ import annotations

from src.data.asset_metadata import ASSET_METADATA, get_asset_metadata
from src.data.data_quality import (
    FreshnessLevel,
    assess_record_freshness,
    build_data_quality_context,
)


def _record(
    symbol: str,
    timestamp: str,
    status: str = "success",
    price: float | None = 100.0,
) -> dict:
    return {
        "symbol": symbol,
        "timestamp": timestamp,
        "status": status,
        "price": price,
    }


def test_metadata_covers_every_supported_asset_and_alias() -> None:
    assert set(ASSET_METADATA) == {
        "SPY",
        "QQQ",
        "NVDA",
        "AAPL",
        "TSLA",
        "BTC-USD",
        "ETH-USD",
        "GOLD",
        "EURUSD",
        "USDJPY",
    }
    assert get_asset_metadata("BTC").symbol == "BTC-USD"
    assert get_asset_metadata("ETH").symbol == "ETH-USD"
    assert get_asset_metadata("Gold").provider_symbol == "GC=F"
    assert "不是現貨金" in get_asset_metadata("GOLD").price_basis


def test_freshness_uses_asset_specific_thresholds() -> None:
    report_time = "2026-07-29T12:00:00Z"

    current = assess_record_freshness(
        _record("SPY", "2026-07-29T04:00:00Z"),
        report_time,
    )
    delayed = assess_record_freshness(
        _record("BTC-USD", "2026-07-28T00:00:00Z"),
        report_time,
    )
    stale = assess_record_freshness(
        _record("BTC-USD", "2026-07-26T00:00:00Z"),
        report_time,
    )

    assert current.level is FreshnessLevel.CURRENT
    assert current.age_hours == 8.0
    assert delayed.level is FreshnessLevel.DELAYED
    assert stale.level is FreshnessLevel.STALE


def test_provider_status_and_invalid_time_override_age_policy() -> None:
    report_time = "2026-07-29T12:00:00Z"

    failed = assess_record_freshness(
        _record("SPY", report_time, status="failed", price=None),
        report_time,
    )
    provider_stale = assess_record_freshness(
        _record("SPY", report_time, status="stale"),
        report_time,
    )
    future = assess_record_freshness(
        _record("SPY", "2026-07-30T12:00:00Z"),
        report_time,
    )

    assert failed.level is FreshnessLevel.FAILED
    assert provider_stale.level is FreshnessLevel.STALE
    assert future.level is FreshnessLevel.UNKNOWN


def test_quality_context_contains_time_window_metadata_and_counts() -> None:
    snapshot = {
        "generated_at": "2026-07-29T12:00:00Z",
        "records": [
            _record("SPY", "2026-07-29T04:00:00Z"),
            _record("BTC-USD", "2026-07-28T00:00:00Z"),
            _record(
                "ETH-USD",
                "2026-07-29T00:00:00Z",
                status="failed",
                price=None,
            ),
        ],
    }

    quality = build_data_quality_context(snapshot)

    assert quality["summary"]["earliest_data_time"] == "2026-07-28T00:00:00Z"
    assert quality["summary"]["latest_data_time"] == "2026-07-29T04:00:00Z"
    assert quality["summary"]["counts"]["current"] == 1
    assert quality["summary"]["counts"]["delayed"] == 1
    assert quality["summary"]["counts"]["failed"] == 1
    assert (
        quality["records"]["SPY"]["metadata"]["market_session"]
        == "美股核心交易時段 09:30–16:00 ET（交易日）"
    )
