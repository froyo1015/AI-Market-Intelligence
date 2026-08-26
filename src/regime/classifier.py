"""Classify current observed market conditions with deterministic rules."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

from src.evidence.schema import confidence_label
from src.models.regime_schema import MarketRegimeArtifact, RegimeDimension
from src.regime.rules import (
    ANCHOR_DIMENSIONS,
    DIMENSION_RULES,
    MAXIMUM_FUTURE_SKEW_MINUTES,
    MAXIMUM_INPUT_AGE_HOURS,
    MINIMUM_ELIGIBLE_DIMENSIONS,
    MINIMUM_ELIGIBLE_WEIGHT,
    RISK_OFF_THRESHOLD,
    RISK_ON_THRESHOLD,
    RULE_SET_VERSION,
    RegimeDimensionRule,
)
from src.signals.validator import validate_market_signals_artifact


class RegimeClassificationError(ValueError):
    """Raised when linked Phase 6.3-B inputs are structurally inconsistent."""


def build_market_regime_artifact(
    evidence_bundle: Mapping[str, Any],
    market_signals: Mapping[str, Any],
    now: Optional[datetime] = None,
) -> MarketRegimeArtifact:
    generated = _as_utc(now or datetime.now(timezone.utc))
    validate_market_signals_artifact(market_signals, evidence_bundle)
    _validate_input_linkage(evidence_bundle, market_signals, generated)

    evidence_index, stale_observation_ids = _index_evidence(evidence_bundle)
    signals_by_rule = {item["rule_id"]: item for item in market_signals["signals"]}
    freshness = _input_freshness(
        evidence_bundle,
        market_signals,
        generated,
        signals_by_rule,
        stale_observation_ids,
    )
    artifacts_current = not freshness["stale_artifacts"]
    dimensions = [
        _evaluate_dimension(
            rule,
            signals_by_rule[rule.signal_rule_id],
            evidence_index,
            stale_observation_ids,
            artifacts_current,
        )
        for rule in DIMENSION_RULES
    ]

    eligible = [item for item in dimensions if item.eligibility == "eligible"]
    eligible_weight = sum(item.weight for item in eligible)
    weighted_sum = sum(item.weighted_contribution or 0.0 for item in eligible)
    normalized_score = weighted_sum / eligible_weight if eligible_weight else 0.0
    anchor_present = any(
        item.dimension_id in ANCHOR_DIMENSIONS for item in eligible
    )
    requirements_met = (
        len(eligible) >= MINIMUM_ELIGIBLE_DIMENSIONS
        and eligible_weight >= MINIMUM_ELIGIBLE_WEIGHT
        and anchor_present
    )
    classification: Optional[str]
    if not requirements_met:
        classification = None
    elif normalized_score >= RISK_ON_THRESHOLD:
        classification = "risk_on"
    elif normalized_score <= RISK_OFF_THRESHOLD:
        classification = "risk_off"
    else:
        classification = "mixed"

    state_weights = {
        state: sum(item.weight for item in eligible if item.observed_state == state)
        for state in ("risk_on", "risk_off", "mixed")
    }
    agreement = max(state_weights.values()) / eligible_weight if eligible_weight else 0.0
    input_scores = [float(item.confidence["score"]) for item in eligible]
    input_quality = min(input_scores) if input_scores else 0.0
    confidence_score = (
        0.50 * eligible_weight + 0.25 * input_quality + 0.25 * agreement
        if classification is not None
        else 0.0
    )
    confidence_score = round(confidence_score, 6)

    if classification is None:
        status = "unavailable"
    elif len(eligible) == len(DIMENSION_RULES):
        status = "available"
    else:
        status = "partial"

    warnings: List[str] = []
    if freshness["status"] != "current":
        warnings.append("One or more input artifacts or observations are stale.")
    ineligible_count = len(DIMENSION_RULES) - len(eligible)
    if ineligible_count:
        warnings.append(f"{ineligible_count} regime dimension(s) are unavailable.")
    if classification is None:
        warnings.append("Current evidence does not meet classification coverage rules.")

    evidence_refs = _merge_evidence_refs(eligible)
    generated_at = _iso_utc(generated)
    input_refs = {
        "evidence_bundle_run_id": str(evidence_bundle["run_id"]),
        "market_signals_run_id": str(market_signals["run_id"]),
    }
    digest = hashlib.sha256(
        (
            f"{input_refs['evidence_bundle_run_id']}|"
            f"{input_refs['market_signals_run_id']}|{generated_at}|{RULE_SET_VERSION}"
        ).encode("utf-8")
    ).hexdigest()[:16]
    return MarketRegimeArtifact(
        run_id=f"run_{generated:%Y%m%dT%H%M%SZ}_regime_{digest}",
        report_date=str(evidence_bundle["report_date"]),
        generated_at=generated_at,
        status=status,
        classification=classification,
        input_refs=input_refs,
        input_freshness=freshness,
        score={
            "weighted_sum": round(weighted_sum, 6),
            "eligible_weight": round(eligible_weight, 6),
            "eligible_dimension_count": len(eligible),
            "normalized_score": round(normalized_score, 6),
            "risk_on_threshold": RISK_ON_THRESHOLD,
            "risk_off_threshold": RISK_OFF_THRESHOLD,
            "minimum_eligible_weight": MINIMUM_ELIGIBLE_WEIGHT,
            "minimum_eligible_dimensions": MINIMUM_ELIGIBLE_DIMENSIONS,
            "anchor_present": anchor_present,
            "state_weights": {
                key: round(value, 6) for key, value in state_weights.items()
            },
        },
        confidence={
            "score": confidence_score,
            "label": confidence_label(confidence_score).value,
            "basis": "coverage_quality_agreement",
            "coverage_score": round(eligible_weight, 6),
            "input_quality": round(input_quality, 6),
            "agreement_score": round(agreement, 6),
        },
        dimensions=dimensions,
        evidence_refs=evidence_refs,
        warnings=warnings,
        limitations=[
            "The classification describes current observations only.",
            "It does not establish causality, persistence, or later outcomes.",
            "The classifier does not provide investment or trading instructions.",
        ],
    )


def _evaluate_dimension(
    rule: RegimeDimensionRule,
    signal: Mapping[str, Any],
    evidence_index: Mapping[str, Mapping[str, Any]],
    stale_observation_ids: Set[str],
    artifacts_current: bool,
) -> RegimeDimension:
    reason_codes: List[str] = []
    if not artifacts_current:
        reason_codes.append("input_artifact_stale")
    if signal.get("state") not in {"observed", "not_observed"}:
        reason_codes.append(f"signal_{signal.get('state', 'invalid')}")
    if signal.get("data_quality", {}).get("status") != "available":
        reason_codes.append("signal_data_quality_unavailable")

    observation_ids = list(signal.get("evidence_refs", {}).get("observation_ids", []))
    referenced = [evidence_index.get(item) for item in observation_ids]
    if any(item is None for item in referenced):
        reason_codes.append("unresolved_observation_reference")
    if any(item in stale_observation_ids for item in observation_ids):
        reason_codes.append("stale_supporting_observation")
    if any(
        item is not None and item.get("status") != "success" for item in referenced
    ):
        reason_codes.append("non_current_observation_status")

    values_by_asset: Dict[str, List[Mapping[str, Any]]] = {}
    for value in signal.get("observed_values", []):
        values_by_asset.setdefault(str(value.get("asset")), []).append(value)
    if any(asset not in values_by_asset for asset in rule.required_assets):
        reason_codes.append("missing_required_asset_value")

    eligible = not reason_codes
    observed_state = "unavailable"
    contribution: Optional[float] = None
    if eligible:
        selected = {
            asset: values_by_asset[asset][0] for asset in rule.required_assets
        }
        observed_state = _dimension_state(rule, selected, signal)
        contribution = {
            "risk_on": 1.0,
            "mixed": 0.0,
            "risk_off": -1.0,
        }[observed_state]
        if signal.get("state") == "not_observed":
            reason_codes.append("relationship_condition_not_observed")
        else:
            reason_codes.append("current_relationship_observed")

    signal_refs = signal.get("evidence_refs", {})
    evidence_refs = {
        key: sorted(set(signal_refs.get(key, [])))
        for key in (
            "evidence_bundle_ids",
            "source_ids",
            "observation_ids",
            "event_ids",
            "evidence_ids",
        )
    }
    return RegimeDimension(
        dimension_id=rule.dimension_id,
        weight=rule.weight,
        signal_id=str(signal["signal_id"]),
        rule_id=rule.signal_rule_id,
        eligibility="eligible" if eligible else "unavailable",
        observed_state=observed_state,
        contribution=contribution,
        weighted_contribution=(
            round(rule.weight * contribution, 6)
            if contribution is not None
            else None
        ),
        observed_values=[dict(item) for item in signal.get("observed_values", [])],
        evidence_refs=evidence_refs,
        confidence=dict(signal.get("confidence", {})) if eligible else {
            "score": 0.0,
            "label": "insufficient",
            "basis": "data_quality",
        },
        reason_codes=sorted(set(reason_codes)),
    )


def _dimension_state(
    rule: RegimeDimensionRule,
    values: Mapping[str, Mapping[str, Any]],
    signal: Mapping[str, Any],
) -> str:
    thresholds = signal["rule_evaluation"]["thresholds"]
    numbers = [float(values[asset]["value"]) for asset in rule.required_assets]
    threshold_met = all(
        abs(number) >= float(thresholds[asset]["minimum_absolute_move"])
        for asset, number in zip(rule.required_assets, numbers)
    )
    if not threshold_met:
        return "mixed"
    signs = [_sign(number) for number in numbers]
    if rule.evaluator == "inverse_volatility":
        return "risk_on" if signs[0] < 0 else "risk_off"
    if len(set(signs)) != 1 or signs[0] == 0:
        return "mixed"
    if rule.evaluator == "inverse_pressure_pair":
        return "risk_on" if signs[0] < 0 else "risk_off"
    if rule.evaluator == "aligned_risk_assets":
        return "risk_on" if signs[0] > 0 else "risk_off"
    raise RegimeClassificationError(f"unsupported dimension evaluator: {rule.evaluator}")


def _validate_input_linkage(
    evidence_bundle: Mapping[str, Any],
    market_signals: Mapping[str, Any],
    generated: datetime,
) -> None:
    if market_signals.get("input_run_id") != evidence_bundle.get("run_id"):
        raise RegimeClassificationError("market signals do not reference evidence run")
    if market_signals.get("report_date") != evidence_bundle.get("report_date"):
        raise RegimeClassificationError("input report dates do not match")
    evidence_time = _parse_timestamp(str(evidence_bundle["generated_at"]))
    signal_time = _parse_timestamp(str(market_signals["generated_at"]))
    if signal_time < evidence_time:
        raise RegimeClassificationError("market signals predate evidence bundle")
    future_limit = MAXIMUM_FUTURE_SKEW_MINUTES * 60
    if (evidence_time - generated).total_seconds() > future_limit:
        raise RegimeClassificationError("evidence bundle is future-dated")
    if (signal_time - generated).total_seconds() > future_limit:
        raise RegimeClassificationError("market signals are future-dated")


def _input_freshness(
    evidence_bundle: Mapping[str, Any],
    market_signals: Mapping[str, Any],
    generated: datetime,
    signals_by_rule: Mapping[str, Mapping[str, Any]],
    stale_observation_ids: Set[str],
) -> Dict[str, Any]:
    evidence_time = _parse_timestamp(str(evidence_bundle["generated_at"]))
    signal_time = _parse_timestamp(str(market_signals["generated_at"]))
    ages = {
        "evidence_bundle.json": max(
            0.0, (generated - evidence_time).total_seconds() / 3600
        ),
        "market_signals.json": max(
            0.0, (generated - signal_time).total_seconds() / 3600
        ),
    }
    stale_artifacts = sorted(
        name for name, age in ages.items() if age > MAXIMUM_INPUT_AGE_HOURS
    )
    relevant_ids = {
        observation_id
        for rule in DIMENSION_RULES
        for observation_id in signals_by_rule[rule.signal_rule_id]
        .get("evidence_refs", {})
        .get("observation_ids", [])
    }
    stale_supporting = sorted(relevant_ids & stale_observation_ids)
    status = "stale" if stale_artifacts or stale_supporting else "current"
    return {
        "status": status,
        "checked_at": _iso_utc(generated),
        "maximum_artifact_age_hours": MAXIMUM_INPUT_AGE_HOURS,
        "artifacts": {
            "evidence_bundle.json": {
                "generated_at": _iso_utc(evidence_time),
                "age_hours": round(ages["evidence_bundle.json"], 6),
            },
            "market_signals.json": {
                "generated_at": _iso_utc(signal_time),
                "age_hours": round(ages["market_signals.json"], 6),
            },
        },
        "stale_artifacts": stale_artifacts,
        "stale_supporting_observation_ids": stale_supporting,
    }


def _index_evidence(
    evidence_bundle: Mapping[str, Any],
) -> Tuple[Dict[str, Mapping[str, Any]], Set[str]]:
    observations: Dict[str, Mapping[str, Any]] = {}
    stale: Set[str] = set()
    for bundle in evidence_bundle["bundles"]:
        stale.update(str(item) for item in bundle["freshness"]["stale_record_ids"])
        for observation in bundle["observations"]:
            observation_id = str(observation["observation_id"])
            observations.setdefault(observation_id, observation)
            if observation.get("status") == "stale":
                stale.add(observation_id)
    return observations, stale


def _merge_evidence_refs(
    dimensions: Sequence[RegimeDimension],
) -> Dict[str, List[str]]:
    keys = (
        "evidence_bundle_ids",
        "source_ids",
        "observation_ids",
        "event_ids",
        "evidence_ids",
    )
    return {
        key: sorted(
            {
                item
                for dimension in dimensions
                for item in dimension.evidence_refs.get(key, [])
            }
        )
        for key in keys
    }


def _sign(value: float) -> int:
    return 1 if value > 0 else -1 if value < 0 else 0


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise RegimeClassificationError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _iso_utc(value: datetime) -> str:
    return _as_utc(value).isoformat().replace("+00:00", "Z")
