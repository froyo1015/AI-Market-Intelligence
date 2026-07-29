"""Normalize provider-specific history into a canonical close series."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pandas as pd

from src.data.market_adapter import MarketDataError
from src.models.schema import Instrument, SnapshotStatus


@dataclass(frozen=True)
class NormalizedMarketData:
    """Canonical daily close series plus freshness metadata."""

    instrument: Instrument
    closes: pd.Series
    timestamp: datetime
    status: SnapshotStatus


def normalize_history(
    history: pd.DataFrame,
    instrument: Instrument,
    now: datetime | None = None,
) -> NormalizedMarketData:
    """Validate, sort, de-duplicate and timezone-normalize daily closes."""
    if "Close" not in history.columns:
        raise MarketDataError(
            f"provider response has no Close column for {instrument.symbol}"
        )

    closes = pd.to_numeric(history["Close"], errors="coerce").dropna()
    closes = closes[~closes.index.duplicated(keep="last")].sort_index()

    if len(closes) < 2:
        raise MarketDataError(
            f"not enough valid close values for {instrument.symbol}"
        )

    index = pd.DatetimeIndex(closes.index)
    if index.tz is None:
        index = index.tz_localize(timezone.utc)
    else:
        index = index.tz_convert(timezone.utc)

    closes.index = index
    timestamp = index[-1].to_pydatetime()
    current_time = _as_utc(now or datetime.now(timezone.utc))
    age = current_time - timestamp
    status = (
        SnapshotStatus.STALE
        if age > timedelta(days=instrument.stale_after_days)
        else SnapshotStatus.SUCCESS
    )

    return NormalizedMarketData(
        instrument=instrument,
        closes=closes.astype(float),
        timestamp=timestamp,
        status=status,
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)

