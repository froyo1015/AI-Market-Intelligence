"""Evaluate descriptive cross-asset relationships from consolidated evidence."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

from src.consolidation.validator import validate_consolidated_evidence_artifact
from src.evidence.schema import confidence_label
from src.models.cross_asset_schema import (
    MarketSignalsArtifact,
    ObservedValue,
    RelationshipSignal,
)
from src.signals.rules import CrossAssetRule, RULE_SET_VERSION, RULES


@dataclass
class ObservationContext:
    record: Dict[str, Any]
    bundle_ids: Set[str] = field(default_factory=set)
    source_ids: Set[str] = field(default_factory=set)
    event_ids: Set[str] = field(default_factory=set)
    evidence_ids: Set[str] = field(default_factory=set)
    stale: bool = False


def build_market_signals_artifact(
    evidence_bundle: Mapping[str, Any],
    now: Optional[datetime] = None,
) -> MarketSignalsArtifact:
    """Evaluate every frozen rule without prediction or interpretation."""
    validate_consolidated_evidence_artifact(evidence_bundle)
    generated = _as_utc(now or datetime.now(timezone.utc))
    generated_at = _iso_utc(generated)
    index, conflicting_keys = _index_observations(evidence_bundle)
    signals = [
        _evaluate_rule(
            rule,
            index,
            conflicting_keys,
            str(evidence_bundle["run_id"]),
        )
        for rule in RULES
    ]
    warnings: List[str] = []
    stale_count = sum(item.state == "stale_data" for item in signals)
    insufficient_count = sum(item.state == "insufficient_data" for item in signals)
    if evidence_bundle.get("status") != "available":
        warnings.append(
            f"Input evidence coverage is {evidence_bundle.get('status')}."
        )
    if stale_count:
        warnings.append(
            f"{stale_count} relationship rule(s) use stale observations and "
            "are not marked observed."
        )
    if insufficient_count:
        warnings.append(
            f"{insufficient_count} relationship rule(s) have insufficient data."
        )
    if evidence_bundle.get("status") == "unavailable" or (
        all(item.state == "insufficient_data" for item in signals)
        and not any(item.observed_values for item in signals)
    ):
        status = "unavailable"
    elif (
        evidence_bundle.get("status") != "available"
        or stale_count
        or insufficient_count
    ):
        status = "partial"
    else:
        status = "available"
    input_run_id = str(evidence_bundle["run_id"])
    digest = hashlib.sha256(
        f"{input_run_id}|{generated_at}|{RULE_SET_VERSION}".encode("utf-8")
    ).hexdigest()[:16]
    return MarketSignalsArtifact(
        run_id=f"run_{generated:%Y%m%dT%H%M%SZ}_relationships_{digest}",
        report_date=str(evidence_bundle["report_date"]),
        generated_at=generated_at,
        status=status,
        input_run_id=input_run_id,
        warnings=warnings,
        signals=signals,
    )


def _index_observations(
    artifact: Mapping[str, Any],
) -> Tuple[
    Dict[Tuple[str, str], Dict[str, ObservationContext]],
    Set[Tuple[str, str]],
]:
    index: Dict[Tuple[str, str], Dict[str, ObservationContext]] = {}
    conflicting_keys: Set[Tuple[str, str]] = set()
    records_by_id: Dict[str, Dict[str, Any]] = {}
    for bundle in artifact["bundles"]:
        bundle_id = str(bundle["id"])
        provenance = bundle["provenance"]
        stale_ids = set(bundle["freshness"]["stale_record_ids"])
        for raw_observation in bundle["observations"]:
            observation = dict(raw_observation)
            observation_id = str(observation["observation_id"])
            key = (str(observation["subject"]), str(observation["metric"]))
            previous = records_by_id.get(observation_id)
            if previous is not None and previous != observation:
                conflicting_keys.add(key)
                continue
            records_by_id[observation_id] = observation
            contexts = index.setdefault(key, {})
            context = contexts.get(observation_id)
            if context is None:
                context = ObservationContext(record=observation)
                contexts[observation_id] = context
            context.bundle_ids.add(bundle_id)
            context.source_ids.update(provenance["source_ids"])
            context.event_ids.update(provenance["event_ids"])
            context.evidence_ids.update(provenance["evidence_ids"])
            context.stale = context.stale or (
                observation.get("status") == "stale"
                or observation_id in stale_ids
            )
    return index, conflicting_keys


def _evaluate_rule(
    rule: CrossAssetRule,
    index: Mapping[Tuple[str, str], Dict[str, ObservationContext]],
    conflicting_keys: Set[Tuple[str, str]],
    input_run_id: str,
) -> RelationshipSignal:
    candidates: List[List[ObservationContext]] = []
    missing_inputs: List[str] = []
    conflicting_inputs: List[str] = []
    for required in rule.required_inputs:
        key = (required.asset, required.metric)
        matches = list(index.get(key, {}).values())
        matches.sort(key=lambda item: str(item.record["observation_id"]))
        candidates.append(matches)
        name = f"{required.asset}:{required.metric}"
        if not matches:
            missing_inputs.append(name)
        elif key in conflicting_keys or not _compatible_candidates(matches):
            conflicting_inputs.append(name)

    all_contexts = [context for matches in candidates for context in matches]
    observed_values = [
        _observed_value(context)
        for context in all_contexts
        if _is_number(context.record.get("value"))
    ]
    observed_values.sort(
        key=lambda item: (item.asset, item.metric, item.observation_id)
    )
    evidence_refs = {
        "evidence_bundle_ids": sorted(
            {item for context in all_contexts for item in context.bundle_ids}
        ),
        "source_ids": sorted(
            {item for context in all_contexts for item in context.source_ids}
        ),
        "observation_ids": sorted(
            str(context.record["observation_id"]) for context in all_contexts
        ),
        "event_ids": sorted(
            {item for context in all_contexts for item in context.event_ids}
        ),
        "evidence_ids": sorted(
            {item for context in all_contexts for item in context.evidence_ids}
        ),
    }

    issues: List[str] = []
    if missing_inputs:
        issues.append("missing_required_observation")
    if conflicting_inputs:
        issues.append("conflicting_observation_candidates")
    selected = [
        _merge_compatible_candidates(matches)
        for matches in candidates
        if matches and _compatible_candidates(matches)
    ]
    invalid_values = [
        f"{context.record.get('subject')}:{context.record.get('metric')}"
        for context in selected
        if not _valid_required_value(context.record, rule)
    ]
    if invalid_values:
        issues.append("invalid_observation_value_or_unit")
        conflicting_inputs.extend(invalid_values)

    actual_time_gap: Optional[float] = None
    if len(selected) == len(rule.required_inputs):
        timestamps = [_parse_timestamp(str(item.record["as_of"])) for item in selected]
        actual_time_gap = (
            max(timestamps) - min(timestamps)
        ).total_seconds() / 3600
        if actual_time_gap > rule.maximum_time_gap_hours:
            issues.append("observation_time_gap_exceeded")

    complete = not issues and len(selected) == len(rule.required_inputs)
    values = [float(item.record["value"]) for item in selected]
    thresholds_met: Optional[bool]
    comparison_result: Optional[bool]
    if complete:
        thresholds_met = all(
            abs(value) >= required.minimum_absolute_move
            for value, required in zip(values, rule.required_inputs)
        )
        comparison_result = thresholds_met and _operator_result(rule, values)
    else:
        thresholds_met = None
        comparison_result = None

    stale_ids = sorted(
        str(item.record["observation_id"]) for item in all_contexts if item.stale
    )
    if stale_ids:
        issues.append("stale_observation")
    if not complete:
        state = "insufficient_data"
        condition_met = None
        score = 0.0
    elif stale_ids:
        state = "stale_data"
        condition_met = comparison_result
        score = min(_base_confidence(all_contexts) * 0.50, 0.50)
    else:
        state = "observed" if comparison_result else "not_observed"
        condition_met = comparison_result
        score = _base_confidence(all_contexts)

    signal_id = _signal_id(
        rule.rule_id,
        evidence_refs["observation_ids"],
        input_run_id,
    )
    thresholds = {
        item.asset: {
            "minimum_absolute_move": item.minimum_absolute_move,
            "unit": item.unit,
        }
        for item in rule.required_inputs
    }
    rule_evaluation: Dict[str, Any] = {
        "operator": rule.operator,
        "thresholds": thresholds,
        "spread_threshold": rule.spread_threshold,
        "spread_threshold_unit": (
            "percentage_points" if rule.spread_threshold is not None else None
        ),
        "maximum_time_gap_hours": rule.maximum_time_gap_hours,
        "actual_time_gap_hours": (
            round(actual_time_gap, 6) if actual_time_gap is not None else None
        ),
        "thresholds_met": thresholds_met,
        "comparison_result": comparison_result,
        "rule_version": "v1",
    }
    limitations = [rule.limitation]
    if missing_inputs:
        limitations.append("One or more required observations are unavailable.")
    if conflicting_inputs:
        limitations.append(
            "Multiple incompatible observations prevent deterministic evaluation."
        )
    if actual_time_gap is not None and actual_time_gap > rule.maximum_time_gap_hours:
        limitations.append(
            "Required observations fall outside the permitted comparison window."
        )
    if stale_ids:
        limitations.append(
            "One or more required observations are stale; the relationship is not current."
        )
    data_quality_status = (
        "unavailable"
        if not observed_values
        else "partial"
        if issues
        else "available"
    )
    return RelationshipSignal(
        signal_id=signal_id,
        rule_id=rule.rule_id,
        signal_type="cross_asset_relationship",
        relationship_kind=rule.relationship_kind,
        label=rule.label,
        state=state,
        condition_met=condition_met,
        required_assets=[item.asset for item in rule.required_inputs],
        observed_values=observed_values,
        rule_evaluation=rule_evaluation,
        evidence_refs=evidence_refs,
        confidence={
            "score": round(score, 6),
            "label": confidence_label(score).value,
            "basis": "data_quality",
        },
        data_quality={
            "status": data_quality_status,
            "issues": sorted(set(issues)),
            "missing_inputs": sorted(set(missing_inputs)),
            "stale_observation_ids": stale_ids,
            "conflicting_inputs": sorted(set(conflicting_inputs)),
        },
        limitations=limitations,
    )


def _operator_result(rule: CrossAssetRule, values: Sequence[float]) -> bool:
    signs = [_sign(value) for value in values]
    if rule.operator == "same_sign":
        return len(set(signs)) == 1 and signs[0] != 0
    if rule.operator == "opposite_sign":
        return len(signs) == 2 and signs[0] == -signs[1] and signs[0] != 0
    if rule.operator == "equity_pair_inverse_third":
        return (
            signs[0] == signs[1]
            and signs[0] != 0
            and signs[2] == -signs[0]
        )
    if rule.operator == "dollar_fx_quote_alignment":
        return (
            signs[0] != 0
            and signs[1] == -signs[0]
            and signs[2] == signs[0]
        )
    if rule.operator == "opposite_sign_with_spread":
        return (
            signs[0] == -signs[1]
            and signs[0] != 0
            and rule.spread_threshold is not None
            and abs(values[0] - values[1]) >= rule.spread_threshold
        )
    raise ValueError(f"unsupported cross-asset operator: {rule.operator}")


def _valid_required_value(
    observation: Mapping[str, Any],
    rule: CrossAssetRule,
) -> bool:
    asset = observation.get("subject")
    metric = observation.get("metric")
    expected = next(
        (
            item
            for item in rule.required_inputs
            if item.asset == asset and item.metric == metric
        ),
        None,
    )
    return bool(
        expected is not None
        and observation.get("unit") == expected.unit
        and _is_number(observation.get("value"))
        and math.isfinite(float(observation["value"]))
    )


def _compatible_candidates(contexts: Sequence[ObservationContext]) -> bool:
    if not contexts:
        return False
    signatures = {
        (
            item.record.get("subject"),
            item.record.get("metric"),
            item.record.get("value"),
            item.record.get("unit"),
            item.record.get("as_of"),
        )
        for item in contexts
    }
    return len(signatures) == 1


def _merge_compatible_candidates(
    contexts: Sequence[ObservationContext],
) -> ObservationContext:
    primary = min(
        contexts,
        key=lambda item: str(item.record["observation_id"]),
    )
    merged = ObservationContext(record=dict(primary.record))
    for context in contexts:
        merged.bundle_ids.update(context.bundle_ids)
        merged.source_ids.update(context.source_ids)
        merged.event_ids.update(context.event_ids)
        merged.evidence_ids.update(context.evidence_ids)
        merged.stale = merged.stale or context.stale
    return merged


def _observed_value(context: ObservationContext) -> ObservedValue:
    record = context.record
    return ObservedValue(
        asset=str(record["subject"]),
        metric=str(record["metric"]),
        value=float(record["value"]),
        unit=str(record["unit"]),
        as_of=_iso_utc(_parse_timestamp(str(record["as_of"]))),
        observation_id=str(record["observation_id"]),
        source_id=str(record["source_id"]),
        evidence_bundle_ids=sorted(context.bundle_ids),
    )


def _base_confidence(contexts: Sequence[ObservationContext]) -> float:
    scores = [
        float(item.record.get("confidence_score"))
        for item in contexts
        if _is_number(item.record.get("confidence_score"))
    ]
    return min(scores) if len(scores) == len(contexts) and scores else 0.0


def _signal_id(
    rule_id: str,
    observation_ids: Sequence[str],
    input_run_id: str,
) -> str:
    key = f"{rule_id}|{'|'.join(sorted(observation_ids))}|{input_run_id}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]
    return f"sig_{rule_id}_{digest}"


def _sign(value: float) -> int:
    return 1 if value > 0 else -1 if value < 0 else 0


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _iso_utc(value: datetime) -> str:
    return _as_utc(value).isoformat().replace("+00:00", "Z")
