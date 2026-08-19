from __future__ import annotations

import copy
import json
from datetime import datetime, timezone

import pandas as pd
import pytest

from src.data.macro_adapter import DEFAULT_MACRO_INSTRUMENTS, MacroInstrument
from src.evidence.builder import (
    build_evidence_artifact,
    build_observation_artifact,
)
from src.evidence.pipeline import run_evidence_pipeline
from src.evidence.validator import (
    EvidenceValidationError,
    validate_evidence_artifact,
)
from src.macro_pipeline import build_macro_snapshot


class FakeMacroAdapter:
    source_name = "fake_macro"

    def fetch_history(
        self, instrument: MacroInstrument, period: str
    ) -> pd.DataFrame:
        if instrument.symbol == "OIL":
            raise RuntimeError("simulated oil provider failure")
        index = pd.date_range("2026-08-10", periods=8, freq="D", tz="UTC")
        if instrument.symbol == "US10Y":
            closes = [4.00, 4.02, 4.04, 4.06, 4.08, 4.10, 4.15, 4.20]
        else:
            closes = [100.0 + value for value in range(8)]
        return pd.DataFrame({"Close": closes}, index=index)


def _market_snapshot() -> dict:
    return {
        "schema_version": "1.0",
        "generated_at": "2026-08-18T01:30:00Z",
        "source": "yahoo_finance",
        "records": [
            {
                "symbol": "SPY",
                "asset_type": "equity",
                "price": 100.0,
                "daily_change": -1.0,
                "weekly_change": -2.0,
                "sma20": 101.0,
                "volatility_20d": 20.0,
                "trend": "below_sma20",
                "timestamp": "2026-08-17T20:00:00Z",
                "source": "yahoo_finance",
                "status": "success",
            }
        ],
    }


def _macro_snapshot() -> dict:
    return build_macro_snapshot(
        adapter=FakeMacroAdapter(),
        now=datetime(2026, 8, 18, 1, 30, tzinfo=timezone.utc),
    ).to_dict()


def test_macro_instrument_contract_is_fixed_and_source_grounded() -> None:
    assert [item.symbol for item in DEFAULT_MACRO_INSTRUMENTS] == [
        "DXY",
        "US10Y",
        "VIX",
        "OIL",
    ]
    assert [item.provider_symbol for item in DEFAULT_MACRO_INSTRUMENTS] == [
        "DX-Y.NYB",
        "^TNX",
        "^VIX",
        "CL=F",
    ]
    assert all(item.provider_url.startswith("https://") for item in DEFAULT_MACRO_INSTRUMENTS)
    assert all(item.semantic_reference_url.startswith("https://") for item in DEFAULT_MACRO_INSTRUMENTS)
    assert all(item.asset_mapping for item in DEFAULT_MACRO_INSTRUMENTS)


def test_macro_pipeline_calculates_percent_and_basis_point_changes() -> None:
    payload = _macro_snapshot()
    records = {record["symbol"]: record for record in payload["records"]}

    assert payload["status"] == "partial"
    assert records["DXY"]["daily_change"] == pytest.approx(0.9434)
    assert records["DXY"]["change_unit"] == "percent"
    assert records["US10Y"]["value"] == 4.2
    assert records["US10Y"]["daily_change"] == pytest.approx(5.0)
    assert records["US10Y"]["change_unit"] == "basis_points"
    assert records["OIL"]["status"] == "failed"
    assert records["OIL"]["confidence_label"] == "insufficient"
    assert "simulated oil provider failure" in records["OIL"]["error"]


def test_macro_failure_is_isolated_without_losing_other_records() -> None:
    payload = _macro_snapshot()

    assert len(payload["records"]) == 4
    assert sum(record["status"] == "success" for record in payload["records"]) == 3
    assert sum(record["status"] == "failed" for record in payload["records"]) == 1


def test_macro_records_become_mapped_observations_and_evidence() -> None:
    observations = build_observation_artifact(
        _market_snapshot(),
        _macro_snapshot(),
    )
    evidence = build_evidence_artifact(observations)
    indexed = {
        (item["subject"], item["metric"]): item
        for item in observations["observations"]
    }

    us10y = indexed[("US10Y", "daily_change_bps")]
    assert observations["schema_version"] == "1.1"
    assert us10y["observation_type"] == "macro_value"
    assert us10y["source_id"] == "src_fake_macro_us10y"
    assert us10y["asset_mapping"] == ["SPY", "QQQ", "GOLD", "DXY", "USDJPY"]
    assert us10y["confidence_score"] == 0.75

    macro_bundles = {
        item["evidence_id"]: item
        for item in evidence["evidence"]
        if item["claim_type"] == "macro_move"
    }
    us10y_bundle = next(
        item for key, item in macro_bundles.items() if key.startswith("evd_us10y_")
    )
    assert us10y_bundle["statement"] == (
        "US10Y increased 5 basis points over the latest daily interval."
    )
    assert us10y_bundle["confidence_score"] == 0.75
    assert "SPY" in us10y_bundle["affected_assets"]
    assert any("OIL macro observations omitted" in item for item in evidence["warnings"])
    validate_evidence_artifact(evidence, observations)


def test_macro_observation_requires_asset_mapping_and_confidence() -> None:
    observations = build_observation_artifact(
        _market_snapshot(),
        _macro_snapshot(),
    )
    evidence = build_evidence_artifact(observations)
    invalid = copy.deepcopy(observations)
    macro = next(
        item
        for item in invalid["observations"]
        if item["observation_type"] == "macro_value"
    )
    macro["asset_mapping"] = []

    with pytest.raises(EvidenceValidationError, match="no asset mapping"):
        validate_evidence_artifact(evidence, invalid)


def test_evidence_pipeline_merges_explicit_macro_snapshot(tmp_path) -> None:
    market_path = tmp_path / "market_snapshot.json"
    macro_path = tmp_path / "macro_snapshot.json"
    observations_path = tmp_path / "observations.json"
    evidence_path = tmp_path / "evidence.json"
    market_path.write_text(json.dumps(_market_snapshot()), encoding="utf-8")
    macro_path.write_text(json.dumps(_macro_snapshot()), encoding="utf-8")

    observations, evidence = run_evidence_pipeline(
        snapshot_path=market_path,
        macro_snapshot_path=macro_path,
        observations_path=observations_path,
        evidence_path=evidence_path,
    )

    assert any(
        item["observation_type"] == "macro_value"
        for item in observations["observations"]
    )
    assert sum(
        item["claim_type"] == "macro_move" for item in evidence["evidence"]
    ) == 3
