"""Calculate the Phase 1.1 market snapshot features."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Optional

import pandas as pd

from src.models.schema import AssetType


@dataclass(frozen=True)
class FeatureSet:
    price: float
    daily_change: Optional[float]
    weekly_change: Optional[float]
    sma20: Optional[float]
    volatility_20d: Optional[float]
    trend: str


def calculate_features(closes: pd.Series, asset_type: AssetType) -> FeatureSet:
    """Return changes in percent and annualized 20-day volatility in percent."""
    clean = pd.to_numeric(closes, errors="coerce").dropna().astype(float)
    if len(clean) < 2:
        raise ValueError("at least two close values are required")

    price = float(clean.iloc[-1])
    daily_change = _percent_change(price, float(clean.iloc[-2]))
    weekly_change = (
        _percent_change(price, float(clean.iloc[-6]))
        if len(clean) >= 6
        else None
    )
    sma20 = float(clean.tail(20).mean()) if len(clean) >= 20 else None

    returns = clean.pct_change().dropna().tail(20)
    annualization_factor = 365 if asset_type is AssetType.CRYPTO else 252
    volatility = (
        float(returns.std(ddof=1) * sqrt(annualization_factor) * 100)
        if len(returns) >= 20
        else None
    )

    if sma20 is None:
        trend = "insufficient_data"
    elif price > sma20:
        trend = "above_sma20"
    elif price < sma20:
        trend = "below_sma20"
    else:
        trend = "at_sma20"

    return FeatureSet(
        price=_rounded(price, 6),
        daily_change=_rounded(daily_change, 4),
        weekly_change=_rounded(weekly_change, 4),
        sma20=_rounded(sma20, 6),
        volatility_20d=_rounded(volatility, 4),
        trend=trend,
    )


def _percent_change(latest: float, previous: float) -> Optional[float]:
    if previous == 0:
        return None
    return ((latest / previous) - 1) * 100


def _rounded(value: Optional[float], digits: int) -> Optional[float]:
    return None if value is None else round(value, digits)

