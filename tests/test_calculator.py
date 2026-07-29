import math

import pandas as pd

from src.features.calculator import calculate_features
from src.models.schema import AssetType


def test_calculates_required_features() -> None:
    closes = pd.Series([100 + index for index in range(25)], dtype=float)

    result = calculate_features(closes, AssetType.EQUITY)

    assert result.price == 124.0
    assert result.daily_change == round(((124 / 123) - 1) * 100, 4)
    assert result.weekly_change == round(((124 / 119) - 1) * 100, 4)
    assert result.sma20 == 114.5
    assert result.volatility_20d is not None
    assert result.volatility_20d > 0
    assert result.trend == "above_sma20"


def test_crypto_uses_365_day_annualization() -> None:
    closes = pd.Series([100 + index for index in range(25)], dtype=float)

    equity = calculate_features(closes, AssetType.EQUITY)
    crypto = calculate_features(closes, AssetType.CRYPTO)

    expected_ratio = math.sqrt(365 / 252)
    assert crypto.volatility_20d is not None
    assert equity.volatility_20d is not None
    assert math.isclose(
        crypto.volatility_20d / equity.volatility_20d,
        expected_ratio,
        rel_tol=1e-3,
    )
