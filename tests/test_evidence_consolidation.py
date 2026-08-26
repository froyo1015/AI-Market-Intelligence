from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.consolidation.builder import build_consolidated_evidence_artifact
from src.consolidation.pipeline import run_consolidation_pipeline
from src.consolidation.validator import (
    ConsolidatedEvidenceValidationError,
    validate_consolidated_evidence_artifact,
)


NOW = datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc)
GENERATED_AT = "2026-08-26T11:00:00Z"


def _source(source_id: str, source_type: str = "market_data") -> dict:
    return {
        "source_id": source_id,
        "provider": "test_provider",
        "publisher": "Test Publisher",
        "source_type": source_type,
        "quality_tier": 3,
        "title": f"Source {source_id}",
        "url": "https://example.com/source",
        "published_at": None,
        "retrieved_at": GENERATED_AT,
        "content_hash": f"sha256:{'a' if 'market' in source_id else 'b'}" + "0" * 63,
    }


def _observation(
    observation_id: str,
    observation_type: str,
    subject: str,
    source_id: str,
    value: float,
    status: str = "success",
) -> dict:
    return {
        "observation_id": observation_id,
        "observation_type": observation_type,
        "subject": subject,
        "metric": "daily_change_pct",
        "value": value,
        "unit": "percent",
        "period": "daily",
        "as_of": "2026-08-26T10:00:00Z",
        "source_id": source_id,
        "status": status,
        "calculation": {
            "rule_id": "daily_change_v1",
            "input_ids": [],
            "source_artifact": "fixture.json",
        },
        "asset_mapping": [subject],
        "confidence_score": 0.95 if status == "success" else 0.65,
        "confidence_label": "high" if status == "success" else "medium",
    }


def _observations() -> dict:
    return {
        "schema_version": "1.1",
        "artifact_type": "observations",
        "run_id": "run_observations",
        "report_date": "2026-08-26",
        "generated_at": GENERATED_AT,
        "status": "complete",
        "warnings": [],
        "sources": [
            _source("src_market"),
            _source("src_macro", "macro_market_data"),
        ],
        "observations": [
            _observation(
                "obs_spy_daily",
                "market_feature",
                "SPY",
                "src_market",
                1.5,
            ),
            _observation(
                "obs_dxy_daily",
                "macro_value",
                "DXY",
                "src_macro",
                -0.8,
            ),
        ],
    }


def _evidence() -> dict:
    return {
        "schema_version": "1.1",
        "artifact_type": "evidence",
        "run_id": "run_observations",
        "report_date": "2026-08-26",
        "generated_at": GENERATED_AT,
        "status": "complete",
        "warnings": [],
        "evidence": [
            {
                "evidence_id": "evd_spy",
                "claim_type": "market_move",
                "statement": "SPY increased 1.5% over the latest daily interval.",
                "relation": "observed",
                "event_ids": [],
                "observation_ids": ["obs_spy_daily"],
                "supporting_source_ids": ["src_market"],
                "contradicting_evidence_ids": [],
                "confidence_score": 0.95,
                "confidence_label": "high",
                "affected_assets": ["SPY"],
                "limitations": ["The observation does not identify a cause."],
            },
            {
                "evidence_id": "evd_dxy",
                "claim_type": "macro_move",
                "statement": "DXY declined 0.8% over the latest daily interval.",
                "relation": "observed",
                "event_ids": [],
                "observation_ids": ["obs_dxy_daily"],
                "supporting_source_ids": ["src_macro"],
                "contradicting_evidence_ids": [],
                "confidence_score": 0.95,
                "confidence_label": "high",
                "affected_assets": ["DXY"],
                "limitations": ["The observation does not identify a cause."],
            },
        ],
    }


def _calendar(status: str = "complete") -> dict:
    return {
        "schema_version": "1.0",
        "artifact_type": "economic_calendar",
        "run_id": "run_calendar",
        "report_date": "2026-08-26",
        "generated_at": GENERATED_AT,
        "window_start": GENERATED_AT,
        "window_end": "2026-08-28T11:00:00Z",
        "source": "bls_release_calendar",
        "source_url": "https://www.bls.gov/schedule/news_release/bls.ics",
        "status": status,
        "failure_type": "source_access_error" if status == "failed" else None,
        "retryable": status == "failed",
        "warnings": ["Calendar unavailable"] if status == "failed" else [],
        "events": []
        if status == "failed"
        else [
            {
                "event_id": "evt_cpi",
                "event_type": "economic_event",
                "name": "Consumer Price Index",
                "scheduled_at": "2026-08-27T12:30:00Z",
                "country": "US",
                "impact": "high",
                "affected_assets": ["SPY", "DXY", "GOLD"],
                "topics": ["inflation"],
                "source": "bls_release_calendar",
                "publisher": "U.S. Bureau of Labor Statistics",
                "source_url": "https://www.bls.gov/schedule/news_release/cpi.htm",
                "retrieved_at": GENERATED_AT,
                "status": "scheduled",
                "confidence_score": 0.95,
                "confidence_label": "high",
                "provider_event_id": "cpi",
                "content_hash": f"sha256:{'c' * 64}",
            }
        ],
    }


def _news_events() -> dict:
    return {
        "schema_version": "1.1",
        "artifact_type": "events",
        "run_id": "run_news",
        "report_date": "2026-08-26",
        "generated_at": GENERATED_AT,
        "status": "complete",
        "warnings": [],
        "input_artifact": "news_items.json",
        "input_run_id": "run_news_items",
        "event_count": 1,
        "normalization_rejection_count": 0,
        "normalization_rejections": [],
        "events": [
            {
                "event_id": "evt_news_1234567890abcdef",
                "event_type": "central_bank",
                "status": "success",
                "title": "Federal Reserve issues FOMC statement",
                "summary": None,
                "occurred_at": None,
                "scheduled_at": None,
                "country_codes": ["US"],
                "entity_ids": [
                    "federal_reserve_board",
                    "federal_open_market_committee",
                ],
                "candidate_assets": [],
                "topics": ["monetary_policy"],
                "source_refs": [
                    {
                        "source_id": "src_news_1234567890abcdef",
                        "provider": "federal_reserve_press_releases",
                        "publisher": "Federal Reserve Board",
                        "source_type": "official",
                        "quality_tier": 1,
                        "title": "Federal Reserve issues FOMC statement",
                        "url": "https://www.federalreserve.gov/example.htm",
                        "published_at": "2026-08-26T10:30:00Z",
                        "retrieved_at": GENERATED_AT,
                        "content_hash": f"sha256:{'d' * 64}",
                    }
                ],
                "canonical_hash": f"sha256:{'e' * 64}",
                "duplicate_of": None,
                "normalization": {
                    "input_item_ids": ["nws_1"],
                    "method": "headline_rules",
                    "rule_version": "news_normalization_v1",
                    "normalized_action": "issues_policy_statement",
                    "event_key_fields": [
                        "event_type",
                        "entity_ids",
                        "normalized_action",
                    ],
                    "mapping_rule_ids": [],
                    "extraction_quality_score": 0.95,
                    "mapping_quality_score": 0.95,
                    "verification_level": "official",
                    "deduplication_rule_id": "single_item_v1",
                    "deduplication_score": 1.0,
                },
                "event_version": 1,
                "lifecycle_status": "confirmed",
                "lifecycle_updated_at": GENERATED_AT,
                "lifecycle_reason_code": "tier1_official_source_v1",
                "retraction_source_ids": [],
            }
        ],
    }


def _build(
    observations: dict | None = None,
    evidence: dict | None = None,
    calendar: dict | None = None,
    news: dict | None = None,
) -> dict:
    artifact = build_consolidated_evidence_artifact(
        observations if observations is not None else _observations(),
        evidence if evidence is not None else _evidence(),
        calendar if calendar is not None else _calendar(),
        news if news is not None else _news_events(),
        now=NOW,
    ).to_dict()
    validate_consolidated_evidence_artifact(artifact)
    return artifact


def test_combines_market_and_macro_evidence_without_losing_types() -> None:
    artifact = _build()

    assert artifact["status"] == "available"
    evidence_bundles = {
        bundle["evidence_records"][0]["evidence_id"]: bundle
        for bundle in artifact["bundles"]
        if bundle["type"] == "evidence_fact"
    }
    assert evidence_bundles["evd_spy"]["observations"][0]["observation_type"] == (
        "market_feature"
    )
    assert evidence_bundles["evd_dxy"]["observations"][0]["observation_type"] == (
        "macro_value"
    )
    assert evidence_bundles["evd_spy"]["related_assets"] == ["SPY"]
    assert evidence_bundles["evd_dxy"]["related_assets"] == ["DXY"]


def test_exact_duplicate_evidence_merges_and_preserves_every_record() -> None:
    observations = _observations()
    second_source = _source("src_market_two")
    second_source["provider"] = "second_test_provider"
    second_source["publisher"] = "Second Test Publisher"
    second_source["url"] = "https://second.example.com/source"
    second_observation = _observation(
        "obs_spy_daily_two",
        "market_feature",
        "SPY",
        "src_market_two",
        1.5,
    )
    observations["sources"].append(second_source)
    observations["observations"].append(second_observation)
    evidence = _evidence()
    duplicate = copy.deepcopy(evidence["evidence"][0])
    duplicate["evidence_id"] = "evd_spy_second_source_record"
    duplicate["observation_ids"] = ["obs_spy_daily_two"]
    duplicate["supporting_source_ids"] = ["src_market_two"]
    evidence["evidence"].append(duplicate)

    artifact = _build(observations=observations, evidence=evidence)
    matching = [
        bundle
        for bundle in artifact["bundles"]
        if bundle["type"] == "evidence_fact"
        and bundle["related_assets"] == ["SPY"]
    ]

    assert len(matching) == 1
    assert [
        item["evidence_id"] for item in matching[0]["evidence_records"]
    ] == ["evd_spy", "evd_spy_second_source_record"]
    assert matching[0]["provenance"]["evidence_ids"] == [
        "evd_spy",
        "evd_spy_second_source_record",
    ]
    assert matching[0]["provenance"]["source_ids"] == [
        "src_market",
        "src_market_two",
    ]
    assert matching[0]["provenance"]["observation_ids"] == [
        "obs_spy_daily",
        "obs_spy_daily_two",
    ]
    assert matching[0]["verification_level"] == "corroborated"


def test_missing_source_rejects_broken_chain_without_fake_evidence() -> None:
    observations = _observations()
    observations["sources"] = [
        source for source in observations["sources"] if source["source_id"] != "src_macro"
    ]

    artifact = _build(observations=observations)

    assert artifact["status"] == "partial"
    macro_coverage = next(
        item for item in artifact["coverage"] if item["input_type"] == "macro_observations"
    )
    assert macro_coverage["status"] == "unavailable"
    assert any(
        "missing_source_reference" in rejection["reason_codes"]
        for rejection in artifact["rejections"]
    )
    assert all(
        observation["observation_id"] != "obs_dxy_daily"
        for bundle in artifact["bundles"]
        for observation in bundle["observations"]
    )


def test_stale_observation_remains_stale_in_bundle_and_coverage() -> None:
    observations = _observations()
    observations["observations"][0]["status"] = "stale"
    observations["observations"][0]["confidence_score"] = 0.65
    observations["observations"][0]["confidence_label"] = "medium"
    observations["status"] = "partial"

    artifact = _build(observations=observations)
    spy_bundle = next(
        bundle
        for bundle in artifact["bundles"]
        if "obs_spy_daily" in bundle["provenance"]["observation_ids"]
    )

    assert artifact["status"] == "partial"
    assert spy_bundle["freshness"]["status"] == "mixed"
    assert spy_bundle["freshness"]["stale_record_ids"] == ["obs_spy_daily"]
    assert spy_bundle["data_quality"]["status"] == "partial"


def test_calendar_and_news_provenance_and_timestamps_are_preserved() -> None:
    artifact = _build()
    calendar_bundle = next(
        bundle for bundle in artifact["bundles"] if bundle["type"] == "calendar_event"
    )
    news_bundle = next(
        bundle for bundle in artifact["bundles"] if bundle["type"] == "news_event"
    )

    assert calendar_bundle["provenance"]["event_ids"] == ["evt_cpi"]
    assert calendar_bundle["timestamps"]["scheduled_at"] == [
        "2026-08-27T12:30:00Z"
    ]
    assert calendar_bundle["source_records"][0]["publisher"] == (
        "U.S. Bureau of Labor Statistics"
    )
    assert news_bundle["provenance"]["source_ids"] == [
        "src_news_1234567890abcdef"
    ]
    assert news_bundle["timestamps"]["published_at"] == [
        "2026-08-26T10:30:00Z"
    ]
    assert news_bundle["verification_level"] == "official"


def test_failed_calendar_is_unavailable_and_creates_no_fake_event() -> None:
    artifact = _build(calendar=_calendar("failed"))

    coverage = next(
        item for item in artifact["coverage"] if item["input_type"] == "economic_calendar"
    )
    assert coverage["status"] == "unavailable"
    assert not any(bundle["type"] == "calendar_event" for bundle in artifact["bundles"])
    assert artifact["status"] == "partial"


def test_validator_rejects_new_prediction_or_dangling_provenance() -> None:
    artifact = _build()
    predictive = copy.deepcopy(artifact)
    predictive["bundles"][0]["prediction"] = "BTC will rise"
    with pytest.raises(
        ConsolidatedEvidenceValidationError,
        match="prohibited Phase 6.2-D field",
    ):
        validate_consolidated_evidence_artifact(predictive)

    dangling = copy.deepcopy(artifact)
    dangling["bundles"][0]["provenance"]["source_ids"] = ["src_missing"]
    with pytest.raises(
        ConsolidatedEvidenceValidationError,
        match="source provenance mismatch",
    ):
        validate_consolidated_evidence_artifact(dangling)


def test_pipeline_writes_valid_artifact_atomically(tmp_path: Path) -> None:
    paths = {
        "observations": tmp_path / "observations.json",
        "evidence": tmp_path / "evidence.json",
        "calendar": tmp_path / "economic_calendar.json",
        "news": tmp_path / "events.json",
        "output": tmp_path / "evidence_bundle.json",
    }
    for key, payload in (
        ("observations", _observations()),
        ("evidence", _evidence()),
        ("calendar", _calendar()),
        ("news", _news_events()),
    ):
        paths[key].write_text(json.dumps(payload), encoding="utf-8")

    result = run_consolidation_pipeline(
        observations_path=paths["observations"],
        evidence_path=paths["evidence"],
        calendar_path=paths["calendar"],
        news_events_path=paths["news"],
        output_path=paths["output"],
    )

    written = json.loads(paths["output"].read_text(encoding="utf-8"))
    assert written == result.to_dict()
    assert written["artifact_type"] == "evidence_bundle"
    assert not (tmp_path / "evidence_bundle.json.tmp").exists()
