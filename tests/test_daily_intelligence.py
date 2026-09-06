from __future__ import annotations

import copy
import json
from datetime import timedelta
from pathlib import Path
from typing import Dict, Optional, Set, Tuple

import pytest

from src.data.freshness import strip_freshness_metadata, validate_freshness_contract
from src.intelligence.composer import build_daily_intelligence_artifact
from src.intelligence.pipeline import (
    DailyIntelligenceInputError,
    run_daily_intelligence_pipeline,
)
from src.intelligence.validator import (
    DailyIntelligenceValidationError,
    validate_daily_intelligence_artifact,
)
from src.risk.monitor import build_risk_monitor_artifact
from tests.test_cross_asset_signals import DEFAULT_VALUES, NOW
from tests.test_evidence_consolidation import _calendar
from tests.test_risk_monitor import _linked_inputs


def _four_inputs(
    values: Optional[Dict[str, float]] = None,
    stale_assets: Optional[Set[str]] = None,
    calendar: Optional[dict] = None,
) -> Tuple[dict, dict, dict, dict]:
    evidence, signals, regime = _linked_inputs(
        values=values,
        stale_assets=stale_assets,
        calendar=calendar,
    )
    risk = build_risk_monitor_artifact(
        evidence,
        signals,
        regime,
        now=NOW,
    ).to_dict()
    return evidence, signals, regime, risk


def _compose(inputs: Tuple[dict, dict, dict, dict], now=NOW) -> dict:
    artifact = build_daily_intelligence_artifact(*inputs, now=now).to_dict()
    validate_daily_intelligence_artifact(artifact, *inputs)
    return artifact


def test_complete_intelligence_assembly_preserves_all_validated_objects() -> None:
    inputs = _four_inputs()
    evidence, signals, regime, risk = inputs
    artifact = _compose(inputs)

    assert artifact["status"] == "available"
    assert artifact["market_regime"]["payload"] == regime
    assert len(artifact["cross_asset_signals"]) == signals["signal_count"] == 8
    assert artifact["upcoming_events"] == []
    assert artifact["data_quality_risks"] == []
    assert artifact["observed_market_stress"] == []
    assert artifact["object_counts"]["total"] == 9
    assert all(
        item["validation_status"] == "validated"
        for item in [artifact["market_regime"]]
        + artifact["cross_asset_signals"]
    )
    assert artifact["input_refs"]["evidence_bundle_run_id"] == evidence["run_id"]
    assert artifact["input_refs"]["risk_monitor_run_id"] == risk["run_id"]


def test_partial_data_preserves_degraded_objects_and_statuses() -> None:
    inputs = _four_inputs(stale_assets={"DXY"})
    artifact = _compose(inputs)

    assert artifact["status"] == "partial"
    assert artifact["data_quality_risks"]
    states = {
        item["payload"]["rule_id"]: item["data_status"]
        for item in artifact["cross_asset_signals"]
    }
    assert states["dollar_yield_co_movement_v1"] == "stale_data"
    assert artifact["market_regime"]["data_status"] == "partial"
    assert "upstream_partial:evidence_bundle.json" in artifact["warnings"]


def test_unavailable_upstream_modules_keep_quality_objects_without_fabrication() -> None:
    inputs = _four_inputs(stale_assets=set(DEFAULT_VALUES))
    artifact = _compose(inputs)

    assert artifact["status"] == "unavailable"
    assert artifact["market_regime"]["payload"]["classification"] is None
    assert artifact["data_quality_risks"]
    assert artifact["upcoming_events"] == []
    assert artifact["observed_market_stress"] == []
    assert "no_current_substantive_intelligence" in artifact["warnings"]
    assert not any(
        item["data_status"] in {"observed", "not_observed"}
        and item["payload"]["data_quality"]["status"] == "available"
        for item in artifact["cross_asset_signals"]
    )


def test_provenance_catalog_resolves_event_signal_and_stress_references() -> None:
    inputs = _four_inputs(
        values={
            "SPY": -1.0,
            "QQQ": -1.2,
            "BTC-USD": -0.8,
            "ETH-USD": -0.7,
            "VIX": 0.5,
            "DXY": 0.8,
            "US10Y": 2.0,
        },
        calendar=_calendar(),
    )
    artifact = _compose(inputs)
    catalog = artifact["provenance_catalog"]
    event_ids = {item["event_id"] for item in catalog["event_records"]}
    source_ids = {item["source_id"] for item in catalog["source_records"]}
    observation_ids = {
        item["observation_id"] for item in catalog["observation_records"]
    }

    assert len(artifact["upcoming_events"]) == 1
    assert artifact["observed_market_stress"]
    assert "evt_cpi" in event_ids
    for section in (
        artifact["cross_asset_signals"],
        artifact["upcoming_events"],
        artifact["observed_market_stress"],
    ):
        for item in section:
            refs = item["evidence_refs"]
            assert set(refs["source_ids"]).issubset(source_ids)
            assert set(refs["observation_ids"]).issubset(observation_ids)
            assert set(refs["event_ids"]).issubset(event_ids)
            assert item["source_generated_at"]
            assert item["validation_status"] == "validated"


def test_identical_inputs_and_time_produce_identical_ordered_output() -> None:
    inputs = _four_inputs(calendar=_calendar())
    first = build_daily_intelligence_artifact(*inputs, now=NOW).to_dict()
    second = build_daily_intelligence_artifact(*inputs, now=NOW).to_dict()

    assert first == second
    assert [item["payload"]["rule_id"] for item in first["cross_asset_signals"]] == sorted(
        item["rule_id"] for item in inputs[1]["signals"]
    )
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_artifacts_older_than_24_hours_are_not_current_intelligence() -> None:
    inputs = _four_inputs()
    artifact = _compose(inputs, now=NOW + timedelta(hours=25))

    assert artifact["status"] == "unavailable"
    assert all(
        item["artifact_freshness_status"] == "stale"
        for item in artifact["coverage"]
    )
    assert all(item["age_hours"] >= 25 for item in artifact["coverage"])
    assert "upstream_stale:evidence_bundle.json" in artifact["warnings"]
    assert "no_current_substantive_intelligence" in artifact["warnings"]


def test_validator_rejects_payload_status_and_prohibited_field_tampering() -> None:
    inputs = _four_inputs()
    artifact = _compose(inputs)

    payload_tamper = copy.deepcopy(artifact)
    original_condition = payload_tamper["cross_asset_signals"][0]["payload"][
        "condition_met"
    ]
    payload_tamper["cross_asset_signals"][0]["payload"]["condition_met"] = (
        not original_condition
    )
    with pytest.raises(
        DailyIntelligenceValidationError,
        match="does not match deterministic assembly",
    ):
        validate_daily_intelligence_artifact(payload_tamper, *inputs)

    validation_tamper = copy.deepcopy(artifact)
    validation_tamper["market_regime"]["validation_status"] = "unchecked"
    with pytest.raises(
        DailyIntelligenceValidationError,
        match="does not match deterministic assembly",
    ):
        validate_daily_intelligence_artifact(validation_tamper, *inputs)

    prohibited = copy.deepcopy(artifact)
    prohibited["prediction"] = "unsupported"
    with pytest.raises(
        DailyIntelligenceValidationError,
        match="prohibited Phase 6.4-A field",
    ):
        validate_daily_intelligence_artifact(prohibited, *inputs)


def test_pipeline_reads_four_artifact_types_and_writes_atomically(
    tmp_path: Path,
) -> None:
    inputs = _four_inputs(calendar=_calendar())
    paths = [
        tmp_path / "evidence_bundle.json",
        tmp_path / "market_signals.json",
        tmp_path / "market_regime.json",
        tmp_path / "risk_monitor.json",
    ]
    for path, payload in zip(paths, inputs):
        path.write_text(json.dumps(payload), encoding="utf-8")
    output_path = tmp_path / "daily_intelligence.json"

    result = run_daily_intelligence_pipeline(*paths, output_path)

    written = json.loads(output_path.read_text(encoding="utf-8"))
    validate_freshness_contract(written)
    assert strip_freshness_metadata(written) == result.to_dict()
    assert not (tmp_path / "daily_intelligence.json.tmp").exists()

    wrong = tmp_path / "wrong.json"
    wrong.write_text(json.dumps({"artifact_type": "events"}), encoding="utf-8")
    with pytest.raises(DailyIntelligenceInputError, match="requires risk_monitor"):
        run_daily_intelligence_pipeline(*paths[:3], wrong, output_path)
