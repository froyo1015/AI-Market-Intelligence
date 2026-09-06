"""Shared freshness enrichment and validation without intelligence semantics."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Optional, Sequence

from src.models.freshness_schema import (
    DEFAULT_STALE_AFTER_SECONDS,
    FRESHNESS_CONTRACT_VERSION,
    STALE_AFTER_SECONDS,
    FreshnessMetadata,
    FreshnessStatus,
)


SOURCE_TIMESTAMP_KEYS = {
    "as_of",
    "observed_at",
    "occurred_at",
    "published_at",
    "source_timestamp",
    "timestamp",
}
SOURCE_BOUNDARY_TYPES = {
    "market_snapshot",
    "macro_snapshot",
    "economic_calendar",
    "news_items",
}
UNAVAILABLE_DATA_STATUSES = {"failed", "invalid", "unavailable"}
MAXIMUM_FUTURE_SKEW_SECONDS = 300.0
FRESHNESS_FIELDS = {
    "freshness_contract_version",
    "source_timestamp",
    "retrieved_at",
    "age_seconds",
    "freshness_status",
    "freshness_basis",
    "stale_after_seconds",
}


class FreshnessValidationError(ValueError):
    """Raised when shared freshness metadata is inconsistent."""


def enrich_artifact_freshness(
    artifact: Mapping[str, Any],
    supporting_artifacts: Sequence[Mapping[str, Any]] = (),
    stale_after_seconds: Optional[int] = None,
) -> dict[str, Any]:
    """Return an artifact copy with the canonical top-level freshness fields."""
    payload = strip_freshness_metadata(artifact)
    generated = _required_timestamp(payload.get("generated_at"), "generated_at")
    artifact_type = str(payload.get("artifact_type") or "market_snapshot")
    threshold = (
        stale_after_seconds
        if stale_after_seconds is not None
        else STALE_AFTER_SECONDS.get(artifact_type, DEFAULT_STALE_AFTER_SECONDS)
    )
    if threshold <= 0:
        raise FreshnessValidationError("stale_after_seconds must be positive")

    candidates: list[Mapping[str, Any]] = [payload, *supporting_artifacts]
    source_times = _collect_source_timestamps(candidates)
    retrieval_times = _collect_named_timestamps(candidates, "retrieved_at")
    source_timestamp = min(source_times) if source_times else None
    retrieved_at = max(retrieval_times) if retrieval_times else None
    unavailable = _is_unavailable(payload)
    if (
        retrieved_at is None
        and artifact_type in SOURCE_BOUNDARY_TYPES
        and not unavailable
    ):
        retrieved_at = generated

    if unavailable:
        metadata = FreshnessMetadata(
            source_timestamp=_iso(source_timestamp) if source_timestamp else None,
            retrieved_at=_iso(retrieved_at) if retrieved_at else None,
            generated_at=_iso(generated),
            age_seconds=None,
            freshness_status=FreshnessStatus.UNAVAILABLE,
            freshness_basis="unavailable",
            stale_after_seconds=threshold,
        )
    else:
        basis_name = "source_timestamp" if source_timestamp else "retrieved_at"
        basis = source_timestamp or retrieved_at
        if basis is None or (basis - generated).total_seconds() > MAXIMUM_FUTURE_SKEW_SECONDS:
            metadata = FreshnessMetadata(
                source_timestamp=_iso(source_timestamp) if source_timestamp else None,
                retrieved_at=_iso(retrieved_at) if retrieved_at else None,
                generated_at=_iso(generated),
                age_seconds=None,
                freshness_status=FreshnessStatus.UNKNOWN,
                freshness_basis="unknown",
                stale_after_seconds=threshold,
            )
        else:
            age = round(max(0.0, (generated - basis).total_seconds()), 3)
            status = (
                FreshnessStatus.STALE
                if age > threshold
                else FreshnessStatus.CURRENT
            )
            metadata = FreshnessMetadata(
                source_timestamp=_iso(source_timestamp) if source_timestamp else None,
                retrieved_at=_iso(retrieved_at) if retrieved_at else None,
                generated_at=_iso(generated),
                age_seconds=age,
                freshness_status=status,
                freshness_basis=basis_name,
                stale_after_seconds=threshold,
            )

    payload.update(metadata.to_dict())
    validate_freshness_contract(payload)
    return payload


def validate_freshness_contract(payload: Mapping[str, Any]) -> None:
    missing = sorted(FRESHNESS_FIELDS - set(payload))
    if missing:
        raise FreshnessValidationError(f"freshness fields missing: {missing}")
    if payload.get("freshness_contract_version") != FRESHNESS_CONTRACT_VERSION:
        raise FreshnessValidationError("unsupported freshness contract version")

    status_value = payload.get("freshness_status")
    try:
        status = FreshnessStatus(str(status_value))
    except ValueError as exc:
        raise FreshnessValidationError("invalid freshness_status") from exc
    generated = _required_timestamp(payload.get("generated_at"), "generated_at")
    source = _optional_timestamp(payload.get("source_timestamp"), "source_timestamp")
    retrieved = _optional_timestamp(payload.get("retrieved_at"), "retrieved_at")
    age = payload.get("age_seconds")
    threshold = payload.get("stale_after_seconds")
    basis_name = payload.get("freshness_basis")

    if status in {FreshnessStatus.UNAVAILABLE, FreshnessStatus.UNKNOWN}:
        if age is not None:
            raise FreshnessValidationError(f"{status.value} freshness cannot declare age")
        expected_basis = "unavailable" if status is FreshnessStatus.UNAVAILABLE else "unknown"
        if basis_name != expected_basis:
            raise FreshnessValidationError(f"{status.value} freshness basis is invalid")
        return

    if not isinstance(threshold, int) or threshold <= 0:
        raise FreshnessValidationError("stale_after_seconds must be a positive integer")
    if not isinstance(age, (int, float)) or isinstance(age, bool) or not math.isfinite(age):
        raise FreshnessValidationError("age_seconds must be a finite number")
    if age < 0:
        raise FreshnessValidationError("age_seconds cannot be negative")
    if basis_name not in {"source_timestamp", "retrieved_at"}:
        raise FreshnessValidationError("freshness_basis is invalid")
    basis = source if basis_name == "source_timestamp" else retrieved
    if basis is None:
        raise FreshnessValidationError("freshness basis timestamp is missing")
    if (basis - generated).total_seconds() > MAXIMUM_FUTURE_SKEW_SECONDS:
        raise FreshnessValidationError("freshness basis is in the future")
    expected_age = round(max(0.0, (generated - basis).total_seconds()), 3)
    if abs(float(age) - expected_age) > 0.001:
        raise FreshnessValidationError("age_seconds does not match freshness timestamps")
    if status is FreshnessStatus.CURRENT and age > threshold:
        raise FreshnessValidationError("current freshness exceeds stale threshold")
    if status is FreshnessStatus.STALE and age <= threshold:
        raise FreshnessValidationError("stale freshness does not exceed threshold")


def aggregate_freshness_status(statuses: Iterable[str]) -> str:
    values = {str(status) for status in statuses}
    unsupported = values - {status.value for status in FreshnessStatus}
    if unsupported:
        raise FreshnessValidationError(
            f"cannot aggregate unsupported freshness status: {sorted(unsupported)}"
        )
    if FreshnessStatus.UNAVAILABLE.value in values:
        return FreshnessStatus.UNAVAILABLE.value
    if FreshnessStatus.UNKNOWN.value in values:
        return FreshnessStatus.UNKNOWN.value
    if FreshnessStatus.STALE.value in values:
        return FreshnessStatus.STALE.value
    if FreshnessStatus.CURRENT.value in values:
        return FreshnessStatus.CURRENT.value
    return FreshnessStatus.UNKNOWN.value


def aggregate_freshness_fields(
    records: Sequence[Mapping[str, Any]],
    generated_at: str,
) -> dict[str, Any]:
    generated = _required_timestamp(generated_at, "generated_at")
    sources = [
        value
        for record in records
        for value in [_optional_timestamp(record.get("source_timestamp"), "source_timestamp")]
        if value is not None
    ]
    retrievals = [
        value
        for record in records
        for value in [_optional_timestamp(record.get("retrieved_at"), "retrieved_at")]
        if value is not None
    ]
    source_timestamp = min(sources) if sources else None
    retrieved_at = max(retrievals) if retrievals else None
    basis = source_timestamp or retrieved_at
    age_seconds = (
        round(max(0.0, (generated - basis).total_seconds()), 3)
        if basis is not None
        else None
    )
    aggregate_status = aggregate_freshness_status(
        str(record.get("freshness_status", "unknown")) for record in records
    )
    if aggregate_status in {"unavailable", "unknown"}:
        age_seconds = None
    return {
        "source_timestamp": _iso(source_timestamp) if source_timestamp else None,
        "retrieved_at": _iso(retrieved_at) if retrieved_at else None,
        "generated_at": _iso(generated),
        "age_seconds": age_seconds,
        "freshness_status": aggregate_status,
    }


def validate_freshness_summary(payload: Mapping[str, Any]) -> None:
    """Validate the five-field freshness summary used by manifests/modules."""
    required = {
        "source_timestamp",
        "retrieved_at",
        "generated_at",
        "age_seconds",
        "freshness_status",
    }
    missing = sorted(required - set(payload))
    if missing:
        raise FreshnessValidationError(f"freshness summary fields missing: {missing}")
    status = str(payload.get("freshness_status"))
    if status not in {item.value for item in FreshnessStatus}:
        raise FreshnessValidationError("invalid freshness_status")
    generated = _required_timestamp(payload.get("generated_at"), "generated_at")
    source = _optional_timestamp(payload.get("source_timestamp"), "source_timestamp")
    retrieved = _optional_timestamp(payload.get("retrieved_at"), "retrieved_at")
    age = payload.get("age_seconds")
    if status in {"unavailable", "unknown"}:
        if age is not None:
            raise FreshnessValidationError(f"{status} freshness cannot declare age")
        return
    if not isinstance(age, (int, float)) or isinstance(age, bool) or not math.isfinite(age):
        raise FreshnessValidationError("age_seconds must be a finite number")
    basis = source or retrieved
    if basis is None:
        raise FreshnessValidationError("freshness summary has no basis timestamp")
    expected_age = round(max(0.0, (generated - basis).total_seconds()), 3)
    if abs(float(age) - expected_age) > 0.001:
        raise FreshnessValidationError("age_seconds does not match freshness summary")


def strip_freshness_metadata(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return the domain artifact without top-level freshness envelope fields."""
    return {key: value for key, value in payload.items() if key not in FRESHNESS_FIELDS}


def _is_unavailable(payload: Mapping[str, Any]) -> bool:
    if payload.get("status") in UNAVAILABLE_DATA_STATUSES:
        return True
    records = payload.get("records")
    if isinstance(records, list) and records:
        statuses = {
            item.get("status") for item in records if isinstance(item, Mapping)
        }
        return bool(statuses) and statuses <= UNAVAILABLE_DATA_STATUSES
    return False


def _collect_source_timestamps(
    artifacts: Sequence[Mapping[str, Any]],
) -> list[datetime]:
    values: list[datetime] = []
    for artifact in artifacts:
        _walk_source_timestamps(artifact, values)
    return values


def _walk_source_timestamps(value: Any, output: list[datetime]) -> None:
    if isinstance(value, Mapping):
        record_unavailable = value.get("status") in UNAVAILABLE_DATA_STATUSES
        for key, child in value.items():
            if key in FRESHNESS_FIELDS - {"source_timestamp"}:
                continue
            if key in SOURCE_TIMESTAMP_KEYS and not record_unavailable:
                output.extend(_timestamp_values(child))
            else:
                _walk_source_timestamps(child, output)
    elif isinstance(value, list):
        for child in value:
            _walk_source_timestamps(child, output)


def _collect_named_timestamps(
    artifacts: Sequence[Mapping[str, Any]],
    field: str,
) -> list[datetime]:
    values: list[datetime] = []
    for artifact in artifacts:
        _walk_named_timestamps(artifact, field, values)
    return values


def _walk_named_timestamps(value: Any, field: str, output: list[datetime]) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key == field:
                output.extend(_timestamp_values(child))
            else:
                _walk_named_timestamps(child, field, output)
    elif isinstance(value, list):
        for child in value:
            _walk_named_timestamps(child, field, output)


def _timestamp_values(value: Any) -> list[datetime]:
    if isinstance(value, str):
        parsed = _parse_timestamp(value)
        return [parsed] if parsed else []
    if isinstance(value, Mapping):
        values: list[datetime] = []
        for child in value.values():
            values.extend(_timestamp_values(child))
        return values
    if isinstance(value, list):
        values = []
        for child in value:
            values.extend(_timestamp_values(child))
        return values
    return []


def _required_timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise FreshnessValidationError(f"{field} must be an ISO UTC timestamp")
    parsed = _parse_timestamp(value)
    if parsed is None or not value.endswith("Z"):
        raise FreshnessValidationError(f"{field} must be an ISO UTC timestamp")
    return parsed


def _optional_timestamp(value: Any, field: str) -> Optional[datetime]:
    if value is None:
        return None
    return _required_timestamp(value, field)


def _parse_timestamp(value: str) -> Optional[datetime]:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
