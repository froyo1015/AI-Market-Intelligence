from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Set, Tuple

import pytest

from src.consolidation.builder import build_consolidated_evidence_artifact
from src.consolidation.validator import validate_consolidated_evidence_artifact
from src.signals.engine import build_market_signals_artifact
from src.signals.pipeline import MarketSignalsInputError, run_market_signals_pipeline
from src.signals.rules import RULES
from src.signals.validator import (
    MarketSignalsValidationError,
    validate_market_signals_artifact,
)


NOW = datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc)
GENERATED_AT = "2026-08-26T11:00:00Z"
DEFAULT_VALUES = {
    "SPY": 1.0,
    "QQQ": 1.2,
    "BTC-USD": 0.8,
    "ETH-USD": 0.7,
    "VIX": -0.5,
    "GOLD": 1.5,
    "DXY": -0.8,
    "EURUSD": 0.6,
    "USDJPY": -0.4,
    "US10Y": -2.0,
}
MACRO_ASSETS = {"DXY", "US10Y", "VIX"}


def _source(source_id: str, macro: bool) -> dict:
    return {
        "source_id": source_id,
        "provider": "fixture_provider",
        "publisher": "Fixture Publisher",
        "source_type": "macro_market_data" if macro else "market_data",
        "quality_tier": 3,
        "title": f"Fixture source for {source_id}",
        "url": "https://example.com/data",
        "published_at": None,
        "retrieved_at": GENERATED_AT,
        "content_hash": f"sha256:{source_id[-1].lower() * 64}",
    }


def _inputs(
    values: Optional[Dict[str, float]] = None,
    stale_assets: Optional[Set[str]] = None,
    omitted_assets: Optional[Set[str]] = None,
    times: Optional[Dict[str, str]] = None,
    confidence: Optional[Dict[str, float]] = None,
    duplicate_assets: Optional[Set[str]] = None,
    equivalent_duplicate_assets: Optional[Set[str]] = None,
) -> Tuple[dict, dict, dict, dict]:
    actual_values = dict(DEFAULT_VALUES)
    actual_values.update(values or {})
    stale = stale_assets or set()
    omitted = omitted_assets or set()
    timestamps = times or {}
    scores = confidence or {}
    duplicates = duplicate_assets or set()
    equivalent_duplicates = equivalent_duplicate_assets or set()
    sources = []
    observations = []
    evidence_records = []

    for index, (asset, value) in enumerate(actual_values.items()):
        if asset in omitted:
            continue
        source_id = f"src_{index:x}"
        macro = asset in MACRO_ASSETS
        sources.append(_source(source_id, macro))
        metric = "daily_change_bps" if asset == "US10Y" else "daily_change_pct"
        unit = "basis_points" if asset == "US10Y" else "percent"
        observation_id = f"obs_{asset.casefold().replace('-', '_')}_daily"
        status = "stale" if asset in stale else "success"
        score = scores.get(asset, 0.95 if status == "success" else 0.65)
        observation = {
            "observation_id": observation_id,
            "observation_type": "macro_value" if macro else "market_feature",
            "subject": asset,
            "metric": metric,
            "value": value,
            "unit": unit,
            "period": "daily",
            "as_of": timestamps.get(asset, "2026-08-26T10:00:00Z"),
            "source_id": source_id,
            "status": status,
            "calculation": {
                "rule_id": "fixture_daily_change_v1",
                "input_ids": [],
                "source_artifact": "fixture.json",
            },
            "asset_mapping": [asset],
            "confidence_score": score,
            "confidence_label": (
                "high" if score >= 0.8 else "medium" if score >= 0.55 else "low"
            ),
        }
        observations.append(observation)
        evidence_records.append(_evidence_record(asset, observation, source_id))
        if asset in duplicates or asset in equivalent_duplicates:
            duplicate = copy.deepcopy(observation)
            duplicate["observation_id"] = f"{observation_id}_duplicate"
            if asset in duplicates:
                duplicate["value"] = value + 0.1
            observations.append(duplicate)
            evidence_records.append(_evidence_record(asset, duplicate, source_id))

    observations_artifact = {
        "schema_version": "1.1",
        "artifact_type": "observations",
        "run_id": "run_signal_observations",
        "report_date": "2026-08-26",
        "generated_at": GENERATED_AT,
        "status": "partial" if stale else "complete",
        "warnings": ["Fixture contains stale data."] if stale else [],
        "sources": sources,
        "observations": observations,
    }
    evidence_artifact = {
        "schema_version": "1.1",
        "artifact_type": "evidence",
        "run_id": "run_signal_observations",
        "report_date": "2026-08-26",
        "generated_at": GENERATED_AT,
        "status": "partial" if stale else "complete",
        "warnings": ["Fixture contains stale data."] if stale else [],
        "evidence": evidence_records,
    }
    calendar_artifact = {
        "schema_version": "1.0",
        "artifact_type": "economic_calendar",
        "run_id": "run_signal_calendar",
        "report_date": "2026-08-26",
        "generated_at": GENERATED_AT,
        "status": "complete",
        "warnings": [],
        "events": [],
    }
    news_artifact = {
        "schema_version": "1.1",
        "artifact_type": "events",
        "run_id": "run_signal_news",
        "report_date": "2026-08-26",
        "generated_at": GENERATED_AT,
        "status": "complete",
        "warnings": [],
        "events": [],
    }
    return (
        observations_artifact,
        evidence_artifact,
        calendar_artifact,
        news_artifact,
    )


def _evidence_record(asset: str, observation: dict, source_id: str) -> dict:
    value = observation["value"]
    unit = observation["unit"]
    return {
        "evidence_id": f"evd_{observation['observation_id']}",
        "claim_type": "observed_daily_change",
        "statement": f"{asset} recorded a daily change of {value} {unit}.",
        "relation": "observed",
        "event_ids": [],
        "observation_ids": [observation["observation_id"]],
        "supporting_source_ids": [source_id],
        "contradicting_evidence_ids": [],
        "confidence_score": observation["confidence_score"],
        "confidence_label": observation["confidence_label"],
        "affected_assets": [asset],
        "limitations": ["The observation does not establish a cause."],
    }


def _evidence_bundle(**kwargs) -> dict:
    inputs = _inputs(**kwargs)
    artifact = build_consolidated_evidence_artifact(
        *inputs,
        now=NOW,
    ).to_dict()
    validate_consolidated_evidence_artifact(artifact)
    return artifact


def _signals(bundle: dict) -> dict:
    artifact = build_market_signals_artifact(bundle, now=NOW).to_dict()
    validate_market_signals_artifact(artifact, bundle)
    return artifact


def _by_rule(artifact: dict) -> dict[str, dict]:
    return {item["rule_id"]: item for item in artifact["signals"]}


def test_all_rules_are_evaluated_and_fresh_relationships_are_observed() -> None:
    artifact = _signals(_evidence_bundle())
    rules = _by_rule(artifact)

    assert artifact["status"] == "available"
    assert artifact["signal_count"] == len(RULES) == 8
    assert set(rules) == {rule.rule_id for rule in RULES}
    assert artifact["observed_count"] == 7
    assert rules["equity_index_divergence_v1"]["state"] == "not_observed"
    assert rules["gold_dollar_inverse_move_v1"]["state"] == "observed"
    assert rules["dollar_fx_quote_alignment_v1"]["state"] == "observed"
    assert all(item["signal_type"] == "cross_asset_relationship" for item in rules.values())


def test_divergence_rule_describes_observed_difference_without_direction_label() -> None:
    artifact = _signals(
        _evidence_bundle(values={"SPY": 0.6, "QQQ": -0.6})
    )
    signal = _by_rule(artifact)["equity_index_divergence_v1"]

    assert signal["state"] == "observed"
    assert signal["condition_met"] is True
    assert signal["rule_evaluation"]["spread_threshold"] == 1.0
    assert "direction" not in signal
    assert "strength" not in signal


def test_stale_data_cannot_be_promoted_to_observed() -> None:
    artifact = _signals(_evidence_bundle(stale_assets={"GOLD"}))
    signal = _by_rule(artifact)["gold_dollar_inverse_move_v1"]

    assert signal["condition_met"] is True
    assert signal["state"] == "stale_data"
    assert signal["confidence"]["score"] <= 0.5
    assert signal["data_quality"]["stale_observation_ids"] == ["obs_gold_daily"]


def test_missing_input_only_degrades_affected_rules() -> None:
    artifact = _signals(_evidence_bundle(omitted_assets={"DXY"}))
    rules = _by_rule(artifact)

    assert rules["gold_dollar_inverse_move_v1"]["state"] == "insufficient_data"
    assert rules["dollar_fx_quote_alignment_v1"]["state"] == "insufficient_data"
    assert rules["dollar_yield_co_movement_v1"]["state"] == "insufficient_data"
    assert rules["crypto_co_movement_v1"]["state"] == "observed"
    assert rules["gold_dollar_inverse_move_v1"]["condition_met"] is None


def test_time_gap_and_conflicting_observations_fail_closed() -> None:
    old_vix = _signals(
        _evidence_bundle(times={"VIX": "2026-08-24T10:00:00Z"})
    )
    time_signal = _by_rule(old_vix)["equity_volatility_inverse_move_v1"]
    assert time_signal["state"] == "insufficient_data"
    assert "observation_time_gap_exceeded" in time_signal["data_quality"]["issues"]

    conflicting = _signals(_evidence_bundle(duplicate_assets={"DXY"}))
    conflict_signal = _by_rule(conflicting)["gold_dollar_inverse_move_v1"]
    assert conflict_signal["state"] == "insufficient_data"
    assert "DXY:daily_change_pct" in conflict_signal["data_quality"][
        "conflicting_inputs"
    ]


def test_equivalent_multi_source_values_keep_all_references() -> None:
    artifact = _signals(
        _evidence_bundle(equivalent_duplicate_assets={"DXY"})
    )
    signal = _by_rule(artifact)["gold_dollar_inverse_move_v1"]

    assert signal["state"] == "observed"
    assert signal["evidence_refs"]["observation_ids"] == [
        "obs_dxy_daily",
        "obs_dxy_daily_duplicate",
        "obs_gold_daily",
    ]
    assert len(
        [item for item in signal["observed_values"] if item["asset"] == "DXY"]
    ) == 2


def test_confidence_uses_minimum_input_score_and_preserves_provenance() -> None:
    bundle = _evidence_bundle(confidence={"GOLD": 0.9, "DXY": 0.7})
    signal = _by_rule(_signals(bundle))["gold_dollar_inverse_move_v1"]

    assert signal["confidence"] == {
        "score": 0.7,
        "label": "medium",
        "basis": "data_quality",
    }
    assert signal["evidence_refs"]["observation_ids"] == [
        "obs_dxy_daily",
        "obs_gold_daily",
    ]
    assert len(signal["evidence_refs"]["evidence_bundle_ids"]) == 2
    assert set(signal["evidence_refs"]["source_ids"]) == {
        next(
            item["source_id"]
            for item in signal["observed_values"]
            if item["asset"] == "DXY"
        ),
        next(
            item["source_id"]
            for item in signal["observed_values"]
            if item["asset"] == "GOLD"
        ),
    }


def test_validator_rejects_directional_fields_and_tampered_values() -> None:
    bundle = _evidence_bundle()
    artifact = _signals(bundle)
    directional = copy.deepcopy(artifact)
    directional["signals"][0]["direction"] = "up"
    with pytest.raises(
        MarketSignalsValidationError,
        match="prohibited Phase 6.3-A field",
    ):
        validate_market_signals_artifact(directional, bundle)

    tampered = copy.deepcopy(artifact)
    tampered["signals"][0]["observed_values"][0]["value"] = 99.0
    with pytest.raises(
        MarketSignalsValidationError,
        match="does not match deterministic rule evaluation",
    ):
        validate_market_signals_artifact(tampered, bundle)


def test_pipeline_uses_one_input_and_writes_atomically(tmp_path: Path) -> None:
    input_path = tmp_path / "evidence_bundle.json"
    output_path = tmp_path / "market_signals.json"
    input_path.write_text(json.dumps(_evidence_bundle()), encoding="utf-8")

    result = run_market_signals_pipeline(input_path, output_path)

    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written == result.to_dict()
    assert written["input_artifact"] == "evidence_bundle.json"
    assert not (tmp_path / "market_signals.json.tmp").exists()

    invalid_path = tmp_path / "observations.json"
    invalid_path.write_text(json.dumps({"artifact_type": "observations"}), encoding="utf-8")
    with pytest.raises(MarketSignalsInputError, match="only evidence_bundle"):
        run_market_signals_pipeline(invalid_path, output_path)
