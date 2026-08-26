from __future__ import annotations

import copy
import json
from datetime import timedelta
from pathlib import Path

import pytest

from src.regime.classifier import (
    RegimeClassificationError,
    build_market_regime_artifact,
)
from src.regime.pipeline import (
    MarketRegimeInputError,
    run_market_regime_pipeline,
)
from src.regime.validator import (
    MarketRegimeValidationError,
    validate_market_regime_artifact,
)
from tests.test_cross_asset_signals import NOW, _evidence_bundle, _signals


def _regime(bundle: dict, signals: dict, now=NOW) -> dict:
    artifact = build_market_regime_artifact(bundle, signals, now=now).to_dict()
    validate_market_regime_artifact(artifact, bundle, signals)
    return artifact


def test_complete_current_inputs_classify_risk_on() -> None:
    bundle = _evidence_bundle()
    artifact = _regime(bundle, _signals(bundle))

    assert artifact["status"] == "available"
    assert artifact["classification"] == "risk_on"
    assert artifact["classification_scope"] == "current_observed_conditions"
    assert artifact["score"]["eligible_dimension_count"] == 5
    assert artifact["score"]["eligible_weight"] == 1.0
    assert {item["observed_state"] for item in artifact["dimensions"]} == {
        "risk_on"
    }


def test_complete_current_inputs_classify_risk_off() -> None:
    bundle = _evidence_bundle(
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
    artifact = _regime(bundle, _signals(bundle))

    assert artifact["classification"] == "risk_off"
    assert artifact["score"]["normalized_score"] == -1.0


def test_conflicting_current_dimensions_classify_mixed() -> None:
    bundle = _evidence_bundle(
        values={
            "SPY": 1.0,
            "QQQ": 1.2,
            "BTC-USD": -0.8,
            "ETH-USD": -0.7,
            "VIX": 0.5,
            "DXY": -0.8,
            "US10Y": -2.0,
        }
    )
    artifact = _regime(bundle, _signals(bundle))

    assert artifact["classification"] == "mixed"
    assert artifact["score"]["normalized_score"] == 0.0
    states = {
        item["dimension_id"]: item["observed_state"]
        for item in artifact["dimensions"]
    }
    assert states == {
        "equity": "risk_on",
        "volatility": "risk_off",
        "crypto": "risk_off",
        "dollar_yield": "risk_on",
        "cross_asset_alignment": "mixed",
    }


def test_stale_evidence_returns_null_instead_of_mixed() -> None:
    bundle = _evidence_bundle(stale_assets={"SPY"})
    artifact = _regime(bundle, _signals(bundle))

    assert artifact["status"] == "unavailable"
    assert artifact["classification"] is None
    assert artifact["confidence"]["score"] == 0.0
    assert artifact["input_freshness"]["status"] == "stale"


def test_partial_but_sufficient_current_coverage_can_classify() -> None:
    bundle = _evidence_bundle(omitted_assets={"BTC-USD"})
    artifact = _regime(bundle, _signals(bundle))

    assert artifact["status"] == "partial"
    assert artifact["classification"] == "risk_on"
    assert artifact["score"]["eligible_dimension_count"] == 3
    assert artifact["score"]["eligible_weight"] == 0.7
    unavailable = {
        item["dimension_id"]
        for item in artifact["dimensions"]
        if item["eligibility"] == "unavailable"
    }
    assert unavailable == {"crypto", "cross_asset_alignment"}


def test_stale_observation_only_disables_dependent_dimensions() -> None:
    bundle = _evidence_bundle(stale_assets={"DXY"})
    artifact = _regime(bundle, _signals(bundle))

    assert artifact["status"] == "partial"
    assert artifact["classification"] == "risk_on"
    assert artifact["input_freshness"]["status"] == "stale"
    unavailable = {
        item["dimension_id"]
        for item in artifact["dimensions"]
        if item["eligibility"] == "unavailable"
    }
    assert unavailable == {"dollar_yield"}


def test_old_artifacts_fail_closed_even_when_observations_were_current() -> None:
    bundle = _evidence_bundle()
    signals = _signals(bundle)
    artifact = _regime(bundle, signals, now=NOW + timedelta(hours=25))

    assert artifact["classification"] is None
    assert artifact["status"] == "unavailable"
    assert artifact["input_freshness"]["stale_artifacts"] == [
        "evidence_bundle.json",
        "market_signals.json",
    ]
    assert all(
        item["eligibility"] == "unavailable" for item in artifact["dimensions"]
    )


def test_input_linkage_and_future_timestamps_are_rejected() -> None:
    bundle = _evidence_bundle()
    signals = _signals(bundle)
    mismatched = copy.deepcopy(signals)
    mismatched["input_run_id"] = "run_different"
    with pytest.raises(ValueError):
        build_market_regime_artifact(bundle, mismatched, now=NOW)

    with pytest.raises(RegimeClassificationError, match="future-dated"):
        build_market_regime_artifact(
            bundle,
            signals,
            now=NOW - timedelta(minutes=6),
        )


def test_provenance_is_preserved_and_confidence_is_data_based() -> None:
    bundle = _evidence_bundle(confidence={"SPY": 0.85, "QQQ": 0.8})
    artifact = _regime(bundle, _signals(bundle))
    equity = next(
        item for item in artifact["dimensions"] if item["dimension_id"] == "equity"
    )

    assert equity["confidence"]["basis"] == "data_quality"
    assert equity["evidence_refs"]["observation_ids"] == [
        "obs_qqq_daily",
        "obs_spy_daily",
    ]
    assert set(equity["evidence_refs"]["observation_ids"]).issubset(
        artifact["evidence_refs"]["observation_ids"]
    )


def test_validator_rejects_tampering_and_predictive_fields() -> None:
    bundle = _evidence_bundle()
    signals = _signals(bundle)
    artifact = _regime(bundle, signals)

    tampered = copy.deepcopy(artifact)
    tampered["classification"] = "risk_off"
    with pytest.raises(
        MarketRegimeValidationError,
        match="does not match deterministic classification",
    ):
        validate_market_regime_artifact(tampered, bundle, signals)

    prohibited = copy.deepcopy(artifact)
    prohibited["prediction"] = "prices will rise"
    with pytest.raises(
        MarketRegimeValidationError,
        match="prohibited Phase 6.3-B field",
    ):
        validate_market_regime_artifact(prohibited, bundle, signals)


def test_pipeline_reads_exactly_two_artifact_types_and_writes_atomically(
    tmp_path: Path,
) -> None:
    bundle = _evidence_bundle()
    signals = _signals(bundle)
    evidence_path = tmp_path / "evidence_bundle.json"
    signals_path = tmp_path / "market_signals.json"
    output_path = tmp_path / "market_regime.json"
    evidence_path.write_text(json.dumps(bundle), encoding="utf-8")
    signals_path.write_text(json.dumps(signals), encoding="utf-8")

    result = run_market_regime_pipeline(
        evidence_path,
        signals_path,
        output_path,
    )

    assert json.loads(output_path.read_text(encoding="utf-8")) == result.to_dict()
    assert not (tmp_path / "market_regime.json.tmp").exists()

    wrong_path = tmp_path / "wrong.json"
    wrong_path.write_text(json.dumps({"artifact_type": "events"}), encoding="utf-8")
    with pytest.raises(MarketRegimeInputError, match="requires market_signals"):
        run_market_regime_pipeline(evidence_path, wrong_path, output_path)
