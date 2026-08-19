from __future__ import annotations

import copy
import json

import pytest

from src.evidence.builder import (
    build_evidence_artifact,
    build_observation_artifact,
)
from src.evidence.pipeline import run_evidence_pipeline
from src.evidence.validator import (
    EvidenceValidationError,
    validate_evidence_artifact,
    validate_observation_artifact,
)


def _snapshot(status: str = "success") -> dict:
    return {
        "schema_version": "1.0",
        "generated_at": "2026-08-18T01:30:00Z",
        "source": "yahoo_finance",
        "change_unit": "percent",
        "volatility_unit": "annualized_percent",
        "records": [
            {
                "symbol": "SPY",
                "asset_type": "equity",
                "price": 100.5 if status != "failed" else None,
                "daily_change": -1.2 if status != "failed" else None,
                "weekly_change": 2.4 if status != "failed" else None,
                "sma20": 101.0 if status != "failed" else None,
                "volatility_20d": 18.5 if status != "failed" else None,
                "trend": "below_sma20" if status != "failed" else "unavailable",
                "timestamp": "2026-08-17T20:00:00Z",
                "source": "yahoo_finance",
                "status": status,
            }
        ],
    }


def _artifacts(status: str = "success") -> tuple[dict, dict]:
    observations = build_observation_artifact(_snapshot(status))
    evidence = build_evidence_artifact(observations)
    return observations, evidence


def test_snapshot_builds_canonical_observations_and_market_move_evidence() -> None:
    observations, evidence = _artifacts()

    assert observations["artifact_type"] == "observations"
    assert observations["status"] == "complete"
    assert len(observations["observations"]) == 6
    assert {item["metric"] for item in observations["observations"]} == {
        "price",
        "daily_change_pct",
        "weekly_change_pct",
        "sma20",
        "volatility_20d",
        "trend",
    }
    assert observations["sources"][0]["source_id"] == "src_yahoo_finance"

    bundle = evidence["evidence"][0]
    assert evidence["status"] == "complete"
    assert bundle["claim_type"] == "market_move"
    assert bundle["relation"] == "observed"
    assert bundle["statement"] == (
        "SPY decreased 1.2% over the latest daily interval."
    )
    assert bundle["event_ids"] == []
    assert bundle["confidence_score"] == 0.95
    assert "do not identify the cause" in bundle["limitations"][0]


def test_artifact_ids_and_payloads_are_deterministic() -> None:
    first = _artifacts()
    second = _artifacts()

    assert first == second
    assert first[0]["run_id"] == "run_2026_08_18t01_30_00z"
    assert first[0]["observations"][0]["observation_id"].startswith(
        "obs_spy_price_"
    )


def test_report_date_uses_configured_taipei_timezone() -> None:
    snapshot = _snapshot()
    snapshot["generated_at"] = "2026-08-18T17:30:00Z"

    artifact = build_observation_artifact(snapshot)

    assert artifact["report_date"] == "2026-08-19"


def test_stale_observation_lowers_confidence_and_marks_partial() -> None:
    observations, evidence = _artifacts("stale")

    assert observations["status"] == "partial"
    assert observations["observations"][0]["status"] == "stale"
    assert evidence["status"] == "partial"
    assert evidence["evidence"][0]["confidence_score"] == 0.65
    assert evidence["evidence"][0]["confidence_label"] == "medium"
    assert "stale" in evidence["evidence"][0]["limitations"][1]


def test_failed_market_record_produces_failed_empty_artifacts() -> None:
    observations, evidence = _artifacts("failed")

    assert observations["status"] == "failed"
    assert observations["observations"] == []
    assert evidence["status"] == "failed"
    assert evidence["evidence"] == []
    assert "status is failed" in observations["warnings"][0]


def test_valid_artifacts_pass_guardrails() -> None:
    observations, evidence = _artifacts()

    validate_observation_artifact(observations)
    validate_evidence_artifact(evidence, observations)


def test_validator_rejects_unsupported_causal_claim() -> None:
    observations, evidence = _artifacts()
    invalid = copy.deepcopy(evidence)
    invalid["evidence"][0]["statement"] = (
        "The Fed caused SPY to decrease 1.2%."
    )

    with pytest.raises(EvidenceValidationError, match="causal language"):
        validate_evidence_artifact(invalid, observations)

    invalid["evidence"][0]["statement"] = "由於聯儲局行動，SPY 下跌 1.2%。"
    with pytest.raises(EvidenceValidationError, match="causal language"):
        validate_evidence_artifact(invalid, observations)


def test_validator_rejects_unknown_observation_and_unsupported_number() -> None:
    observations, evidence = _artifacts()
    unknown = copy.deepcopy(evidence)
    unknown["evidence"][0]["observation_ids"] = ["obs_missing"]
    with pytest.raises(EvidenceValidationError, match="unknown observation"):
        validate_evidence_artifact(unknown, observations)

    unsupported = copy.deepcopy(evidence)
    unsupported["evidence"][0]["statement"] = (
        "SPY decreased 9.9% over the latest daily interval."
    )
    with pytest.raises(EvidenceValidationError, match="unsupported number"):
        validate_evidence_artifact(unsupported, observations)

    no_source = copy.deepcopy(evidence)
    no_source["evidence"][0]["supporting_source_ids"] = []
    with pytest.raises(EvidenceValidationError, match="no supporting source"):
        validate_evidence_artifact(no_source, observations)

    invalid_time = copy.deepcopy(observations)
    invalid_time["observations"][0]["as_of"] = "not-a-timestamp"
    with pytest.raises(EvidenceValidationError, match="as_of is invalid"):
        validate_observation_artifact(invalid_time)


def test_pipeline_validates_before_writing_both_artifacts(tmp_path) -> None:
    snapshot_path = tmp_path / "market_snapshot.json"
    observations_path = tmp_path / "observations.json"
    evidence_path = tmp_path / "evidence.json"
    snapshot_path.write_text(json.dumps(_snapshot()), encoding="utf-8")

    observations, evidence = run_evidence_pipeline(
        snapshot_path=snapshot_path,
        observations_path=observations_path,
        evidence_path=evidence_path,
    )

    assert json.loads(observations_path.read_text(encoding="utf-8")) == observations
    assert json.loads(evidence_path.read_text(encoding="utf-8")) == evidence
    assert evidence["evidence"][0]["supporting_source_ids"] == [
        "src_yahoo_finance"
    ]
