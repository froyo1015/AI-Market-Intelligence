from __future__ import annotations

from src.data.freshness import (
    aggregate_freshness_fields,
    enrich_artifact_freshness,
    validate_freshness_contract,
    validate_freshness_summary,
)


def _artifact(**overrides: object) -> dict:
    payload = {
        "schema_version": "1.0",
        "artifact_type": "market_snapshot",
        "status": "success",
        "generated_at": "2026-08-28T12:00:00Z",
        "records": [
            {
                "symbol": "SPY",
                "status": "success",
                "timestamp": "2026-08-28T11:00:00Z",
                "retrieved_at": "2026-08-28T11:05:00Z",
            }
        ],
    }
    payload.update(overrides)
    return payload


def test_current_data_uses_source_timestamp_age() -> None:
    result = enrich_artifact_freshness(_artifact())

    validate_freshness_contract(result)
    assert result["source_timestamp"] == "2026-08-28T11:00:00Z"
    assert result["retrieved_at"] == "2026-08-28T11:05:00Z"
    assert result["age_seconds"] == 3600.0
    assert result["freshness_status"] == "current"


def test_stale_data_exceeds_artifact_threshold() -> None:
    result = enrich_artifact_freshness(
        _artifact(generated_at="2026-09-01T12:00:00Z")
    )

    validate_freshness_contract(result)
    assert result["freshness_status"] == "stale"


def test_unavailable_source_has_no_age() -> None:
    result = enrich_artifact_freshness(
        _artifact(status="failed", records=[])
    )

    validate_freshness_contract(result)
    assert result["freshness_status"] == "unavailable"
    assert result["retrieved_at"] is None
    assert result["age_seconds"] is None


def test_unknown_freshness_has_no_invented_timestamp() -> None:
    result = enrich_artifact_freshness(
        {
            "schema_version": "1.0",
            "artifact_type": "market_signals",
            "status": "complete",
            "generated_at": "2026-08-28T12:00:00Z",
            "signals": [],
        }
    )

    validate_freshness_contract(result)
    assert result["source_timestamp"] is None
    assert result["retrieved_at"] is None
    assert result["freshness_status"] == "unknown"
    assert result["age_seconds"] is None


def test_manifest_aggregation_preserves_oldest_source_and_worst_status() -> None:
    records = [
        {
            "source_timestamp": "2026-08-28T10:00:00Z",
            "retrieved_at": "2026-08-28T10:05:00Z",
            "generated_at": "2026-08-28T11:00:00Z",
            "age_seconds": 3600.0,
            "freshness_status": "current",
        },
        {
            "source_timestamp": "2026-08-25T10:00:00Z",
            "retrieved_at": "2026-08-28T11:30:00Z",
            "generated_at": "2026-08-28T11:45:00Z",
            "age_seconds": 265500.0,
            "freshness_status": "stale",
        },
    ]

    result = aggregate_freshness_fields(records, "2026-08-28T12:00:00Z")

    validate_freshness_summary(result)
    assert result == {
        "source_timestamp": "2026-08-25T10:00:00Z",
        "retrieved_at": "2026-08-28T11:30:00Z",
        "generated_at": "2026-08-28T12:00:00Z",
        "age_seconds": 266400.0,
        "freshness_status": "stale",
    }


def test_manifest_aggregation_does_not_mask_unavailable_input() -> None:
    result = aggregate_freshness_fields(
        [
            {
                "source_timestamp": "2026-08-28T10:00:00Z",
                "retrieved_at": "2026-08-28T10:05:00Z",
                "generated_at": "2026-08-28T11:00:00Z",
                "age_seconds": 3600.0,
                "freshness_status": "current",
            },
            {
                "source_timestamp": None,
                "retrieved_at": None,
                "generated_at": "2026-08-28T11:00:00Z",
                "age_seconds": None,
                "freshness_status": "unavailable",
            },
        ],
        "2026-08-28T12:00:00Z",
    )

    validate_freshness_summary(result)
    assert result["freshness_status"] == "unavailable"
    assert result["age_seconds"] is None
