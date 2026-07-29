from datetime import datetime, timezone

import pandas as pd

from src.data.normalizer import normalize_history
from src.models.schema import AssetType, Instrument, SnapshotStatus


def _instrument(stale_after_days: int = 5) -> Instrument:
    return Instrument(
        symbol="TEST",
        provider_symbol="TEST",
        asset_type=AssetType.EQUITY,
        stale_after_days=stale_after_days,
    )


def test_normalizer_sorts_and_deduplicates() -> None:
    history = pd.DataFrame(
        {"Close": [102.0, 100.0, 101.0, 103.0]},
        index=pd.to_datetime(
            ["2026-07-28", "2026-07-27", "2026-07-28", "2026-07-29"]
        ),
    )

    result = normalize_history(
        history,
        _instrument(),
        now=datetime(2026, 7, 29, 12, tzinfo=timezone.utc),
    )

    assert list(result.closes) == [100.0, 101.0, 103.0]
    assert result.timestamp.tzinfo is not None
    assert result.status is SnapshotStatus.SUCCESS


def test_normalizer_marks_old_data_stale() -> None:
    history = pd.DataFrame(
        {"Close": [100.0, 101.0]},
        index=pd.to_datetime(["2026-07-01", "2026-07-02"]),
    )

    result = normalize_history(
        history,
        _instrument(stale_after_days=5),
        now=datetime(2026, 7, 10, tzinfo=timezone.utc),
    )

    assert result.status is SnapshotStatus.STALE

