"""Orchestrate market download, normalization, features and JSON output."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

from src.data.market_adapter import (
    DEFAULT_INSTRUMENTS,
    MarketDataAdapter,
    YahooFinanceMarketAdapter,
)
from src.data.normalizer import normalize_history
from src.features.calculator import calculate_features
from src.models.schema import (
    Instrument,
    MarketSnapshot,
    MarketSnapshotRecord,
    SnapshotStatus,
)


DEFAULT_OUTPUT_PATH = Path(__file__).resolve().parent / "output" / "market_snapshot.json"


def build_snapshot(
    adapter: Optional[MarketDataAdapter] = None,
    instruments: Iterable[Instrument] = DEFAULT_INSTRUMENTS,
    period: str = "3mo",
    now: Optional[datetime] = None,
) -> MarketSnapshot:
    """Build all records while isolating failures to individual instruments."""
    provider = adapter or YahooFinanceMarketAdapter()
    generated_at = _as_utc(now or datetime.now(timezone.utc))
    records = []

    for instrument in instruments:
        try:
            history = provider.fetch_history(instrument, period)
            normalized = normalize_history(history, instrument, now=generated_at)
            features = calculate_features(
                normalized.closes,
                instrument.asset_type,
            )
            records.append(
                MarketSnapshotRecord(
                    symbol=instrument.symbol,
                    asset_type=instrument.asset_type,
                    price=features.price,
                    daily_change=features.daily_change,
                    weekly_change=features.weekly_change,
                    sma20=features.sma20,
                    volatility_20d=features.volatility_20d,
                    trend=features.trend,
                    timestamp=normalized.timestamp,
                    source=provider.source_name,
                    status=normalized.status,
                )
            )
        except Exception as exc:
            records.append(
                MarketSnapshotRecord(
                    symbol=instrument.symbol,
                    asset_type=instrument.asset_type,
                    price=None,
                    daily_change=None,
                    weekly_change=None,
                    sma20=None,
                    volatility_20d=None,
                    trend="unavailable",
                    timestamp=generated_at,
                    source=provider.source_name,
                    status=SnapshotStatus.FAILED,
                    error=_safe_error(exc),
                )
            )

    return MarketSnapshot(
        generated_at=generated_at,
        source=provider.source_name,
        records=records,
    )


def write_snapshot(
    snapshot: MarketSnapshot,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> Path:
    """Write formatted UTF-8 JSON atomically enough for the MVP batch job."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(f"{output_path.suffix}.tmp")
    temporary_path.write_text(
        json.dumps(snapshot.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(output_path)
    return output_path


def run_pipeline(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    period: str = "3mo",
) -> MarketSnapshot:
    snapshot = build_snapshot(period=period)
    write_snapshot(snapshot, output_path)
    return snapshot


def _safe_error(exc: Exception) -> str:
    message = " ".join(str(exc).split())
    return f"{type(exc).__name__}: {message}"[:300]


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)

