"""Select up to three current, distinct intelligence objects deterministically."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from src.top_intelligence.schema import (
    TopIntelligenceArtifact,
    TopIntelligenceItem,
)


RULE_SET_VERSION = "top_intelligence_rules_v1"
TYPE_PRIORITY = {
    "market_stress": 0,
    "upcoming_event": 1,
    "market_regime": 2,
    "cross_asset_signal": 3,
    "data_quality": 4,
}
MATERIAL_COVERAGE_INPUTS = {
    "market_observations",
    "macro_observations",
    "economic_calendar",
    "market_signals",
    "market_regime",
}
REFERENCE_KEYS = (
    "artifact_run_ids",
    "evidence_bundle_ids",
    "source_ids",
    "observation_ids",
    "event_ids",
    "evidence_ids",
    "signal_ids",
    "regime_dimension_ids",
    "risk_ids",
    "coverage_inputs",
)


class TopIntelligenceSelectionError(ValueError):
    """Raised when the canonical input cannot support safe selection."""


def build_top_intelligence_artifact(
    daily: Mapping[str, Any],
    now: Optional[datetime] = None,
) -> TopIntelligenceArtifact:
    generated = _as_utc(now or datetime.now(timezone.utc))
    _validate_input_shape(daily)
    _validate_input_traceability(daily)
    if "freshness_items" in daily:
        from src.data.item_freshness import build_item_freshness
        if daily["freshness_items"] != build_item_freshness(daily):
            raise TopIntelligenceSelectionError("daily item freshness does not match its evidence catalog")
    coverage = {
        str(item.get("artifact")): item for item in daily.get("coverage", [])
    }
    source_catalog = {
        str(item.get("source_id")): item
        for item in daily.get("provenance_catalog", {}).get("source_records", [])
    }

    objects: List[tuple[str, Mapping[str, Any]]] = []
    regime = daily.get("market_regime")
    if isinstance(regime, Mapping):
        objects.append(("market_regime", regime))
    for section, item_type in (
        ("cross_asset_signals", "cross_asset_signal"),
        ("upcoming_events", "upcoming_event"),
        ("observed_market_stress", "market_stress"),
        ("data_quality_risks", "data_quality"),
    ):
        for obj in daily.get(section, []):
            if isinstance(obj, Mapping):
                objects.append((item_type, obj))

    scoped = daily.get("freshness_items", {}).get("items", {}) if "freshness_items" in daily else None
    candidates = [
        candidate
        for item_type, obj in objects
        for candidate in [_build_candidate(item_type, obj, coverage, source_catalog, generated,
            scoped.get(str(obj.get("object_id")), {}) if scoped is not None else None)]
        if candidate is not None
    ]
    candidates.sort(key=_sort_key)
    story_winners: Dict[str, Dict[str, Any]] = {}
    for candidate in candidates:
        story_winners.setdefault(str(candidate["story_key"]), candidate)
    distinct_story_candidates = list(story_winners.values())

    selected: List[Dict[str, Any]] = []
    used_themes: set[str] = set()
    for candidate in distinct_story_candidates:
        if len(selected) == 3:
            break
        if candidate["primary_theme"] in used_themes:
            continue
        selected.append(candidate)
        used_themes.add(str(candidate["primary_theme"]))

    items = [
        TopIntelligenceItem(rank=index, **_public_candidate(candidate))
        for index, candidate in enumerate(selected, start=1)
    ]
    status = "complete" if len(items) == 3 else "partial" if items else "unavailable"
    warnings: List[str] = []
    if not items:
        warnings.append("no_current_eligible_top_intelligence")
    elif len(items) < 3:
        warnings.append("fewer_than_three_eligible_items")
    if len(candidates) > len(distinct_story_candidates):
        warnings.append("semantic_story_duplicates_suppressed")
    if len(distinct_story_candidates) > len(items):
        warnings.append("duplicate_or_same_theme_candidates_suppressed")

    generated_at = _iso(generated)
    input_run = str(daily["run_id"])
    digest = hashlib.sha256(
        f"{input_run}|{generated_at}|{RULE_SET_VERSION}".encode("utf-8")
    ).hexdigest()[:16]
    return TopIntelligenceArtifact(
        run_id=f"run_{generated:%Y%m%dT%H%M%SZ}_top_{digest}",
        report_date=str(daily["report_date"]),
        generated_at=generated_at,
        status=status,
        input_refs={"daily_intelligence_run_id": input_run},
        candidate_count=len(objects),
        eligible_count=len(candidates),
        items=items,
        warnings=warnings,
        limitations=[
            "Selection uses current validated structured intelligence only.",
            "Scores order observed conditions; they are not forecasts or trading signals.",
            "Fewer than three items are published when distinct evidence is unavailable.",
        ],
    )


def _build_candidate(
    item_type: str,
    obj: Mapping[str, Any],
    coverage: Mapping[str, Mapping[str, Any]],
    source_catalog: Mapping[str, Mapping[str, Any]],
    generated: datetime,
    scoped_freshness: Optional[Mapping[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    if obj.get("validation_status") != "validated":
        return None
    if scoped_freshness is not None:
        from src.data.freshness import validate_freshness_contract
        try:
            validate_freshness_contract(scoped_freshness)
            source_time = datetime.fromisoformat(str(scoped_freshness["source_timestamp"] or scoped_freshness["retrieved_at"]).replace("Z", "+00:00"))
            if scoped_freshness["freshness_status"] != "current" or (generated - source_time).total_seconds() > scoped_freshness["stale_after_seconds"]:
                return None
        except (ValueError, TypeError, KeyError):
            return None
    source_artifact = str(obj.get("source_artifact", ""))
    source_coverage = coverage.get(source_artifact)
    if not source_coverage or not _coverage_current(
        source_coverage,
        generated,
        allow_degraded_record=item_type == "data_quality" or scoped_freshness is not None,
    ):
        return None
    payload = obj.get("payload")
    refs = _normalized_refs(obj.get("evidence_refs"))
    if not isinstance(payload, Mapping) or not _eligible(item_type, obj, payload, refs, source_catalog, generated):
        return None

    assets = sorted({str(value) for value in payload.get("related_assets", []) if value})
    if item_type == "cross_asset_signal":
        assets = sorted({str(value) for value in payload.get("required_assets", []) if value})
    if item_type == "market_regime":
        assets = sorted(
            {
                str(value.get("asset"))
                for dimension in payload.get("dimensions", [])
                for value in dimension.get("observed_values", [])
                if value.get("asset")
            }
        )
    theme = _primary_theme(item_type, assets, payload)
    story_key = _story_key(item_type, payload, assets)
    breakdown = _score(item_type, payload, refs, assets, source_catalog, generated)
    source_object_id = _source_object_id(item_type, obj, payload)
    item_id = "top_" + hashlib.sha256(
        f"{item_type}|{source_object_id}|{obj['source_run_id']}|{RULE_SET_VERSION}".encode("utf-8")
    ).hexdigest()[:16]
    headline, why, monitor = _text(item_type, payload, assets)
    timestamps = {
        key: sorted({str(value) for value in obj.get("timestamps", {}).get(key, []) if value})
        for key in ("observed_at", "scheduled_at", "detected_at")
    }
    return {
        "item_id": item_id,
        "type": item_type,
        "story_key": story_key,
        "source_object_id": source_object_id,
        "headline": headline,
        "why": why,
        "monitor": monitor,
        "total_score": sum(breakdown.values()),
        "score_breakdown": breakdown,
        "primary_theme": theme,
        "related_assets": assets,
        "evidence_refs": refs,
        "source_refs": refs["source_ids"],
        "timestamps": timestamps,
        "freshness_status": "current",
        "validation_status": "validated",
        "_scheduled_at": min(timestamps["scheduled_at"], default="9999"),
    }


def _eligible(
    item_type: str,
    obj: Mapping[str, Any],
    payload: Mapping[str, Any],
    refs: Mapping[str, Sequence[str]],
    source_catalog: Mapping[str, Mapping[str, Any]],
    generated: datetime,
) -> bool:
    if item_type == "cross_asset_signal":
        state_ok = (
            payload.get("state") == "observed"
            and payload.get("condition_met") is True
            and payload.get("data_quality", {}).get("status") == "available"
        )
    elif item_type == "market_regime":
        state_ok = (
            payload.get("status") in {"available", "partial"}
            and payload.get("classification") in {"risk_on", "risk_off", "mixed"}
        )
    elif item_type == "upcoming_event":
        scheduled = _first_timestamp(payload, obj, "scheduled_at")
        state_ok = (
            payload.get("status") == "scheduled"
            and scheduled is not None
            and generated < scheduled <= generated + timedelta(hours=48)
            and bool(refs["event_ids"])
            and any(_official(source_catalog.get(source_id, {})) for source_id in refs["source_ids"])
        )
    elif item_type == "market_stress":
        state_ok = payload.get("status") in {"observed", "detected"}
    elif item_type == "data_quality":
        coverage_inputs = set(refs["coverage_inputs"])
        rule_id = str(payload.get("rule_id", ""))
        state_ok = (
            payload.get("status") == "detected"
            and payload.get("attention_level") == "high"
            and (
                bool(coverage_inputs & MATERIAL_COVERAGE_INPUTS)
                or rule_id in {
                    "market_signal_coverage_degraded_v1",
                    "market_regime_coverage_degraded_v1",
                    "input_artifact_stale_v1",
                }
            )
        )
    else:
        return False
    if not state_ok:
        return False
    if item_type == "data_quality":
        return bool(refs["risk_ids"] and (refs["coverage_inputs"] or refs["artifact_run_ids"]))
    return bool(refs["source_ids"] and any(refs[key] for key in REFERENCE_KEYS[1:] if key != "source_ids"))


def _score(
    item_type: str,
    payload: Mapping[str, Any],
    refs: Mapping[str, Sequence[str]],
    assets: Sequence[str],
    source_catalog: Mapping[str, Mapping[str, Any]],
    generated: datetime,
) -> Dict[str, int]:
    official = item_type == "upcoming_event" and any(
        _official(source_catalog.get(source_id, {})) for source_id in refs["source_ids"]
    )
    support_count = len(set(refs["evidence_ids"] + refs["observation_ids"]))
    if official:
        evidence_quality = 20
    elif refs["source_ids"] and support_count:
        evidence_quality = 18
    elif refs["source_ids"]:
        evidence_quality = 14
    else:
        evidence_quality = 12
    breadth = 15 if item_type == "market_regime" else min(15, 5 * len(_asset_themes(assets)))
    proximity = 0
    if item_type == "upcoming_event":
        scheduled = _first_timestamp(payload, {}, "scheduled_at")
        hours = (scheduled - generated).total_seconds() / 3600 if scheduled else 49
        proximity = 15 if hours <= 6 else 12 if hours <= 24 else 8
    attention = str(payload.get("attention_level", "low"))
    impact = str(payload.get("observed_facts", {}).get("impact", attention))
    if item_type == "market_regime":
        relevance = 15
    elif item_type == "market_stress":
        relevance = {"high": 15, "medium": 10, "low": 5}.get(attention, 5)
    elif item_type == "cross_asset_signal":
        relevance = min(15, 5 * len(assets))
    elif item_type == "upcoming_event":
        relevance = {"high": 15, "medium": 10, "low": 5}.get(impact, 5)
    else:
        relevance = 10
    confirmation = (
        10 if official or len(refs["source_ids"]) >= 2
        else 8 if support_count >= 2
        else 6 if refs["source_ids"]
        else 4
    )
    risk_relevance = (
        5 if item_type == "market_stress" or (item_type == "upcoming_event" and impact == "high")
        else 3 if item_type == "market_regime" or (item_type == "upcoming_event" and impact == "medium")
        else 0
    )
    return {
        "freshness": 20,
        "evidence_quality": evidence_quality,
        "cross_asset_breadth": breadth,
        "event_proximity": proximity,
        "market_relevance": relevance,
        "confirmation": confirmation,
        "risk_relevance": risk_relevance,
    }


def _text(item_type: str, payload: Mapping[str, Any], assets: Sequence[str]) -> tuple[str, str, str]:
    joined_assets = ", ".join(assets) if assets else "referenced markets"
    if item_type == "cross_asset_signal":
        label = str(payload.get("label") or payload.get("rule_id"))
        values = ", ".join(
            f"{item.get('asset')} {item.get('metric')}={item.get('value')} {item.get('unit')}"
            for item in payload.get("observed_values", [])
        )
        return (
            f"Observed: {label}",
            f"The validated relationship condition is observed across {joined_assets}; {values or 'supporting values are preserved in evidence references'}.",
            "Monitor the same validated metrics and their observation timestamps on the next run.",
        )
    if item_type == "market_regime":
        classification = str(payload.get("classification"))
        count = payload.get("score", {}).get("eligible_dimension_count", 0)
        return (
            f"Current market regime: {classification}",
            f"The deterministic classifier used {count} eligible current dimensions; confidence is {payload.get('confidence', {}).get('label', 'unavailable')}.",
            "Monitor the existing regime dimensions and their current evidence coverage.",
        )
    if item_type == "upcoming_event":
        facts = payload.get("observed_facts", {})
        scheduled = facts.get("scheduled_at") or payload.get("time_window", {}).get("scheduled_at")
        name = facts.get("name") or facts.get("event_name") or payload.get("title")
        return (
            f"Upcoming official event: {name}",
            f"The validated official calendar record is scheduled for {scheduled}; impact is {facts.get('impact', payload.get('attention_level', 'unavailable'))}.",
            f"Monitor the official event record at {scheduled} and any validated lifecycle update.",
        )
    if item_type == "market_stress":
        return (
            str(payload.get("title")),
            f"{payload.get('description')} Attention level is {payload.get('attention_level')} and the condition is linked to current evidence.",
            f"Monitor the referenced observations for {joined_assets} on the next validated run.",
        )
    facts = payload.get("observed_facts", {})
    affected = facts.get("input_type") or facts.get("artifact") or "intelligence coverage"
    return (
        str(payload.get("title")),
        f"This high-attention data-quality condition materially limits interpretation of {affected}.",
        f"Monitor {affected} until its validated coverage status is available and current.",
    )


def _primary_theme(item_type: str, assets: Sequence[str], payload: Mapping[str, Any]) -> str:
    if item_type == "upcoming_event":
        return "upcoming_events"
    if item_type == "market_regime":
        return "market_regime"
    if item_type == "data_quality":
        return "data_quality"
    themes = _asset_themes(assets)
    if "equities_volatility" in themes:
        return "equities_volatility"
    if "macro_rates" in themes:
        return "macro_rates"
    if "crypto" in themes:
        return "crypto"
    if "commodities" in themes:
        return "commodities"
    return "equities_volatility" if item_type == "market_stress" else "macro_rates"


def _asset_themes(assets: Sequence[str]) -> set[str]:
    themes: set[str] = set()
    for asset in assets:
        if asset in {"SPY", "QQQ", "NVDA", "AAPL", "TSLA", "VIX"}:
            themes.add("equities_volatility")
        elif asset in {"BTC", "ETH", "BTC-USD", "ETH-USD"}:
            themes.add("crypto")
        elif asset in {"GOLD", "WTI"}:
            themes.add("commodities")
        elif asset in {"DXY", "US10Y", "EURUSD", "USDJPY"}:
            themes.add("macro_rates")
    return themes


def _story_key(
    item_type: str,
    payload: Mapping[str, Any],
    assets: Sequence[str],
) -> str:
    if item_type == "market_regime":
        return f"market_state:{payload.get('classification')}"
    if item_type == "upcoming_event":
        event_id = payload.get("observed_facts", {}).get("event_id")
        return f"event:{event_id or payload.get('risk_id')}"
    if item_type == "data_quality":
        inputs = payload.get("evidence_refs", {}).get("coverage_inputs", [])
        affected = inputs[0] if inputs else payload.get("rule_id", "unknown")
        if affected in {"market_signals", "market_regime"}:
            affected = "intelligence_coverage"
        return f"data_quality:{affected}"
    if item_type == "market_stress":
        rule_id = str(payload.get("rule_id", ""))
        if rule_id in {
            "observed_risk_off_regime_v1",
            "observed_equity_volatility_stress_v1",
            "observed_equity_crypto_stress_v1",
        }:
            return "market_state:risk_off"
        if rule_id == "observed_dollar_yield_pressure_v1":
            return "macro_state:usd_strength"
        if rule_id == "observed_equity_divergence_v1":
            return "equity_state:index_divergence"
        return f"market_stress:{rule_id or payload.get('risk_id')}"

    rule_id = str(payload.get("rule_id", ""))
    values = {
        str(item.get("asset")): float(item["value"])
        for item in payload.get("observed_values", [])
        if item.get("asset") and isinstance(item.get("value"), (int, float))
    }
    if rule_id in {
        "equity_index_co_movement_v1",
        "equity_crypto_co_movement_v1",
        "equity_volatility_inverse_move_v1",
    }:
        state = _risk_state_from_values(values)
        if state:
            return f"market_state:{state}"
    if rule_id in {
        "gold_dollar_inverse_move_v1",
        "dollar_yield_co_movement_v1",
        "dollar_fx_quote_alignment_v1",
    }:
        dxy = values.get("DXY")
        if dxy is not None and dxy != 0:
            return f"macro_state:{'usd_strength' if dxy > 0 else 'usd_weakness'}"
    if rule_id == "crypto_co_movement_v1":
        direction = _common_direction(values, ("BTC-USD", "ETH-USD"))
        if direction:
            return f"crypto_state:{direction}_co_movement"
    if rule_id == "equity_index_divergence_v1":
        return "equity_state:index_divergence"
    return f"relationship:{rule_id or ','.join(assets) or 'unknown'}"


def _risk_state_from_values(values: Mapping[str, float]) -> Optional[str]:
    equities = [values[asset] for asset in ("SPY", "QQQ") if asset in values]
    if len(equities) != 2:
        return None
    if all(value > 0 for value in equities):
        if "VIX" in values and values["VIX"] >= 0:
            return None
        if "BTC-USD" in values and values["BTC-USD"] <= 0:
            return None
        return "risk_on"
    if all(value < 0 for value in equities):
        if "VIX" in values and values["VIX"] <= 0:
            return None
        if "BTC-USD" in values and values["BTC-USD"] >= 0:
            return None
        return "risk_off"
    return None


def _common_direction(
    values: Mapping[str, float],
    assets: Sequence[str],
) -> Optional[str]:
    selected = [values[asset] for asset in assets if asset in values]
    if len(selected) != len(assets):
        return None
    if all(value > 0 for value in selected):
        return "positive"
    if all(value < 0 for value in selected):
        return "negative"
    return None


def _sort_key(item: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        -int(item["total_score"]),
        TYPE_PRIORITY[str(item["type"])],
        item["_scheduled_at"],
        item["source_object_id"],
    )


def _public_candidate(candidate: Mapping[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in candidate.items() if not key.startswith("_")}


def _source_object_id(item_type: str, obj: Mapping[str, Any], payload: Mapping[str, Any]) -> str:
    key = {
        "cross_asset_signal": "signal_id",
        "market_regime": "run_id",
        "upcoming_event": "risk_id",
        "market_stress": "risk_id",
        "data_quality": "risk_id",
    }[item_type]
    return str(payload.get(key) or obj.get("object_id"))


def _coverage_current(
    item: Mapping[str, Any],
    generated: datetime,
    allow_degraded_record: bool = False,
) -> bool:
    try:
        artifact_generated = _as_utc(
            datetime.fromisoformat(str(item["generated_at"]).replace("Z", "+00:00"))
        )
        maximum_age = float(item.get("maximum_age_hours", 24.0))
    except (KeyError, TypeError, ValueError):
        return False
    actual_age = max(0.0, (generated - artifact_generated).total_seconds() / 3600)
    return (
        item.get("validation_status") == "validated"
        and (allow_degraded_record or item.get("freshness_status") == "current")
        and item.get("artifact_freshness_status") == "current"
        and actual_age <= maximum_age
    )


def _normalized_refs(value: Any) -> Dict[str, List[str]]:
    raw = value if isinstance(value, Mapping) else {}
    return {
        key: sorted({str(item) for item in raw.get(key, []) if item})
        for key in REFERENCE_KEYS
    }


def _official(source: Mapping[str, Any]) -> bool:
    tier = source.get("quality_tier")
    return tier in {1, "1", "tier1", "official"} or str(source.get("source_type", "")).casefold() in {
        "official", "official_calendar", "government", "central_bank"
    }


def _first_timestamp(payload: Mapping[str, Any], obj: Mapping[str, Any], key: str) -> Optional[datetime]:
    values: List[Any] = []
    facts = payload.get("observed_facts", {})
    window = payload.get("time_window", {})
    if isinstance(facts, Mapping):
        values.append(facts.get(key))
    if isinstance(window, Mapping):
        values.append(window.get(key))
    values.extend(obj.get("timestamps", {}).get(key, []) if isinstance(obj.get("timestamps"), Mapping) else [])
    for value in values:
        if isinstance(value, str) and value:
            try:
                return _as_utc(datetime.fromisoformat(value.replace("Z", "+00:00")))
            except ValueError:
                continue
    return None


def _validate_input_shape(daily: Mapping[str, Any]) -> None:
    if daily.get("artifact_type") != "daily_intelligence":
        raise TopIntelligenceSelectionError("selector requires daily_intelligence input")
    for key in ("run_id", "report_date", "generated_at", "coverage", "provenance_catalog"):
        if key not in daily:
            raise TopIntelligenceSelectionError(f"daily intelligence missing {key}")


def _validate_input_traceability(daily: Mapping[str, Any]) -> None:
    catalog = daily.get("provenance_catalog", {})
    catalog_contract = {
        "evidence_bundle_ids": ("evidence_bundles", "id"),
        "source_ids": ("source_records", "source_id"),
        "observation_ids": ("observation_records", "observation_id"),
        "event_ids": ("event_records", "event_id"),
        "evidence_ids": ("evidence_records", "evidence_id"),
    }
    known: Dict[str, set[str]] = {
        ref_key: {
            str(record.get(id_key))
            for record in catalog.get(catalog_key, [])
            if isinstance(record, Mapping) and record.get(id_key)
        }
        for ref_key, (catalog_key, id_key) in catalog_contract.items()
    }
    signals = [
        obj for obj in daily.get("cross_asset_signals", []) if isinstance(obj, Mapping)
    ]
    risk_objects = [
        obj
        for section in ("upcoming_events", "data_quality_risks", "observed_market_stress")
        for obj in daily.get(section, [])
        if isinstance(obj, Mapping)
    ]
    known["signal_ids"] = {
        str(obj.get("payload", {}).get("signal_id"))
        for obj in signals
        if isinstance(obj.get("payload"), Mapping) and obj["payload"].get("signal_id")
    }
    known["risk_ids"] = {
        str(obj.get("payload", {}).get("risk_id"))
        for obj in risk_objects
        if isinstance(obj.get("payload"), Mapping) and obj["payload"].get("risk_id")
    }
    regime = daily.get("market_regime", {})
    regime_payload = regime.get("payload", {}) if isinstance(regime, Mapping) else {}
    known["regime_dimension_ids"] = {
        str(item.get("dimension_id"))
        for item in regime_payload.get("dimensions", [])
        if isinstance(item, Mapping) and item.get("dimension_id")
    }
    objects = ([regime] if isinstance(regime, Mapping) else []) + signals + risk_objects
    for obj in objects:
        refs = _normalized_refs(obj.get("evidence_refs"))
        for key, valid_ids in known.items():
            unresolved = set(refs[key]) - valid_ids
            if unresolved:
                raise TopIntelligenceSelectionError(
                    f"unresolved {key}: {', '.join(sorted(unresolved))}"
                )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise TopIntelligenceSelectionError("selection time must include timezone")
    return value.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
