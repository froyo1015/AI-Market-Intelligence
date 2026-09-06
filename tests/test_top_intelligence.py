from __future__ import annotations

import copy
import json
from datetime import timedelta
from pathlib import Path

import pytest

from src.data.freshness import enrich_artifact_freshness, strip_freshness_metadata
from src.top_intelligence.pipeline import run_top_intelligence_pipeline
from src.top_intelligence.selector import build_top_intelligence_artifact
from src.top_intelligence.validator import (
    TopIntelligenceValidationError,
    validate_top_intelligence_artifact,
)
from tests.test_cross_asset_signals import DEFAULT_VALUES, NOW
from tests.test_daily_intelligence import _compose, _four_inputs
from tests.test_evidence_consolidation import _calendar


RISK_OFF_VALUES = {
    "SPY": -1.0,
    "QQQ": -1.2,
    "BTC-USD": -0.8,
    "ETH-USD": -0.7,
    "VIX": 0.5,
    "DXY": 0.8,
    "US10Y": 2.0,
}


def _daily(values=None, *, calendar=None, stale_assets=None, now=NOW) -> dict:
    return _compose(
        _four_inputs(values=values, calendar=calendar, stale_assets=stale_assets),
        now=now,
    )


def _top(daily: dict, now=NOW) -> dict:
    return build_top_intelligence_artifact(daily, now=now).to_dict()


def test_complete_top_three_selection_is_scored_and_traceable() -> None:
    daily = _daily(values=RISK_OFF_VALUES, calendar=_calendar())
    artifact = _top(daily)

    assert artifact["status"] == "complete"
    assert artifact["selected_count"] == 3
    assert [item["rank"] for item in artifact["items"]] == [1, 2, 3]
    assert artifact["items"][0]["type"] == "upcoming_event"
    assert all(item["source_refs"] for item in artifact["items"])
    assert all(item["freshness_status"] == "current" for item in artifact["items"])
    assert all(item["total_score"] == sum(item["score_breakdown"].values()) for item in artifact["items"])


def test_stale_candidates_are_rejected_not_down_ranked() -> None:
    daily = _daily(now=NOW + timedelta(hours=25))
    artifact = _top(daily, now=NOW + timedelta(hours=25))

    assert artifact["status"] == "unavailable"
    assert artifact["items"] == []
    assert "no_current_eligible_top_intelligence" in artifact["warnings"]


def test_upcoming_official_event_is_eligible_and_preserves_event_source() -> None:
    artifact = _top(_daily(calendar=_calendar()))
    event = next(item for item in artifact["items"] if item["type"] == "upcoming_event")

    assert event["evidence_refs"]["event_ids"] == ["evt_cpi"]
    assert event["source_refs"]
    assert event["timestamps"]["scheduled_at"] == ["2026-08-27T12:30:00Z"]
    assert event["score_breakdown"]["evidence_quality"] == 20


def test_observed_stress_outranks_overlapping_equity_signal() -> None:
    artifact = _top(_daily(values=RISK_OFF_VALUES))
    equity_theme = [item for item in artifact["items"] if item["primary_theme"] == "equities_volatility"]

    assert len(equity_theme) == 1
    assert equity_theme[0]["type"] == "market_stress"


def test_regime_and_risk_off_stress_share_one_semantic_story() -> None:
    daily = _daily(values=RISK_OFF_VALUES)
    artifact = _top(daily)
    risk_off = [
        item for item in artifact["items"] if item["story_key"] == "market_state:risk_off"
    ]

    assert daily["market_regime"]["payload"]["classification"] == "risk_off"
    assert any(
        item["payload"]["rule_id"] == "observed_risk_off_regime_v1"
        for item in daily["observed_market_stress"]
    )
    assert len(risk_off) == 1
    assert risk_off[0]["type"] == "market_stress"
    assert "semantic_story_duplicates_suppressed" in artifact["warnings"]


def test_inverse_risk_on_relationships_share_regime_story() -> None:
    daily = _daily()
    artifact = _top(daily)
    risk_on = [
        item for item in artifact["items"] if item["story_key"] == "market_state:risk_on"
    ]

    assert daily["market_regime"]["payload"]["classification"] == "risk_on"
    assert any(
        item["payload"]["rule_id"] == "equity_volatility_inverse_move_v1"
        and item["payload"]["state"] == "observed"
        for item in daily["cross_asset_signals"]
    )
    assert len(risk_on) == 1
    assert risk_on[0]["type"] == "market_regime"


def test_gold_usd_and_yield_relationships_share_one_macro_story() -> None:
    values = dict(DEFAULT_VALUES, GOLD=-1.0, DXY=0.8, US10Y=4.0)
    daily = _daily(values=values)
    artifact = _top(daily)
    observed_rules = {
        item["payload"]["rule_id"]
        for item in daily["cross_asset_signals"]
        if item["payload"]["state"] == "observed"
    }
    usd_strength = [
        item for item in artifact["items"] if item["story_key"] == "macro_state:usd_strength"
    ]

    assert {
        "gold_dollar_inverse_move_v1",
        "dollar_yield_co_movement_v1",
    }.issubset(observed_rules)
    assert len(usd_strength) == 1
    assert "semantic_story_duplicates_suppressed" in artifact["warnings"]


def test_genuinely_distinct_event_market_state_and_macro_stories_remain() -> None:
    artifact = _top(_daily(values=RISK_OFF_VALUES, calendar=_calendar()))

    assert artifact["status"] == "complete"
    assert [item["story_key"] for item in artifact["items"]] == [
        "event:evt_cpi",
        "market_state:risk_off",
        "macro_state:usd_strength",
    ]


def test_material_data_quality_limitation_can_be_selected() -> None:
    daily = _daily(stale_assets={"SPY"})
    artifact = _top(daily)

    assert any(item["type"] == "data_quality" for item in artifact["items"])
    assert all(item["freshness_status"] == "current" for item in artifact["items"])


def test_duplicate_theme_suppression_never_uses_filler() -> None:
    artifact = _top(_daily(values=RISK_OFF_VALUES, calendar=_calendar()))
    themes = [item["primary_theme"] for item in artifact["items"]]

    assert len(themes) == len(set(themes))
    assert "duplicate_or_same_theme_candidates_suppressed" in artifact["warnings"]


def test_deterministic_tie_break_and_stable_hash() -> None:
    daily = _daily()
    first = _top(daily)
    second = _top(copy.deepcopy(daily))

    assert first == second
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert [item["item_id"] for item in first["items"]] == [item["item_id"] for item in second["items"]]


def test_fewer_than_three_candidates_returns_partial_without_padding() -> None:
    zero_values = {key: 0.0 for key in DEFAULT_VALUES}
    artifact = _top(_daily(values=zero_values))

    assert artifact["status"] == "partial"
    assert artifact["selected_count"] == 1
    assert artifact["items"][0]["type"] == "market_regime"
    assert artifact["warnings"] == ["fewer_than_three_eligible_items"]


def test_unsupported_objects_and_tampering_are_rejected() -> None:
    daily = _daily(values={key: 0.0 for key in DEFAULT_VALUES})
    unsupported = copy.deepcopy(daily)
    unsupported["cross_asset_signals"][0]["payload"]["state"] = "insufficient_data"
    assert all(item["type"] != "cross_asset_signal" for item in _top(unsupported)["items"])

    artifact = enrich_artifact_freshness(_top(daily), supporting_artifacts=[daily])
    tampered = copy.deepcopy(artifact)
    tampered["items"][0]["headline"] = "Market will rise"
    with pytest.raises(TopIntelligenceValidationError):
        validate_top_intelligence_artifact(tampered, daily)


def test_pipeline_writes_validated_artifact_atomically(tmp_path: Path) -> None:
    daily = _daily(values=RISK_OFF_VALUES, calendar=_calendar())
    input_path = tmp_path / "daily_intelligence.json"
    output_path = tmp_path / "top_intelligence.json"
    input_path.write_text(json.dumps(daily), encoding="utf-8")

    artifact = run_top_intelligence_pipeline(input_path, output_path, now=NOW)
    written = json.loads(output_path.read_text(encoding="utf-8"))

    assert strip_freshness_metadata(written) == strip_freshness_metadata(artifact)
    assert written["freshness_status"] == "current"
    validate_top_intelligence_artifact(written, daily)
    assert not output_path.with_suffix(".json.tmp").exists()
