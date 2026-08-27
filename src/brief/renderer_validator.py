"""Standalone contract validation for the Phase 6.4-B1 renderer."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Mapping, Sequence, Set


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
SECTION_TYPES = {
    "cross_asset_signals": "cross_asset_signal",
    "upcoming_events": "upcoming_event_risk",
    "data_quality_risks": "data_quality_risk",
    "observed_market_stress": "market_stress_risk",
}
CATALOG_IDS = {
    "evidence_bundle_ids": ("evidence_bundles", "id"),
    "source_ids": ("source_records", "source_id"),
    "observation_ids": ("observation_records", "observation_id"),
    "event_ids": ("event_records", "event_id"),
    "evidence_ids": ("evidence_records", "evidence_id"),
}


class BriefRendererValidationError(ValueError):
    """Raised when an input or rendered brief violates the B1 contract."""


def validate_renderer_input(artifact: Mapping[str, Any]) -> None:
    if artifact.get("artifact_type") != "daily_intelligence":
        raise BriefRendererValidationError(
            "renderer requires a daily_intelligence artifact"
        )
    if artifact.get("schema_contract") != "daily_intelligence_v1":
        raise BriefRendererValidationError(
            "renderer requires daily_intelligence_v1"
        )
    if artifact.get("status") not in {"available", "partial", "unavailable"}:
        raise BriefRendererValidationError("invalid daily intelligence status")
    for key in ("run_id", "report_date", "generated_at"):
        _require_string(artifact, key, "artifact")
    _parse_timestamp(str(artifact["generated_at"]), "generated_at")
    _require_string_list(artifact.get("warnings"), "warnings")
    _require_string_list(artifact.get("limitations"), "limitations")

    input_refs = _require_mapping(artifact.get("input_refs"), "input_refs")
    expected_input_keys = {
        "evidence_bundle_run_id",
        "market_signals_run_id",
        "market_regime_run_id",
        "risk_monitor_run_id",
    }
    if set(input_refs) != expected_input_keys:
        raise BriefRendererValidationError("input_refs keys do not match contract")
    if not all(isinstance(value, str) and value for value in input_refs.values()):
        raise BriefRendererValidationError("input_refs values must be IDs")

    coverage = _require_list(artifact.get("coverage"), "coverage")
    if len(coverage) != 4:
        raise BriefRendererValidationError("coverage must contain four artifacts")
    for index, item in enumerate(coverage):
        row = _require_mapping(item, f"coverage[{index}]")
        if row.get("validation_status") != "validated":
            raise BriefRendererValidationError("coverage is not validated")
        _require_string(row, "run_id", f"coverage[{index}]")
        _parse_timestamp(
            _require_string(row, "generated_at", f"coverage[{index}]"),
            f"coverage[{index}].generated_at",
        )
        for key in (
            "artifact",
            "artifact_type",
            "data_status",
            "freshness_status",
            "artifact_freshness_status",
        ):
            _require_string(row, key, f"coverage[{index}]")
        for key in (
            "object_count",
            "warning_count",
            "age_hours",
            "maximum_age_hours",
        ):
            if not isinstance(row.get(key), (int, float)) or isinstance(
                row.get(key), bool
            ):
                raise BriefRendererValidationError(
                    f"coverage[{index}].{key} must be numeric"
                )

    _validate_data_window(artifact.get("data_window"))

    regime = _require_mapping(artifact.get("market_regime"), "market_regime")
    _validate_object(regime, "market_regime", "market_regime")
    sections: Dict[str, Sequence[Mapping[str, Any]]] = {}
    all_objects = [regime]
    for section, object_type in SECTION_TYPES.items():
        items = _require_list(artifact.get(section), section)
        typed_items = []
        for index, item in enumerate(items):
            obj = _require_mapping(item, f"{section}[{index}]")
            _validate_object(obj, object_type, f"{section}[{index}]")
            typed_items.append(obj)
        sections[section] = typed_items
        all_objects.extend(typed_items)

    object_ids = [str(item["object_id"]) for item in all_objects]
    if len(object_ids) != len(set(object_ids)):
        raise BriefRendererValidationError("duplicate intelligence object ID")
    _validate_counts(artifact, sections)
    _validate_provenance(artifact, all_objects, sections)
    _validate_payload_linkage(artifact, sections)


def validate_rendered_brief(
    markdown: str,
    artifact: Mapping[str, Any],
) -> None:
    validate_renderer_input(artifact)
    from src.brief.intelligence_renderer import render_daily_market_brief

    expected = render_daily_market_brief(artifact).markdown
    if markdown != expected:
        raise BriefRendererValidationError(
            "rendered brief does not match deterministic rendering"
        )


def _validate_object(
    obj: Mapping[str, Any],
    expected_type: str,
    context: str,
) -> None:
    if obj.get("object_type") != expected_type:
        raise BriefRendererValidationError(f"{context} has wrong object type")
    if obj.get("validation_status") != "validated":
        raise BriefRendererValidationError(f"{context} is not validated")
    for key in (
        "object_id",
        "source_artifact",
        "source_run_id",
        "source_generated_at",
        "data_status",
    ):
        _require_string(obj, key, context)
    _parse_timestamp(str(obj["source_generated_at"]), f"{context}.source_generated_at")
    timestamps = _require_mapping(obj.get("timestamps"), f"{context}.timestamps")
    if set(timestamps) != {"observed_at", "scheduled_at", "detected_at"}:
        raise BriefRendererValidationError(f"{context} timestamps do not match")
    for key, values in timestamps.items():
        _validate_sorted_ids(values, f"{context}.timestamps.{key}")
        for value in values:
            _parse_timestamp(value, f"{context}.timestamps.{key}")
    refs = _require_mapping(obj.get("evidence_refs"), f"{context}.evidence_refs")
    if set(refs) != set(REFERENCE_KEYS):
        raise BriefRendererValidationError(f"{context} references do not match")
    for key in REFERENCE_KEYS:
        _validate_sorted_ids(refs[key], f"{context}.evidence_refs.{key}")
    _require_mapping(obj.get("payload"), f"{context}.payload")


def _validate_counts(
    artifact: Mapping[str, Any],
    sections: Mapping[str, Sequence[Mapping[str, Any]]],
) -> None:
    counts = _require_mapping(artifact.get("object_counts"), "object_counts")
    expected = {
        "market_regime": 1,
        **{key: len(value) for key, value in sections.items()},
    }
    expected["total"] = sum(expected.values())
    if counts != expected:
        raise BriefRendererValidationError("object_counts do not match sections")


def _validate_provenance(
    artifact: Mapping[str, Any],
    objects: Sequence[Mapping[str, Any]],
    sections: Mapping[str, Sequence[Mapping[str, Any]]],
) -> None:
    catalog = _require_mapping(
        artifact.get("provenance_catalog"),
        "provenance_catalog",
    )
    resolved: Dict[str, Set[str]] = {}
    for ref_key, (catalog_key, id_key) in CATALOG_IDS.items():
        records = _require_list(catalog.get(catalog_key), catalog_key)
        record_ids = []
        for index, item in enumerate(records):
            record = _require_mapping(item, f"{catalog_key}[{index}]")
            record_ids.append(_require_string(record, id_key, catalog_key))
        if record_ids != sorted(set(record_ids)):
            raise BriefRendererValidationError(f"{catalog_key} is not ordered")
        resolved[ref_key] = set(record_ids)

    signal_ids = {
        _require_string(item["payload"], "signal_id", "signal payload")
        for item in sections["cross_asset_signals"]
    }
    regime_payload = _require_mapping(
        artifact["market_regime"].get("payload"),
        "market_regime.payload",
    )
    dimensions = _require_list(regime_payload.get("dimensions"), "dimensions")
    dimension_ids = {
        _require_string(
            _require_mapping(item, "dimension"),
            "dimension_id",
            "dimension",
        )
        for item in dimensions
    }
    risk_sections = (
        sections["upcoming_events"]
        + sections["data_quality_risks"]
        + sections["observed_market_stress"]
    )
    risk_ids = {
        _require_string(item["payload"], "risk_id", "risk payload")
        for item in risk_sections
    }
    input_refs = _require_mapping(artifact["input_refs"], "input_refs")
    artifact_run_ids = set(str(value) for value in input_refs.values())
    artifact_run_ids.update(str(item["run_id"]) for item in artifact["coverage"])
    artifact_run_ids.update(str(item["source_run_id"]) for item in objects)
    resolved.update(
        {
            "artifact_run_ids": artifact_run_ids,
            "signal_ids": signal_ids,
            "regime_dimension_ids": dimension_ids,
            "risk_ids": risk_ids,
        }
    )
    for obj in objects:
        refs = obj["evidence_refs"]
        for key, known in resolved.items():
            missing = set(refs[key]) - known
            if missing:
                raise BriefRendererValidationError(
                    f"unresolved {key}: {', '.join(sorted(missing))}"
                )


def _validate_payload_linkage(
    artifact: Mapping[str, Any],
    sections: Mapping[str, Sequence[Mapping[str, Any]]],
) -> None:
    regime = artifact["market_regime"]
    regime_payload = regime["payload"]
    if regime.get("data_status") != regime_payload.get("status"):
        raise BriefRendererValidationError("Regime data status was changed")
    if regime.get("source_run_id") != regime_payload.get("run_id"):
        raise BriefRendererValidationError("Regime source run does not match payload")
    for item in sections["cross_asset_signals"]:
        payload = item["payload"]
        signal_id = payload.get("signal_id")
        if item.get("data_status") != payload.get("state"):
            raise BriefRendererValidationError("Signal data status was changed")
        if signal_id not in item["evidence_refs"]["signal_ids"]:
            raise BriefRendererValidationError("Signal self-reference is missing")
    for section in (
        "upcoming_events",
        "data_quality_risks",
        "observed_market_stress",
    ):
        for item in sections[section]:
            payload = item["payload"]
            risk_id = payload.get("risk_id")
            if item.get("data_status") != payload.get("status"):
                raise BriefRendererValidationError("Risk data status was changed")
            if risk_id not in item["evidence_refs"]["risk_ids"]:
                raise BriefRendererValidationError("Risk self-reference is missing")


def _validate_data_window(value: Any) -> None:
    data_window = _require_mapping(value, "data_window")
    _parse_timestamp(
        _require_string(data_window, "composed_at", "data_window"),
        "data_window.composed_at",
    )
    _require_string(data_window, "report_date", "data_window")
    for key in (
        "input_generated_at",
        "observed_at",
        "scheduled_at",
        "occurred_at",
        "published_at",
        "retrieved_at",
        "detected_at",
    ):
        window = _require_mapping(data_window.get(key), f"data_window.{key}")
        values = _require_string_list(window.get("values"), f"{key}.values")
        if values != sorted(set(values)):
            raise BriefRendererValidationError(f"data_window.{key} is not ordered")
        for timestamp in values:
            _parse_timestamp(timestamp, f"data_window.{key}")
        expected_earliest = values[0] if values else None
        expected_latest = values[-1] if values else None
        if window.get("earliest") != expected_earliest:
            raise BriefRendererValidationError(f"data_window.{key}.earliest differs")
        if window.get("latest") != expected_latest:
            raise BriefRendererValidationError(f"data_window.{key}.latest differs")


def _parse_timestamp(value: str, context: str) -> None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise BriefRendererValidationError(f"{context} is invalid") from exc
    if parsed.tzinfo is None:
        raise BriefRendererValidationError(f"{context} needs timezone")


def _validate_sorted_ids(value: Any, context: str) -> None:
    values = _require_string_list(value, context)
    if values != sorted(set(values)):
        raise BriefRendererValidationError(f"{context} is not sorted and unique")


def _require_mapping(value: Any, context: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise BriefRendererValidationError(f"{context} must be an object")
    return value


def _require_list(value: Any, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise BriefRendererValidationError(f"{context} must be an array")
    return value


def _require_string(
    value: Mapping[str, Any],
    key: str,
    context: str,
) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item:
        raise BriefRendererValidationError(f"{context}.{key} must be a string")
    return item


def _require_string_list(value: Any, context: str) -> list[str]:
    values = _require_list(value, context)
    if not all(isinstance(item, str) for item in values):
        raise BriefRendererValidationError(f"{context} must contain strings")
    return values
