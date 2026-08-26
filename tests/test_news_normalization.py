from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.events.pipeline import (
    build_events_artifact,
    run_events_pipeline,
)
from src.events.validator import (
    NewsNormalizationValidationError,
    validate_events_artifact,
)


NOW = datetime(2026, 8, 19, 22, 0, tzinfo=timezone.utc)


def _item(
    item_id: str,
    headline: str,
    published_at: str = "2026-08-19T20:00:00Z",
) -> dict:
    suffix = item_id.rsplit("_", 1)[-1]
    return {
        "item_id": item_id,
        "provider_item_id": f"provider-{suffix}",
        "headline": headline,
        "source_excerpt": None,
        "publisher": "Board of Governors of the Federal Reserve System",
        "provider": "federal_reserve_press_releases",
        "source_type": "official",
        "quality_tier": 1,
        "source_url": (
            "https://www.federalreserve.gov/newsevents/pressreleases/"
            f"{suffix}.htm"
        ),
        "canonical_url": (
            "https://www.federalreserve.gov/newsevents/pressreleases/"
            f"{suffix}.htm"
        ),
        "published_at": published_at,
        "retrieved_at": "2026-08-19T21:00:00Z",
        "language": "en-us",
        "content_hash": f"sha256:{suffix[:1] * 64}",
    }


def _news_artifact(items: list[dict], status: str = "complete") -> dict:
    return {
        "schema_version": "1.0",
        "artifact_type": "news_items",
        "run_id": "run_20260819T210000Z_news",
        "report_date": "2026-08-20",
        "generated_at": "2026-08-19T21:00:00Z",
        "window_start": "2026-08-18T15:00:00Z",
        "window_end": "2026-08-19T21:05:00Z",
        "source": "federal_reserve_press_releases",
        "source_url": "https://www.federalreserve.gov/feeds/press_all.xml",
        "status": status,
        "failure_type": None,
        "retryable": False,
        "warnings": [],
        "accepted_count": len(items),
        "rejected_count": 0,
        "rejections": [],
        "items": items,
    }


def test_normalizes_official_fomc_item_without_intelligence_fields() -> None:
    source = _news_artifact(
        [_item("nws_fed_a", "Federal Reserve issues FOMC statement")]
    )

    artifact = build_events_artifact(source, now=NOW).to_dict()

    assert artifact["status"] == "complete"
    assert artifact["event_count"] == 1
    event = artifact["events"][0]
    assert event["event_type"] == "central_bank"
    assert event["title"] == source["items"][0]["headline"]
    assert event["summary"] is None
    assert event["occurred_at"] is None
    assert event["scheduled_at"] is None
    assert event["candidate_assets"] == []
    assert event["topics"] == ["monetary_policy"]
    assert event["lifecycle_status"] == "confirmed"
    assert event["normalization"]["verification_level"] == "official"
    assert event["source_refs"][0]["url"] == source["items"][0]["canonical_url"]
    serialized = json.dumps(event).casefold()
    for prohibited in ("sentiment", "ranking", "market_impact", "llm"):
        assert prohibited not in serialized


def test_normalizes_regulatory_item_with_deterministic_rules() -> None:
    source = _news_artifact(
        [_item("nws_fed_b", "Federal Reserve issues enforcement action")]
    )

    event = build_events_artifact(source, now=NOW).to_dict()["events"][0]

    assert event["event_type"] == "regulatory"
    assert event["topics"] == ["regulation"]
    assert event["normalization"]["normalized_action"] == "issues_enforcement_action"
    assert event["normalization"]["method"] == "headline_rules"


def test_unsupported_item_is_audited_and_artifact_fails_closed() -> None:
    source = _news_artifact(
        [_item("nws_fed_c", "Federal Reserve announces a community webinar")]
    )

    artifact = build_events_artifact(source, now=NOW).to_dict()

    assert artifact["status"] == "failed"
    assert artifact["events"] == []
    assert artifact["normalization_rejections"] == [
        {"item_id": "nws_fed_c", "reason_codes": ["unsupported_event_type"]}
    ]


def test_causal_headline_is_quarantined_before_event_creation() -> None:
    source = _news_artifact(
        [_item("nws_fed_0", "Federal Reserve issues rule due to market pressure")]
    )

    artifact = build_events_artifact(source, now=NOW).to_dict()

    assert artifact["status"] == "failed"
    assert artifact["events"] == []
    assert artifact["normalization_rejections"] == [
        {
            "item_id": "nws_fed_0",
            "reason_codes": ["prohibited_causal_language"],
        }
    ]


def test_near_identical_items_group_with_all_source_references() -> None:
    items = [
        _item("nws_fed_d", "Federal Reserve issues FOMC statement"),
        _item(
            "nws_fed_e",
            "Federal Reserve issues FOMC statement.",
            "2026-08-19T20:30:00Z",
        ),
    ]

    artifact = build_events_artifact(_news_artifact(items), now=NOW).to_dict()

    assert artifact["event_count"] == 1
    event = artifact["events"][0]
    assert event["normalization"]["input_item_ids"] == ["nws_fed_d", "nws_fed_e"]
    assert event["normalization"]["deduplication_rule_id"] == (
        "headline_token_jaccard_0_90_v1"
    )
    assert event["normalization"]["deduplication_score"] == 1.0
    assert len(event["source_refs"]) == 2


def test_ambiguous_or_distant_items_are_not_force_merged() -> None:
    different = [
        _item("nws_fed_1", "Federal Reserve issues enforcement action against Bank A"),
        _item("nws_fed_2", "Federal Reserve issues enforcement action against Bank B"),
    ]
    distant = [
        _item("nws_fed_3", "Federal Reserve issues FOMC statement"),
        _item(
            "nws_fed_4",
            "Federal Reserve issues FOMC statement.",
            "2026-08-19T07:00:00Z",
        ),
    ]

    assert build_events_artifact(_news_artifact(different), now=NOW).to_dict()[
        "event_count"
    ] == 2
    assert build_events_artifact(_news_artifact(distant), now=NOW).to_dict()[
        "event_count"
    ] == 2


def test_ids_and_hashes_are_stable_for_identical_input() -> None:
    source = _news_artifact(
        [_item("nws_fed_f", "Federal Reserve publishes FOMC meeting minutes")]
    )

    first = build_events_artifact(source, now=NOW).to_dict()["events"][0]
    second = build_events_artifact(source, now=NOW).to_dict()["events"][0]

    assert first["event_id"] == second["event_id"]
    assert first["canonical_hash"] == second["canonical_hash"]
    assert first["source_refs"][0]["source_id"] == second["source_refs"][0]["source_id"]


def test_failed_and_empty_inputs_remain_distinguishable() -> None:
    failed_source = _news_artifact([], status="failed")
    failed_source["failure_type"] = "source_access_error"
    failed_source["retryable"] = True

    failed = build_events_artifact(failed_source, now=NOW).to_dict()
    empty = build_events_artifact(_news_artifact([]), now=NOW).to_dict()

    assert failed["status"] == "failed"
    assert empty["status"] == "complete"
    assert failed["events"] == empty["events"] == []
    assert failed["warnings"] != empty["warnings"]


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (
            lambda event: event.update(title="Invented policy claim"),
            "unsupported facts",
        ),
        (
            lambda event: event.update(candidate_assets=["SPY"]),
            "candidate_assets",
        ),
        (
            lambda event: event.update(sentiment="positive"),
            "prohibited C2 field",
        ),
        (
            lambda event: event.update(title="Fed caused stocks to fall"),
            "causal",
        ),
    ],
)
def test_validator_rejects_scope_and_provenance_violations(mutator, message) -> None:
    source = _news_artifact(
        [_item("nws_fed_9", "Federal Reserve issues FOMC statement")]
    )
    artifact = build_events_artifact(source, now=NOW).to_dict()
    mutator(artifact["events"][0])

    with pytest.raises(NewsNormalizationValidationError, match=message):
        validate_events_artifact(artifact, source)


def test_pipeline_reads_and_atomically_writes_json(tmp_path: Path) -> None:
    source = _news_artifact(
        [_item("nws_fed_8", "Federal Reserve requests comment on regulatory proposal")]
    )
    input_path = tmp_path / "news_items.json"
    output_path = tmp_path / "events.json"
    input_path.write_text(json.dumps(source), encoding="utf-8")

    result = run_events_pipeline(input_path, output_path)

    assert result.to_dict()["event_count"] == 1
    assert json.loads(output_path.read_text(encoding="utf-8"))["artifact_type"] == "events"
    assert not (tmp_path / "events.json.tmp").exists()


def test_validator_rejects_unknown_input_reference() -> None:
    source = _news_artifact(
        [_item("nws_fed_7", "Federal Reserve issues FOMC statement")]
    )
    artifact = build_events_artifact(source, now=NOW).to_dict()
    invalid = copy.deepcopy(artifact)
    invalid["events"][0]["normalization"]["input_item_ids"] = ["nws_unknown"]

    with pytest.raises(NewsNormalizationValidationError, match="input_item_ids"):
        validate_events_artifact(invalid, source)
