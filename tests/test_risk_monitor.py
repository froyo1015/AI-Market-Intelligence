from __future__ import annotations

import copy
import json
from datetime import timedelta
from pathlib import Path
from typing import Dict, Optional, Set, Tuple

import pytest

from src.data.freshness import strip_freshness_metadata, validate_freshness_contract
from src.consolidation.builder import build_consolidated_evidence_artifact
from src.regime.classifier import build_market_regime_artifact
from src.risk.monitor import RiskMonitorError, build_risk_monitor_artifact
from src.risk.pipeline import RiskMonitorInputError, run_risk_monitor_pipeline
from src.risk.validator import (
    RiskMonitorValidationError,
    validate_risk_monitor_artifact,
)
from src.signals.engine import build_market_signals_artifact
from tests.test_cross_asset_signals import NOW, _inputs
from tests.test_evidence_consolidation import _calendar


def _linked_inputs(
    values: Optional[Dict[str, float]] = None,
    stale_assets: Optional[Set[str]] = None,
    calendar: Optional[dict] = None,
) -> Tuple[dict, dict, dict]:
    inputs = list(_inputs(values=values, stale_assets=stale_assets))
    if calendar is not None:
        inputs[2] = calendar
    evidence = build_consolidated_evidence_artifact(*inputs, now=NOW).to_dict()
    signals = build_market_signals_artifact(evidence, now=NOW).to_dict()
    regime = build_market_regime_artifact(evidence, signals, now=NOW).to_dict()
    return evidence, signals, regime


def _monitor(
    evidence: dict,
    signals: dict,
    regime: dict,
    now=NOW,
) -> dict:
    artifact = build_risk_monitor_artifact(
        evidence,
        signals,
        regime,
        now=now,
    ).to_dict()
    validate_risk_monitor_artifact(artifact, evidence, signals, regime)
    return artifact


def _by_rule(artifact: dict, rule_id: str) -> list[dict]:
    return [item for item in artifact["risks"] if item["rule_id"] == rule_id]


def test_upcoming_official_event_preserves_schedule_and_provenance() -> None:
    evidence, signals, regime = _linked_inputs(calendar=_calendar())
    artifact = _monitor(evidence, signals, regime)
    risks = _by_rule(artifact, "upcoming_official_event_v1")

    assert len(risks) == 1
    risk = risks[0]
    assert risk["category"] == "upcoming_event"
    assert risk["status"] == "scheduled"
    assert risk["attention_level"] == "high"
    assert risk["observed_facts"]["event_id"] == "evt_cpi"
    assert risk["observed_facts"]["scheduled_at"] == "2026-08-27T12:30:00Z"
    assert risk["evidence_refs"]["event_ids"] == ["evt_cpi"]
    assert risk["evidence_refs"]["source_ids"]
    assert risk["evidence_refs"]["evidence_bundle_ids"]


def test_degraded_inputs_create_quality_risks_without_market_stress() -> None:
    evidence, signals, regime = _linked_inputs(stale_assets={"SPY"})
    artifact = _monitor(evidence, signals, regime)

    assert artifact["status"] == "partial"
    assert artifact["category_counts"]["data_quality"] >= 3
    assert artifact["category_counts"]["market_stress"] == 0
    assert _by_rule(artifact, "input_coverage_degraded_v1")
    assert _by_rule(artifact, "market_signal_coverage_degraded_v1")
    assert _by_rule(artifact, "market_regime_coverage_degraded_v1")


def test_current_risk_off_conditions_emit_observed_stress_items() -> None:
    evidence, signals, regime = _linked_inputs(
        values={
            "SPY": -1.0,
            "QQQ": -1.2,
            "BTC-USD": -0.8,
            "ETH-USD": -0.7,
            "VIX": 0.5,
            "DXY": 0.8,
            "US10Y": 2.0,
        }
    )
    artifact = _monitor(evidence, signals, regime)

    assert regime["classification"] == "risk_off"
    stress_rules = {
        item["rule_id"]
        for item in artifact["risks"]
        if item["category"] == "market_stress"
    }
    assert stress_rules == {
        "observed_risk_off_regime_v1",
        "observed_equity_volatility_stress_v1",
        "observed_equity_crypto_stress_v1",
        "observed_dollar_yield_pressure_v1",
    }
    assert all(
        item["status"] == "observed"
        for item in artifact["risks"]
        if item["category"] == "market_stress"
    )


def test_current_equity_divergence_is_reported_without_outlook() -> None:
    evidence, signals, regime = _linked_inputs(values={"SPY": 0.6, "QQQ": -0.6})
    artifact = _monitor(evidence, signals, regime)
    risks = _by_rule(artifact, "observed_equity_divergence_v1")

    assert len(risks) == 1
    assert risks[0]["attention_level"] == "medium"
    assert set(risks[0]["evidence_refs"]["observation_ids"]) == {
        "obs_spy_daily",
        "obs_qqq_daily",
    }
    assert "prediction" not in risks[0]
    assert "recommendation" not in risks[0]


def test_current_risk_on_fixture_does_not_create_market_stress() -> None:
    evidence, signals, regime = _linked_inputs()
    artifact = _monitor(evidence, signals, regime)

    assert regime["classification"] == "risk_on"
    assert artifact["status"] == "available"
    assert artifact["category_counts"] == {
        "upcoming_event": 0,
        "data_quality": 0,
        "market_stress": 0,
    }


def test_stale_evidence_artifact_suppresses_upcoming_event() -> None:
    calendar = _calendar()
    calendar["events"][0]["scheduled_at"] = "2026-08-27T18:00:00Z"
    evidence, signals, regime = _linked_inputs(calendar=calendar)
    artifact = _monitor(
        evidence,
        signals,
        regime,
        now=NOW + timedelta(hours=25),
    )

    assert not _by_rule(artifact, "upcoming_official_event_v1")
    stale_items = _by_rule(artifact, "input_artifact_stale_v1")
    assert len(stale_items) == 3
    assert artifact["category_counts"]["market_stress"] == 0


def test_every_risk_has_resolvable_evidence_references() -> None:
    evidence, signals, regime = _linked_inputs(
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
    artifact = _monitor(evidence, signals, regime)
    bundle_ids = {item["id"] for item in evidence["bundles"]}
    source_ids = {
        item["source_id"]
        for bundle in evidence["bundles"]
        for item in bundle["source_records"]
    }
    observation_ids = {
        item["observation_id"]
        for bundle in evidence["bundles"]
        for item in bundle["observations"]
    }
    event_ids = {
        item["event_id"]
        for bundle in evidence["bundles"]
        for item in bundle["events"]
    }
    signal_ids = {item["signal_id"] for item in signals["signals"]}

    for risk in artifact["risks"]:
        refs = risk["evidence_refs"]
        assert refs["artifact_run_ids"]
        assert set(refs["evidence_bundle_ids"]).issubset(bundle_ids)
        assert set(refs["source_ids"]).issubset(source_ids)
        assert set(refs["observation_ids"]).issubset(observation_ids)
        assert set(refs["event_ids"]).issubset(event_ids)
        assert set(refs["signal_ids"]).issubset(signal_ids)


def test_linkage_mismatch_and_future_input_are_rejected() -> None:
    evidence, signals, regime = _linked_inputs()
    mismatched = copy.deepcopy(regime)
    mismatched["input_refs"]["market_signals_run_id"] = "run_other"
    with pytest.raises(ValueError):
        build_risk_monitor_artifact(evidence, signals, mismatched, now=NOW)

    with pytest.raises(RiskMonitorError, match="future-dated"):
        build_risk_monitor_artifact(
            evidence,
            signals,
            regime,
            now=NOW - timedelta(minutes=6),
        )


def test_validator_rejects_tampering_and_prohibited_fields() -> None:
    evidence, signals, regime = _linked_inputs(calendar=_calendar())
    artifact = _monitor(evidence, signals, regime)

    tampered = copy.deepcopy(artifact)
    tampered["risks"][0]["attention_level"] = "low"
    with pytest.raises(
        RiskMonitorValidationError,
        match="does not match deterministic evaluation",
    ):
        validate_risk_monitor_artifact(tampered, evidence, signals, regime)

    prohibited = copy.deepcopy(artifact)
    prohibited["prediction"] = "market crash"
    with pytest.raises(
        RiskMonitorValidationError,
        match="prohibited Phase 6.3-C field",
    ):
        validate_risk_monitor_artifact(prohibited, evidence, signals, regime)


def test_pipeline_reads_three_artifact_types_and_writes_atomically(
    tmp_path: Path,
) -> None:
    evidence, signals, regime = _linked_inputs(calendar=_calendar())
    evidence_path = tmp_path / "evidence_bundle.json"
    signals_path = tmp_path / "market_signals.json"
    regime_path = tmp_path / "market_regime.json"
    output_path = tmp_path / "risk_monitor.json"
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
    signals_path.write_text(json.dumps(signals), encoding="utf-8")
    regime_path.write_text(json.dumps(regime), encoding="utf-8")

    result = run_risk_monitor_pipeline(
        evidence_path,
        signals_path,
        regime_path,
        output_path,
    )

    written = json.loads(output_path.read_text(encoding="utf-8"))
    validate_freshness_contract(written)
    assert strip_freshness_metadata(written) == result.to_dict()
    assert not (tmp_path / "risk_monitor.json.tmp").exists()

    wrong = tmp_path / "wrong.json"
    wrong.write_text(json.dumps({"artifact_type": "events"}), encoding="utf-8")
    with pytest.raises(RiskMonitorInputError, match="requires market_regime"):
        run_risk_monitor_pipeline(evidence_path, signals_path, wrong, output_path)
