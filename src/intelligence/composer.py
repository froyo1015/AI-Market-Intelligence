"""Assemble validated upstream objects without new financial interpretation."""

from __future__ import annotations

import copy
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

from src.models.intelligence_schema import (
    DailyIntelligenceArtifact,
    IntelligenceObject,
)
from src.risk.validator import validate_risk_monitor_artifact


SCHEMA_CONTRACT = "daily_intelligence_v1"
MAXIMUM_FUTURE_SKEW_MINUTES = 5.0
MAXIMUM_INPUT_AGE_HOURS = 24.0
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
CATALOG_KEYS = (
    "evidence_bundles",
    "source_records",
    "observation_records",
    "event_records",
    "evidence_records",
)


class IntelligenceCompositionError(ValueError):
    """Raised when Phase 6.4-A inputs are not one validated linked run."""


def build_daily_intelligence_artifact(
    evidence_bundle: Mapping[str, Any],
    market_signals: Mapping[str, Any],
    market_regime: Mapping[str, Any],
    risk_monitor: Mapping[str, Any],
    now: Optional[datetime] = None,
) -> DailyIntelligenceArtifact:
    generated = _as_utc(now or datetime.now(timezone.utc))
    validate_risk_monitor_artifact(
        risk_monitor,
        evidence_bundle,
        market_signals,
        market_regime,
    )
    _validate_linkage(
        evidence_bundle,
        market_signals,
        market_regime,
        risk_monitor,
        generated,
    )
    input_refs = {
        "evidence_bundle_run_id": str(evidence_bundle["run_id"]),
        "market_signals_run_id": str(market_signals["run_id"]),
        "market_regime_run_id": str(market_regime["run_id"]),
        "risk_monitor_run_id": str(risk_monitor["run_id"]),
    }

    signal_objects = [
        _signal_object(item, market_signals, input_refs)
        for item in market_signals["signals"]
    ]
    signal_objects.sort(
        key=lambda item: (item.payload["rule_id"], item.payload["signal_id"])
    )
    regime_object = _regime_object(market_regime, input_refs)
    risk_objects = [
        _risk_object(item, risk_monitor, input_refs)
        for item in risk_monitor["risks"]
    ]
    risk_objects.sort(key=_risk_sort_key)
    upcoming = [
        item for item in risk_objects if item.payload["category"] == "upcoming_event"
    ]
    quality = [
        item for item in risk_objects if item.payload["category"] == "data_quality"
    ]
    stress = [
        item for item in risk_objects if item.payload["category"] == "market_stress"
    ]
    all_objects = [regime_object] + signal_objects + risk_objects
    refs = _merge_object_refs(all_objects)
    catalog = _build_provenance_catalog(evidence_bundle, refs)
    data_window = _data_window(
        evidence_bundle,
        market_signals,
        market_regime,
        risk_monitor,
        all_objects,
        catalog,
        generated,
    )
    coverage = _coverage(
        evidence_bundle,
        market_signals,
        market_regime,
        risk_monitor,
        generated,
    )
    artifact_freshness = {
        item["artifact"]: item["artifact_freshness_status"] for item in coverage
    }

    current_regime = (
        market_regime.get("classification") is not None
        and artifact_freshness["evidence_bundle.json"] == "current"
        and artifact_freshness["market_signals.json"] == "current"
        and artifact_freshness["market_regime.json"] == "current"
    )
    current_signal = (
        any(
            item.payload.get("state") in {"observed", "not_observed"}
            and item.payload.get("data_quality", {}).get("status") == "available"
            for item in signal_objects
        )
        and artifact_freshness["evidence_bundle.json"] == "current"
        and artifact_freshness["market_signals.json"] == "current"
    )
    current_risk = bool(upcoming or stress) and all(
        item == "current" for item in artifact_freshness.values()
    )
    substantive = current_regime or current_signal or current_risk
    upstream_statuses = [item["data_status"] for item in coverage]
    upstream_freshness = [
        item["artifact_freshness_status"] for item in coverage
    ]
    if not substantive:
        status = "unavailable"
    elif all(item == "available" for item in upstream_statuses) and all(
        item == "current" for item in upstream_freshness
    ):
        status = "available"
    else:
        status = "partial"

    warnings: List[str] = []
    for item in coverage:
        if item["data_status"] == "partial":
            warnings.append(f"upstream_partial:{item['artifact']}")
        elif item["data_status"] == "unavailable":
            warnings.append(f"upstream_unavailable:{item['artifact']}")
        if item["artifact_freshness_status"] == "stale":
            warnings.append(f"upstream_stale:{item['artifact']}")
    if not substantive:
        warnings.append("no_current_substantive_intelligence")
    if not any(catalog.values()):
        warnings.append("provenance_catalog_empty")

    generated_at = _iso_utc(generated)
    digest = hashlib.sha256(
        (
            "|".join(input_refs.values())
            + f"|{generated_at}|{SCHEMA_CONTRACT}"
        ).encode("utf-8")
    ).hexdigest()[:16]
    return DailyIntelligenceArtifact(
        run_id=f"run_{generated:%Y%m%dT%H%M%SZ}_intelligence_{digest}",
        report_date=str(evidence_bundle["report_date"]),
        generated_at=generated_at,
        status=status,
        input_refs=input_refs,
        data_window=data_window,
        coverage=coverage,
        market_regime=regime_object,
        cross_asset_signals=signal_objects,
        upcoming_events=upcoming,
        data_quality_risks=quality,
        observed_market_stress=stress,
        provenance_catalog=catalog,
        warnings=warnings,
        limitations=[
            "structured_assembly_only",
            "no_new_interpretation",
            "no_market_outlook_or_trade_action",
        ],
    )


def _signal_object(
    signal: Mapping[str, Any],
    artifact: Mapping[str, Any],
    input_refs: Mapping[str, str],
) -> IntelligenceObject:
    refs = _normalize_refs(signal.get("evidence_refs", {}))
    refs["artifact_run_ids"] = sorted(
        {
            input_refs["evidence_bundle_run_id"],
            input_refs["market_signals_run_id"],
        }
    )
    refs["signal_ids"] = [str(signal["signal_id"])]
    observed_at = sorted(
        set(str(item["as_of"]) for item in signal.get("observed_values", []))
    )
    return IntelligenceObject(
        object_id=_object_id(
            "signal",
            str(artifact["run_id"]),
            str(signal["signal_id"]),
        ),
        object_type="cross_asset_signal",
        source_artifact="market_signals.json",
        source_run_id=str(artifact["run_id"]),
        source_generated_at=str(artifact["generated_at"]),
        validation_status="validated",
        data_status=str(signal["state"]),
        timestamps={
            "observed_at": observed_at,
            "scheduled_at": [],
            "detected_at": [],
        },
        evidence_refs=_normalize_refs(refs),
        payload=copy.deepcopy(dict(signal)),
    )


def _regime_object(
    regime: Mapping[str, Any],
    input_refs: Mapping[str, str],
) -> IntelligenceObject:
    refs = _normalize_refs(regime.get("evidence_refs", {}))
    refs["artifact_run_ids"] = sorted(
        {
            input_refs["evidence_bundle_run_id"],
            input_refs["market_signals_run_id"],
            input_refs["market_regime_run_id"],
        }
    )
    for dimension in regime["dimensions"]:
        refs["regime_dimension_ids"].append(str(dimension["dimension_id"]))
        refs["signal_ids"].append(str(dimension["signal_id"]))
        refs = _merge_refs(refs, dimension.get("evidence_refs", {}))
    observed_at = sorted(
        {
            str(value["as_of"])
            for dimension in regime["dimensions"]
            for value in dimension.get("observed_values", [])
        }
    )
    return IntelligenceObject(
        object_id=_object_id("regime", str(regime["run_id"]), "market_regime"),
        object_type="market_regime",
        source_artifact="market_regime.json",
        source_run_id=str(regime["run_id"]),
        source_generated_at=str(regime["generated_at"]),
        validation_status="validated",
        data_status=str(regime["status"]),
        timestamps={
            "observed_at": observed_at,
            "scheduled_at": [],
            "detected_at": [],
        },
        evidence_refs=_normalize_refs(refs),
        payload=copy.deepcopy(dict(regime)),
    )


def _risk_object(
    risk: Mapping[str, Any],
    artifact: Mapping[str, Any],
    input_refs: Mapping[str, str],
) -> IntelligenceObject:
    refs = _normalize_refs(risk.get("evidence_refs", {}))
    refs["artifact_run_ids"] = sorted(
        set(refs["artifact_run_ids"]) | set(input_refs.values())
    )
    refs["risk_ids"] = [str(risk["risk_id"])]
    time_window = risk.get("time_window", {})
    return IntelligenceObject(
        object_id=_object_id("risk", str(artifact["run_id"]), str(risk["risk_id"])),
        object_type={
            "upcoming_event": "upcoming_event_risk",
            "data_quality": "data_quality_risk",
            "market_stress": "market_stress_risk",
        }[str(risk["category"])],
        source_artifact="risk_monitor.json",
        source_run_id=str(artifact["run_id"]),
        source_generated_at=str(artifact["generated_at"]),
        validation_status="validated",
        data_status=str(risk["status"]),
        timestamps={
            "observed_at": _timestamp_values(time_window.get("observed_at")),
            "scheduled_at": _timestamp_values(time_window.get("scheduled_at")),
            "detected_at": _timestamp_values(time_window.get("detected_at")),
        },
        evidence_refs=_normalize_refs(refs),
        payload=copy.deepcopy(dict(risk)),
    )


def _coverage(
    evidence_bundle: Mapping[str, Any],
    market_signals: Mapping[str, Any],
    market_regime: Mapping[str, Any],
    risk_monitor: Mapping[str, Any],
    generated: datetime,
) -> List[Dict[str, Any]]:
    stale_evidence = any(
        bundle["freshness"]["stale_record_ids"]
        for bundle in evidence_bundle["bundles"]
    )
    coverage = [
        {
            "artifact": "evidence_bundle.json",
            "artifact_type": "evidence_bundle",
            "run_id": str(evidence_bundle["run_id"]),
            "generated_at": str(evidence_bundle["generated_at"]),
            "validation_status": "validated",
            "data_status": str(evidence_bundle["status"]),
            "freshness_status": "stale" if stale_evidence else "current",
            "object_count": int(evidence_bundle["bundle_count"]),
            "warning_count": len(evidence_bundle["warnings"]),
        },
        {
            "artifact": "market_signals.json",
            "artifact_type": "market_signals",
            "run_id": str(market_signals["run_id"]),
            "generated_at": str(market_signals["generated_at"]),
            "validation_status": "validated",
            "data_status": str(market_signals["status"]),
            "freshness_status": (
                "stale"
                if any(item["state"] == "stale_data" for item in market_signals["signals"])
                else "current"
            ),
            "object_count": int(market_signals["signal_count"]),
            "warning_count": len(market_signals["warnings"]),
        },
        {
            "artifact": "market_regime.json",
            "artifact_type": "market_regime",
            "run_id": str(market_regime["run_id"]),
            "generated_at": str(market_regime["generated_at"]),
            "validation_status": "validated",
            "data_status": str(market_regime["status"]),
            "freshness_status": str(market_regime["input_freshness"]["status"]),
            "object_count": 1,
            "warning_count": len(market_regime["warnings"]),
        },
        {
            "artifact": "risk_monitor.json",
            "artifact_type": "risk_monitor",
            "run_id": str(risk_monitor["run_id"]),
            "generated_at": str(risk_monitor["generated_at"]),
            "validation_status": "validated",
            "data_status": str(risk_monitor["status"]),
            "freshness_status": str(risk_monitor["input_freshness"]["status"]),
            "object_count": int(risk_monitor["risk_count"]),
            "warning_count": len(risk_monitor["warnings"]),
        },
    ]
    for item in coverage:
        age_hours = max(
            0.0,
            (generated - _parse_timestamp(item["generated_at"])).total_seconds()
            / 3600.0,
        )
        item["age_hours"] = round(age_hours, 6)
        item["maximum_age_hours"] = MAXIMUM_INPUT_AGE_HOURS
        item["artifact_freshness_status"] = (
            "stale" if age_hours > MAXIMUM_INPUT_AGE_HOURS else "current"
        )
    return coverage


def _build_provenance_catalog(
    evidence_bundle: Mapping[str, Any],
    refs: Mapping[str, Sequence[str]],
) -> Dict[str, List[Dict[str, Any]]]:
    bundle_index: Dict[str, Dict[str, Any]] = {}
    indexes: Dict[str, Dict[str, Dict[str, Any]]] = {
        "source_records": {},
        "observation_records": {},
        "event_records": {},
        "evidence_records": {},
    }
    id_fields = {
        "source_records": "source_id",
        "observation_records": "observation_id",
        "event_records": "event_id",
        "evidence_records": "evidence_id",
    }
    bundle_lists = {
        "source_records": "source_records",
        "observation_records": "observations",
        "event_records": "events",
        "evidence_records": "evidence_records",
    }
    for bundle in evidence_bundle["bundles"]:
        bundle_id = str(bundle["id"])
        bundle_index[bundle_id] = {
            key: copy.deepcopy(bundle[key])
            for key in (
                "id",
                "type",
                "related_assets",
                "timestamps",
                "verification_level",
                "data_quality",
                "freshness",
                "provenance",
            )
        }
        for catalog_key, bundle_key in bundle_lists.items():
            id_field = id_fields[catalog_key]
            for record in bundle[bundle_key]:
                record_id = str(record[id_field])
                previous = indexes[catalog_key].get(record_id)
                if previous is not None and previous != record:
                    raise IntelligenceCompositionError(
                        f"conflicting provenance record: {record_id}"
                    )
                indexes[catalog_key][record_id] = copy.deepcopy(dict(record))

    requested = {
        "evidence_bundles": refs["evidence_bundle_ids"],
        "source_records": refs["source_ids"],
        "observation_records": refs["observation_ids"],
        "event_records": refs["event_ids"],
        "evidence_records": refs["evidence_ids"],
    }
    result: Dict[str, List[Dict[str, Any]]] = {}
    for key in CATALOG_KEYS:
        index = bundle_index if key == "evidence_bundles" else indexes[key]
        missing = sorted(set(requested[key]) - set(index))
        if missing:
            raise IntelligenceCompositionError(
                f"unresolved {key} references: {', '.join(missing)}"
            )
        result[key] = [copy.deepcopy(index[item]) for item in sorted(requested[key])]
    return result


def _data_window(
    evidence_bundle: Mapping[str, Any],
    market_signals: Mapping[str, Any],
    market_regime: Mapping[str, Any],
    risk_monitor: Mapping[str, Any],
    objects: Sequence[IntelligenceObject],
    catalog: Mapping[str, Sequence[Mapping[str, Any]]],
    generated: datetime,
) -> Dict[str, Any]:
    input_generated = sorted(
        {
            _utc_string(str(item["generated_at"]))
            for item in (
                evidence_bundle,
                market_signals,
                market_regime,
                risk_monitor,
            )
        }
    )
    observed = {
        _utc_string(str(item["as_of"]))
        for item in catalog["observation_records"]
    }
    scheduled = {
        _utc_string(str(item["scheduled_at"]))
        for item in catalog["event_records"]
        if item.get("scheduled_at") is not None
    }
    occurred = {
        _utc_string(str(item["occurred_at"]))
        for item in catalog["event_records"]
        if item.get("occurred_at") is not None
    }
    published = {
        _utc_string(str(item["published_at"]))
        for item in catalog["source_records"]
        if item.get("published_at") is not None
    }
    retrieved = {
        _utc_string(str(item["retrieved_at"]))
        for item in catalog["source_records"]
        if item.get("retrieved_at") is not None
    }
    detected = {
        _utc_string(item)
        for obj in objects
        for item in obj.timestamps["detected_at"]
    }
    return {
        "report_date": str(evidence_bundle["report_date"]),
        "composed_at": _iso_utc(generated),
        "input_generated_at": _window(input_generated),
        "observed_at": _window(observed),
        "scheduled_at": _window(scheduled),
        "occurred_at": _window(occurred),
        "published_at": _window(published),
        "retrieved_at": _window(retrieved),
        "detected_at": _window(detected),
    }


def _validate_linkage(
    evidence_bundle: Mapping[str, Any],
    market_signals: Mapping[str, Any],
    market_regime: Mapping[str, Any],
    risk_monitor: Mapping[str, Any],
    generated: datetime,
) -> None:
    expected_risk_refs = {
        "evidence_bundle_run_id": evidence_bundle.get("run_id"),
        "market_signals_run_id": market_signals.get("run_id"),
        "market_regime_run_id": market_regime.get("run_id"),
    }
    if risk_monitor.get("input_refs") != expected_risk_refs:
        raise IntelligenceCompositionError("risk monitor input linkage mismatch")
    report_dates = {
        item.get("report_date")
        for item in (
            evidence_bundle,
            market_signals,
            market_regime,
            risk_monitor,
        )
    }
    if len(report_dates) != 1:
        raise IntelligenceCompositionError("input report dates do not match")
    times = [
        _parse_timestamp(str(item["generated_at"]))
        for item in (
            evidence_bundle,
            market_signals,
            market_regime,
            risk_monitor,
        )
    ]
    if times != sorted(times):
        raise IntelligenceCompositionError("input artifacts are out of order")
    future_limit = MAXIMUM_FUTURE_SKEW_MINUTES * 60
    if any((item - generated).total_seconds() > future_limit for item in times):
        raise IntelligenceCompositionError("one or more inputs are future-dated")


def _merge_object_refs(
    objects: Sequence[IntelligenceObject],
) -> Dict[str, List[str]]:
    refs = _empty_refs()
    for item in objects:
        refs = _merge_refs(refs, item.evidence_refs)
    return refs


def _merge_refs(
    left: Mapping[str, Sequence[str]],
    right: Mapping[str, Sequence[str]],
) -> Dict[str, List[str]]:
    return {
        key: sorted(set(left.get(key, [])) | set(right.get(key, [])))
        for key in REFERENCE_KEYS
    }


def _normalize_refs(refs: Mapping[str, Sequence[str]]) -> Dict[str, List[str]]:
    return {
        key: sorted(set(str(item) for item in refs.get(key, [])))
        for key in REFERENCE_KEYS
    }


def _empty_refs() -> Dict[str, List[str]]:
    return {key: [] for key in REFERENCE_KEYS}


def _object_id(object_type: str, source_run_id: str, source_id: str) -> str:
    digest = hashlib.sha256(
        f"{object_type}|{source_run_id}|{source_id}".encode("utf-8")
    ).hexdigest()[:16]
    return f"int_{object_type}_{digest}"


def _risk_sort_key(item: IntelligenceObject) -> Tuple[str, str, str, str]:
    payload = item.payload
    time_value = "|".join(
        item.timestamps["scheduled_at"]
        + item.timestamps["observed_at"]
        + item.timestamps["detected_at"]
    )
    return (
        str(payload["category"]),
        str(payload["rule_id"]),
        time_value,
        str(payload["risk_id"]),
    )


def _timestamp_values(value: Any) -> List[str]:
    if value is None:
        return []
    values = value if isinstance(value, list) else [value]
    return sorted(set(_utc_string(str(item)) for item in values))


def _window(values: Iterable[str]) -> Dict[str, Any]:
    normalized = sorted(set(_utc_string(str(item)) for item in values))
    return {
        "values": normalized,
        "earliest": normalized[0] if normalized else None,
        "latest": normalized[-1] if normalized else None,
    }


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise IntelligenceCompositionError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def _utc_string(value: str) -> str:
    return _iso_utc(_parse_timestamp(value))


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _iso_utc(value: datetime) -> str:
    return _as_utc(value).isoformat().replace("+00:00", "Z")
