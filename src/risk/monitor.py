"""Build deterministic observable-risk items from linked factual artifacts."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

from src.models.risk_schema import RiskItem, RiskMonitorArtifact
from src.regime.validator import validate_market_regime_artifact
from src.risk.rules import (
    MAXIMUM_FUTURE_SKEW_MINUTES,
    MAXIMUM_INPUT_AGE_HOURS,
    MARKET_STRESS_RULES,
    RULE_SET_VERSION,
    UPCOMING_EVENT_WINDOW_HOURS,
    MarketStressRule,
)


REFERENCE_KEYS = (
    "artifact_run_ids",
    "evidence_bundle_ids",
    "source_ids",
    "observation_ids",
    "event_ids",
    "evidence_ids",
    "signal_ids",
    "regime_dimension_ids",
    "coverage_inputs",
)


class RiskMonitorError(ValueError):
    """Raised when Phase 6.3-C inputs are not a consistent linked run."""


def build_risk_monitor_artifact(
    evidence_bundle: Mapping[str, Any],
    market_signals: Mapping[str, Any],
    market_regime: Mapping[str, Any],
    now: Optional[datetime] = None,
) -> RiskMonitorArtifact:
    generated = _as_utc(now or datetime.now(timezone.utc))
    validate_market_regime_artifact(
        market_regime,
        evidence_bundle,
        market_signals,
    )
    _validate_linkage(evidence_bundle, market_signals, market_regime, generated)
    input_refs = {
        "evidence_bundle_run_id": str(evidence_bundle["run_id"]),
        "market_signals_run_id": str(market_signals["run_id"]),
        "market_regime_run_id": str(market_regime["run_id"]),
    }
    indexes = _build_indexes(evidence_bundle)
    freshness = _input_freshness(
        evidence_bundle,
        market_signals,
        market_regime,
        generated,
        indexes["stale_ids"],
    )
    risks: List[RiskItem] = []
    risks.extend(
        _upcoming_event_risks(
            evidence_bundle,
            generated,
            indexes,
            freshness,
            input_refs,
        )
    )
    risks.extend(
        _data_quality_risks(
            evidence_bundle,
            market_signals,
            market_regime,
            freshness,
            indexes,
            input_refs,
            generated,
        )
    )
    risks.extend(
        _market_stress_risks(
            market_signals,
            market_regime,
            freshness,
            indexes,
            input_refs,
            generated,
        )
    )
    risks = _deduplicate_and_sort(risks)
    degraded = (
        freshness["status"] != "current"
        or evidence_bundle.get("status") != "available"
        or market_signals.get("status") != "available"
        or market_regime.get("status") != "available"
    )
    status = "partial" if degraded else "available"
    warnings: List[str] = []
    if degraded:
        warnings.append("One or more monitor inputs have degraded coverage or freshness.")
    if not any(item.category == "upcoming_event" for item in risks):
        warnings.append("No eligible official events were found in the next 48 hours.")
    if not any(item.category == "market_stress" for item in risks):
        warnings.append("No current market-stress rule is supported by eligible evidence.")

    generated_at = _iso_utc(generated)
    digest = hashlib.sha256(
        (
            f"{input_refs['evidence_bundle_run_id']}|"
            f"{input_refs['market_signals_run_id']}|"
            f"{input_refs['market_regime_run_id']}|{generated_at}|{RULE_SET_VERSION}"
        ).encode("utf-8")
    ).hexdigest()[:16]
    return RiskMonitorArtifact(
        run_id=f"run_{generated:%Y%m%dT%H%M%SZ}_risk_{digest}",
        report_date=str(evidence_bundle["report_date"]),
        generated_at=generated_at,
        status=status,
        input_refs=input_refs,
        input_freshness=freshness,
        risks=risks,
        warnings=warnings,
        limitations=[
            "Risk items describe scheduled events, data quality, or current observations.",
            "They do not establish causality, persistence, or later outcomes.",
            "No item is an investment or trading instruction.",
        ],
    )


def _upcoming_event_risks(
    evidence_bundle: Mapping[str, Any],
    generated: datetime,
    indexes: Mapping[str, Any],
    freshness: Mapping[str, Any],
    input_refs: Mapping[str, str],
) -> List[RiskItem]:
    if "evidence_bundle.json" in freshness["stale_artifacts"]:
        return []
    window_end = generated + timedelta(hours=UPCOMING_EVENT_WINDOW_HOURS)
    risks: List[RiskItem] = []
    for bundle in evidence_bundle["bundles"]:
        if bundle.get("type") != "calendar_event":
            continue
        if bundle.get("freshness", {}).get("status") == "stale":
            continue
        for event in bundle.get("events", []):
            event_id = str(event["event_id"])
            if event_id in indexes["stale_ids"] or event.get("status") != "scheduled":
                continue
            scheduled = _parse_timestamp(str(event["scheduled_at"]))
            if not generated < scheduled <= window_end:
                continue
            refs = _bundle_refs(bundle, input_refs.values())
            impact = str(event.get("impact", "low")).casefold()
            attention = impact if impact in {"high", "medium"} else "low"
            facts = {
                "event_id": event_id,
                "name": str(event["name"]),
                "scheduled_at": _iso_utc(scheduled),
                "country": str(event.get("country", "unknown")),
                "impact": impact,
                "topics": sorted(set(event.get("topics", []))),
            }
            risks.append(
                _risk_item(
                    rule_id="upcoming_official_event_v1",
                    category="upcoming_event",
                    status="scheduled",
                    attention_level=attention,
                    title=f"Scheduled official event: {event['name']}",
                    description=(
                        "An official calendar event is scheduled within the "
                        "next 48 hours."
                    ),
                    related_assets=event.get("affected_assets", []),
                    time_window={
                        "scheduled_at": _iso_utc(scheduled),
                        "window_start": _iso_utc(generated),
                        "window_end": _iso_utc(window_end),
                    },
                    observed_facts=facts,
                    refs=refs,
                    verification={
                        "level": str(bundle.get("verification_level", "unverified")),
                        "score": float(event.get("confidence_score", 0.0)),
                        "basis": "official_calendar_record",
                    },
                    limitations=[
                        "The scheduled event does not imply a specific market response."
                    ],
                    identity_parts=[event_id, _iso_utc(scheduled)],
                )
            )
    return risks


def _data_quality_risks(
    evidence_bundle: Mapping[str, Any],
    market_signals: Mapping[str, Any],
    market_regime: Mapping[str, Any],
    freshness: Mapping[str, Any],
    indexes: Mapping[str, Any],
    input_refs: Mapping[str, str],
    generated: datetime,
) -> List[RiskItem]:
    risks: List[RiskItem] = []
    for coverage in evidence_bundle["coverage"]:
        if coverage.get("status") == "available" and not coverage.get(
            "stale_record_count"
        ):
            continue
        input_type = str(coverage["input_type"])
        refs = _coverage_refs(input_type, evidence_bundle["bundles"])
        refs["artifact_run_ids"] = [str(evidence_bundle["run_id"])]
        refs["coverage_inputs"] = [input_type]
        status = str(coverage.get("status"))
        risks.append(
            _risk_item(
                rule_id="input_coverage_degraded_v1",
                category="data_quality",
                status="detected",
                attention_level="high" if status == "unavailable" else "medium",
                title=f"Degraded input coverage: {input_type}",
                description=(
                    "The consolidated Evidence input reports incomplete or stale coverage."
                ),
                related_assets=_assets_for_refs(refs, indexes),
                time_window={"detected_at": _iso_utc(generated)},
                observed_facts={
                    "input_type": input_type,
                    "artifact": str(coverage["artifact"]),
                    "coverage_status": status,
                    "record_count": int(coverage["record_count"]),
                    "stale_record_count": int(coverage["stale_record_count"]),
                },
                refs=refs,
                verification={
                    "level": "verified",
                    "score": 1.0,
                    "basis": "artifact_coverage_metadata",
                },
                limitations=["This item concerns data reliability, not market prices."],
                identity_parts=[input_type, status],
            )
        )

    if evidence_bundle.get("rejection_count", 0):
        reason_codes = sorted(
            {
                reason
                for rejection in evidence_bundle.get("rejections", [])
                for reason in rejection.get("reason_codes", [])
            }
        )
        risks.append(
            _risk_item(
                rule_id="consolidation_rejections_present_v1",
                category="data_quality",
                status="detected",
                attention_level="medium",
                title="Evidence consolidation rejections present",
                description="One or more input records failed consolidation validation.",
                related_assets=[],
                time_window={"detected_at": _iso_utc(generated)},
                observed_facts={
                    "rejection_count": int(evidence_bundle["rejection_count"]),
                    "reason_codes": reason_codes,
                },
                refs=_empty_refs([str(evidence_bundle["run_id"])]),
                verification={
                    "level": "verified",
                    "score": 1.0,
                    "basis": "artifact_rejection_audit",
                },
                limitations=["Rejected records are not used as market evidence."],
                identity_parts=reason_codes,
            )
        )

    degraded_signals = [
        item
        for item in market_signals["signals"]
        if item.get("state") in {"stale_data", "insufficient_data"}
    ]
    if market_signals.get("status") != "available" or degraded_signals:
        refs = _refs_from_signals(degraded_signals, input_refs.values())
        state_counts = {
            state: sum(item.get("state") == state for item in market_signals["signals"])
            for state in ("observed", "not_observed", "stale_data", "insufficient_data")
        }
        risks.append(
            _risk_item(
                rule_id="market_signal_coverage_degraded_v1",
                category="data_quality",
                status="detected",
                attention_level=(
                    "high" if market_signals.get("status") == "unavailable" else "medium"
                ),
                title="Cross-asset relationship coverage degraded",
                description=(
                    "One or more cross-asset relationship evaluations are stale "
                    "or incomplete."
                ),
                related_assets=_assets_for_refs(refs, indexes),
                time_window={"detected_at": _iso_utc(generated)},
                observed_facts={
                    "artifact_status": str(market_signals["status"]),
                    "state_counts": state_counts,
                },
                refs=refs,
                verification={
                    "level": "verified",
                    "score": 1.0,
                    "basis": "deterministic_signal_metadata",
                },
                limitations=["This item concerns analytical coverage only."],
                identity_parts=[str(market_signals["status"])],
            )
        )

    if market_regime.get("status") != "available" or market_regime.get(
        "classification"
    ) is None:
        refs = _refs_from_regime(market_regime, input_refs.values())
        risks.append(
            _risk_item(
                rule_id="market_regime_coverage_degraded_v1",
                category="data_quality",
                status="detected",
                attention_level=(
                    "high"
                    if market_regime.get("classification") is None
                    else "medium"
                ),
                title="Current market regime coverage degraded",
                description=(
                    "The current-condition classifier reports partial or "
                    "insufficient eligible coverage."
                ),
                related_assets=_assets_for_refs(refs, indexes),
                time_window={"detected_at": _iso_utc(generated)},
                observed_facts={
                    "artifact_status": str(market_regime["status"]),
                    "classification": market_regime.get("classification"),
                    "eligible_dimension_count": int(
                        market_regime["score"]["eligible_dimension_count"]
                    ),
                    "eligible_weight": float(
                        market_regime["score"]["eligible_weight"]
                    ),
                },
                refs=refs,
                verification={
                    "level": "verified",
                    "score": 1.0,
                    "basis": "deterministic_regime_metadata",
                },
                limitations=["No unavailable regime is treated as mixed."],
                identity_parts=[
                    str(market_regime["status"]),
                    str(market_regime.get("classification")),
                ],
            )
        )

    for artifact_name in freshness["stale_artifacts"]:
        run_key = {
            "evidence_bundle.json": "evidence_bundle_run_id",
            "market_signals.json": "market_signals_run_id",
            "market_regime.json": "market_regime_run_id",
        }[artifact_name]
        risks.append(
            _risk_item(
                rule_id="input_artifact_stale_v1",
                category="data_quality",
                status="detected",
                attention_level="high",
                title=f"Stale monitor input: {artifact_name}",
                description="A required monitor artifact exceeds the freshness limit.",
                related_assets=[],
                time_window={"detected_at": _iso_utc(generated)},
                observed_facts={
                    "artifact": artifact_name,
                    "age_hours": freshness["artifacts"][artifact_name]["age_hours"],
                    "maximum_age_hours": MAXIMUM_INPUT_AGE_HOURS,
                },
                refs=_empty_refs([input_refs[run_key]]),
                verification={
                    "level": "verified",
                    "score": 1.0,
                    "basis": "artifact_timestamp",
                },
                limitations=["Stale inputs cannot support current market stress."],
                identity_parts=[artifact_name],
            )
        )
    return risks


def _market_stress_risks(
    market_signals: Mapping[str, Any],
    market_regime: Mapping[str, Any],
    freshness: Mapping[str, Any],
    indexes: Mapping[str, Any],
    input_refs: Mapping[str, str],
    generated: datetime,
) -> List[RiskItem]:
    signals_by_rule = {item["rule_id"]: item for item in market_signals["signals"]}
    risks: List[RiskItem] = []
    if (
        market_regime.get("classification") == "risk_off"
        and market_regime.get("status") in {"available", "partial"}
        and _refs_are_current(market_regime["evidence_refs"], indexes)
        and not freshness["stale_artifacts"]
    ):
        refs = _refs_from_regime(market_regime, input_refs.values())
        risks.append(
            _risk_item(
                rule_id="observed_risk_off_regime_v1",
                category="market_stress",
                status="observed",
                attention_level="high",
                title="Observed current risk-off regime",
                description=(
                    "The deterministic current-condition classifier reports "
                    "risk_off with sufficient eligible coverage."
                ),
                related_assets=_assets_for_refs(refs, indexes),
                time_window={"observed_at": str(market_regime["generated_at"])},
                observed_facts={
                    "classification": "risk_off",
                    "normalized_score": float(
                        market_regime["score"]["normalized_score"]
                    ),
                    "eligible_weight": float(
                        market_regime["score"]["eligible_weight"]
                    ),
                },
                refs=refs,
                verification={
                    "level": str(market_regime["confidence"]["label"]),
                    "score": float(market_regime["confidence"]["score"]),
                    "basis": "current_regime_evidence",
                },
                limitations=[
                    "The current regime does not imply persistence or a later outcome."
                ],
                identity_parts=[str(market_regime["run_id"])],
            )
        )

    for rule in MARKET_STRESS_RULES:
        signal = signals_by_rule[rule.signal_rule_id]
        if not _signal_is_current_observed(signal, indexes, freshness):
            continue
        if not _stress_condition(rule, signal):
            continue
        refs = _refs_from_signals([signal], input_refs.values())
        values = [dict(item) for item in signal["observed_values"]]
        observed_times = sorted(set(str(item["as_of"]) for item in values))
        risks.append(
            _risk_item(
                rule_id=rule.rule_id,
                category="market_stress",
                status="observed",
                attention_level=rule.attention_level,
                title=rule.title,
                description=rule.description,
                related_assets=sorted(
                    set(str(item["asset"]) for item in values)
                ),
                time_window={"observed_at": observed_times},
                observed_facts={
                    "signal_id": str(signal["signal_id"]),
                    "signal_rule_id": str(signal["rule_id"]),
                    "condition_met": bool(signal["condition_met"]),
                    "observations": values,
                },
                refs=refs,
                verification={
                    "level": str(signal["confidence"]["label"]),
                    "score": float(signal["confidence"]["score"]),
                    "basis": "current_signal_evidence",
                },
                limitations=[
                    "The observed condition does not imply persistence or causality."
                ],
                identity_parts=[str(signal["signal_id"])],
            )
        )
    return risks


def _stress_condition(rule: MarketStressRule, signal: Mapping[str, Any]) -> bool:
    values = {str(item["asset"]): float(item["value"]) for item in signal["observed_values"]}
    if rule.evaluator == "equities_lower_vix_higher":
        return values["SPY"] < 0 and values["QQQ"] < 0 and values["VIX"] > 0
    if rule.evaluator == "all_required_lower":
        return all(values[asset] < 0 for asset in ("SPY", "QQQ", "BTC-USD"))
    if rule.evaluator == "all_required_higher":
        return values["DXY"] > 0 and values["US10Y"] > 0
    if rule.evaluator == "condition_observed":
        return signal.get("condition_met") is True
    raise RiskMonitorError(f"unsupported market stress evaluator: {rule.evaluator}")


def _signal_is_current_observed(
    signal: Mapping[str, Any],
    indexes: Mapping[str, Any],
    freshness: Mapping[str, Any],
) -> bool:
    return (
        not freshness["stale_artifacts"]
        and signal.get("state") == "observed"
        and signal.get("condition_met") is True
        and signal.get("data_quality", {}).get("status") == "available"
        and _refs_are_current(signal.get("evidence_refs", {}), indexes)
    )


def _validate_linkage(
    evidence_bundle: Mapping[str, Any],
    market_signals: Mapping[str, Any],
    market_regime: Mapping[str, Any],
    generated: datetime,
) -> None:
    if market_signals.get("input_run_id") != evidence_bundle.get("run_id"):
        raise RiskMonitorError("market signals do not reference evidence run")
    refs = market_regime.get("input_refs", {})
    if refs.get("evidence_bundle_run_id") != evidence_bundle.get("run_id"):
        raise RiskMonitorError("market regime does not reference evidence run")
    if refs.get("market_signals_run_id") != market_signals.get("run_id"):
        raise RiskMonitorError("market regime does not reference signal run")
    report_dates = {
        evidence_bundle.get("report_date"),
        market_signals.get("report_date"),
        market_regime.get("report_date"),
    }
    if len(report_dates) != 1:
        raise RiskMonitorError("input report dates do not match")
    times = [
        _parse_timestamp(str(item["generated_at"]))
        for item in (evidence_bundle, market_signals, market_regime)
    ]
    if times != sorted(times):
        raise RiskMonitorError("input artifacts are out of generation order")
    future_limit = MAXIMUM_FUTURE_SKEW_MINUTES * 60
    if any((item - generated).total_seconds() > future_limit for item in times):
        raise RiskMonitorError("one or more monitor inputs are future-dated")


def _input_freshness(
    evidence_bundle: Mapping[str, Any],
    market_signals: Mapping[str, Any],
    market_regime: Mapping[str, Any],
    generated: datetime,
    stale_ids: Set[str],
) -> Dict[str, Any]:
    artifacts = {
        "evidence_bundle.json": evidence_bundle,
        "market_signals.json": market_signals,
        "market_regime.json": market_regime,
    }
    details: Dict[str, Dict[str, Any]] = {}
    stale_artifacts: List[str] = []
    for name, artifact in artifacts.items():
        timestamp = _parse_timestamp(str(artifact["generated_at"]))
        age = max(0.0, (generated - timestamp).total_seconds() / 3600)
        details[name] = {
            "generated_at": _iso_utc(timestamp),
            "age_hours": round(age, 6),
        }
        if age > MAXIMUM_INPUT_AGE_HOURS:
            stale_artifacts.append(name)
    return {
        "status": "stale" if stale_artifacts or stale_ids else "current",
        "checked_at": _iso_utc(generated),
        "maximum_artifact_age_hours": MAXIMUM_INPUT_AGE_HOURS,
        "artifacts": details,
        "stale_artifacts": sorted(stale_artifacts),
        "stale_supporting_observation_ids": sorted(stale_ids),
    }


def _build_indexes(evidence_bundle: Mapping[str, Any]) -> Dict[str, Any]:
    observations: Dict[str, Mapping[str, Any]] = {}
    sources: Dict[str, Mapping[str, Any]] = {}
    events: Dict[str, Mapping[str, Any]] = {}
    evidence: Dict[str, Mapping[str, Any]] = {}
    bundles: Dict[str, Mapping[str, Any]] = {}
    stale_ids: Set[str] = set()
    for bundle in evidence_bundle["bundles"]:
        bundles[str(bundle["id"])] = bundle
        stale_ids.update(str(item) for item in bundle["freshness"]["stale_record_ids"])
        for item in bundle["source_records"]:
            sources.setdefault(str(item["source_id"]), item)
        for item in bundle["observations"]:
            item_id = str(item["observation_id"])
            observations.setdefault(item_id, item)
            if item.get("status") == "stale":
                stale_ids.add(item_id)
        for item in bundle["events"]:
            events.setdefault(str(item["event_id"]), item)
        for item in bundle["evidence_records"]:
            evidence.setdefault(str(item["evidence_id"]), item)
    return {
        "observations": observations,
        "sources": sources,
        "events": events,
        "evidence": evidence,
        "bundles": bundles,
        "stale_ids": stale_ids,
    }


def _refs_are_current(refs: Mapping[str, Any], indexes: Mapping[str, Any]) -> bool:
    observation_ids = set(refs.get("observation_ids", []))
    if observation_ids & indexes["stale_ids"]:
        return False
    return all(
        item in indexes["observations"]
        and indexes["observations"][item].get("status") == "success"
        for item in observation_ids
    )


def _coverage_refs(
    input_type: str,
    bundles: Sequence[Mapping[str, Any]],
) -> Dict[str, List[str]]:
    selected: List[Mapping[str, Any]] = []
    for bundle in bundles:
        observations = bundle.get("observations", [])
        if input_type == "market_observations" and any(
            item.get("observation_type") != "macro_value" for item in observations
        ):
            selected.append(bundle)
        elif input_type == "macro_observations" and any(
            item.get("observation_type") == "macro_value" for item in observations
        ):
            selected.append(bundle)
        elif input_type == "economic_calendar" and bundle.get("type") == "calendar_event":
            selected.append(bundle)
        elif input_type == "news_events" and bundle.get("type") == "news_event":
            selected.append(bundle)
        elif input_type == "existing_evidence" and bundle.get("evidence_records"):
            selected.append(bundle)
    refs = _empty_refs([])
    for bundle in selected:
        refs = _merge_refs(refs, _bundle_refs(bundle, []))
    return refs


def _bundle_refs(
    bundle: Mapping[str, Any],
    artifact_run_ids: Iterable[str],
) -> Dict[str, List[str]]:
    provenance = bundle["provenance"]
    return {
        "artifact_run_ids": sorted(set(artifact_run_ids)),
        "evidence_bundle_ids": [str(bundle["id"])],
        "source_ids": sorted(set(provenance["source_ids"])),
        "observation_ids": sorted(set(provenance["observation_ids"])),
        "event_ids": sorted(set(provenance["event_ids"])),
        "evidence_ids": sorted(set(provenance["evidence_ids"])),
        "signal_ids": [],
        "regime_dimension_ids": [],
        "coverage_inputs": [],
    }


def _refs_from_signals(
    signals: Sequence[Mapping[str, Any]],
    artifact_run_ids: Iterable[str],
) -> Dict[str, List[str]]:
    refs = _empty_refs(artifact_run_ids)
    for signal in signals:
        source_refs = signal.get("evidence_refs", {})
        refs["signal_ids"].append(str(signal["signal_id"]))
        for key in (
            "evidence_bundle_ids",
            "source_ids",
            "observation_ids",
            "event_ids",
            "evidence_ids",
        ):
            refs[key].extend(str(item) for item in source_refs.get(key, []))
    return _normalize_refs(refs)


def _refs_from_regime(
    market_regime: Mapping[str, Any],
    artifact_run_ids: Iterable[str],
) -> Dict[str, List[str]]:
    refs = _empty_refs(artifact_run_ids)
    source_refs = market_regime.get("evidence_refs", {})
    for key in (
        "evidence_bundle_ids",
        "source_ids",
        "observation_ids",
        "event_ids",
        "evidence_ids",
    ):
        refs[key].extend(str(item) for item in source_refs.get(key, []))
    for dimension in market_regime.get("dimensions", []):
        refs["regime_dimension_ids"].append(str(dimension["dimension_id"]))
        refs["signal_ids"].append(str(dimension["signal_id"]))
        for key in (
            "evidence_bundle_ids",
            "source_ids",
            "observation_ids",
            "event_ids",
            "evidence_ids",
        ):
            refs[key].extend(
                str(item) for item in dimension.get("evidence_refs", {}).get(key, [])
            )
    return _normalize_refs(refs)


def _assets_for_refs(
    refs: Mapping[str, Sequence[str]],
    indexes: Mapping[str, Any],
) -> List[str]:
    assets: Set[str] = set()
    for observation_id in refs.get("observation_ids", []):
        observation = indexes["observations"].get(observation_id)
        if observation:
            assets.update(str(item) for item in observation.get("asset_mapping", []))
    for event_id in refs.get("event_ids", []):
        event = indexes["events"].get(event_id)
        if event:
            assets.update(str(item) for item in event.get("affected_assets", []))
            assets.update(str(item) for item in event.get("candidate_assets", []))
    for evidence_id in refs.get("evidence_ids", []):
        record = indexes["evidence"].get(evidence_id)
        if record:
            assets.update(str(item) for item in record.get("affected_assets", []))
    return sorted(assets)


def _risk_item(
    rule_id: str,
    category: str,
    status: str,
    attention_level: str,
    title: str,
    description: str,
    related_assets: Sequence[str],
    time_window: Mapping[str, Any],
    observed_facts: Mapping[str, Any],
    refs: Mapping[str, Sequence[str]],
    verification: Mapping[str, Any],
    limitations: Sequence[str],
    identity_parts: Sequence[str],
) -> RiskItem:
    normalized_refs = _normalize_refs(refs)
    identity = "|".join(
        [rule_id]
        + list(identity_parts)
        + [item for key in REFERENCE_KEYS for item in normalized_refs[key]]
    )
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
    return RiskItem(
        risk_id=f"rsk_{rule_id}_{digest}",
        rule_id=rule_id,
        category=category,
        status=status,
        attention_level=attention_level,
        title=title,
        description=description,
        related_assets=sorted(set(str(item) for item in related_assets)),
        time_window=dict(time_window),
        observed_facts=dict(observed_facts),
        evidence_refs=normalized_refs,
        verification=dict(verification),
        limitations=list(limitations),
    )


def _empty_refs(artifact_run_ids: Iterable[str]) -> Dict[str, List[str]]:
    refs = {key: [] for key in REFERENCE_KEYS}
    refs["artifact_run_ids"] = sorted(set(str(item) for item in artifact_run_ids))
    return refs


def _merge_refs(
    left: Mapping[str, Sequence[str]],
    right: Mapping[str, Sequence[str]],
) -> Dict[str, List[str]]:
    return {
        key: sorted(set(left.get(key, [])) | set(right.get(key, [])))
        for key in REFERENCE_KEYS
    }


def _normalize_refs(
    refs: Mapping[str, Sequence[str]],
) -> Dict[str, List[str]]:
    return {
        key: sorted(set(str(item) for item in refs.get(key, [])))
        for key in REFERENCE_KEYS
    }


def _deduplicate_and_sort(risks: Sequence[RiskItem]) -> List[RiskItem]:
    by_id = {item.risk_id: item for item in risks}
    category_order = {"upcoming_event": 0, "data_quality": 1, "market_stress": 2}
    return sorted(
        by_id.values(),
        key=lambda item: (
            category_order[item.category],
            item.rule_id,
            str(item.time_window),
            item.risk_id,
        ),
    )


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise RiskMonitorError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _iso_utc(value: datetime) -> str:
    return _as_utc(value).isoformat().replace("+00:00", "Z")
