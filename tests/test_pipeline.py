import json
from datetime import datetime, timezone

import pandas as pd

from src.models.schema import AssetType, Instrument, SnapshotStatus
from src.pipeline import build_snapshot, write_snapshot


class FakeAdapter:
    source_name = "fake_source"

    def fetch_history(self, instrument: Instrument, period: str) -> pd.DataFrame:
        if instrument.symbol == "FAIL":
            raise RuntimeError("simulated provider failure")

        index = pd.date_range("2026-06-20", periods=40, freq="D", tz="UTC")
        return pd.DataFrame(
            {"Close": [100 + value for value in range(40)]},
            index=index,
        )


def test_pipeline_writes_success_and_failed_records(tmp_path) -> None:
    instruments = (
        Instrument("OK", "OK", AssetType.EQUITY, stale_after_days=5),
        Instrument("FAIL", "FAIL", AssetType.EQUITY, stale_after_days=5),
    )
    snapshot = build_snapshot(
        adapter=FakeAdapter(),
        instruments=instruments,
        now=datetime(2026, 7, 29, 12, tzinfo=timezone.utc),
    )

    assert snapshot.records[0].status is SnapshotStatus.SUCCESS
    assert snapshot.records[1].status is SnapshotStatus.FAILED
    assert snapshot.records[1].error is not None

    output_path = tmp_path / "market_snapshot.json"
    write_snapshot(snapshot, output_path)
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["source"] == "fake_source"
    assert payload["records"][0]["symbol"] == "OK"
    assert payload["records"][1]["status"] == "failed"
    assert payload["records"][1]["timestamp"].endswith("Z")

