"""Validation for the resilient official economic-calendar boundary."""

from __future__ import annotations

import math
import re
from datetime import datetime
from typing import Any, Dict, Mapping, Set
from urllib.parse import urlsplit

from src.data.calendar_adapter import BEA_PUBLISHER, BLS_PUBLISHER


APPROVED_SOURCES = {
    "bls_release_calendar": {
        "priority": 1,
        "format": "ics",
        "publisher": BLS_PUBLISHER,
        "hosts": {"bls.gov", "www.bls.gov"},
    },
    "bea_release_schedule": {
        "priority": 2,
        "format": "bea_html",
        "publisher": BEA_PUBLISHER,
        "hosts": {"bea.gov", "www.bea.gov"},
    },
}
SOURCE_STATUSES = {"available", "unavailable", "invalid"}
VERIFICATION_LEVELS = {
    "official_corroborated",
    "official_primary",
    "official_fallback",
    "official_conflict",
}
HASH_PATTERN = re.compile(r"sha256:[0-9a-f]{64}")


class EconomicCalendarValidationError(ValueError):
    """Raised when economic_calendar.json weakens provenance guarantees."""


def validate_economic_calendar_artifact(artifact: Mapping[str, Any]) -> None:
    if artifact.get("schema_version") != "1.1":
        raise EconomicCalendarValidationError("unsupported calendar schema")
    if artifact.get("artifact_type") != "economic_calendar":
        raise EconomicCalendarValidationError("invalid calendar artifact_type")
    for field in ("generated_at", "window_start", "window_end"):
        _timestamp(artifact.get(field), field)
    if artifact.get("status") not in {"complete", "partial", "failed"}:
        raise EconomicCalendarValidationError("invalid calendar status")
    if not isinstance(artifact.get("retryable"), bool):
        raise EconomicCalendarValidationError("retryable must be boolean")
    if not isinstance(artifact.get("warnings"), list):
        raise EconomicCalendarValidationError("warnings must be a list")

    raw_sources = artifact.get("sources")
    raw_events = artifact.get("events")
    if not isinstance(raw_sources, list) or not raw_sources:
        raise EconomicCalendarValidationError("calendar sources must be non-empty")
    if not isinstance(raw_events, list):
        raise EconomicCalendarValidationError("calendar events must be a list")

    sources: Dict[str, Mapping[str, Any]] = {}
    for source in raw_sources:
        if not isinstance(source, Mapping):
            raise EconomicCalendarValidationError("source attempt must be an object")
        source_name = _required_text(source, "source", "source attempt")
        if source_name in sources:
            raise EconomicCalendarValidationError(f"duplicate source: {source_name}")
        policy = APPROVED_SOURCES.get(source_name)
        if policy is None:
            raise EconomicCalendarValidationError(f"unapproved source: {source_name}")
        if source.get("publisher") != policy["publisher"]:
            raise EconomicCalendarValidationError("calendar publisher is invalid")
        if source.get("priority") != policy["priority"]:
            raise EconomicCalendarValidationError("source priority is invalid")
        if source.get("source_format") != policy["format"]:
            raise EconomicCalendarValidationError("source format is invalid")
        _official_url(
            source.get("source_url"),
            f"{source_name}.source_url",
            policy["hosts"],
        )
        status = source.get("status")
        if status not in SOURCE_STATUSES:
            raise EconomicCalendarValidationError("source status is invalid")
        retrieved_at = source.get("retrieved_at")
        if status == "available":
            _timestamp(retrieved_at, f"{source_name}.retrieved_at")
            if source.get("failure_type") is not None or source.get("error") is not None:
                raise EconomicCalendarValidationError(
                    "available source cannot declare failure"
                )
        elif retrieved_at is not None:
            _timestamp(retrieved_at, f"{source_name}.retrieved_at")
        if not isinstance(source.get("retryable"), bool):
            raise EconomicCalendarValidationError("source retryable must be boolean")
        for count_field in ("parsed_event_count", "accepted_event_count"):
            value = source.get(count_field)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise EconomicCalendarValidationError(
                    f"{source_name}.{count_field} is invalid"
                )
        sources[source_name] = source

    if artifact.get("status") == "failed" and raw_events:
        raise EconomicCalendarValidationError("failed calendar contains events")
    if artifact.get("status") != "failed" and not any(
        source.get("status") == "available" for source in sources.values()
    ):
        raise EconomicCalendarValidationError("available calendar has no source")

    event_ids: Set[str] = set()
    conflict_groups: Dict[str, list[Mapping[str, Any]]] = {}
    for event in raw_events:
        if not isinstance(event, Mapping):
            raise EconomicCalendarValidationError("calendar event must be an object")
        event_id = _required_text(event, "event_id", "calendar event")
        if event_id in event_ids:
            raise EconomicCalendarValidationError(f"duplicate event_id: {event_id}")
        event_ids.add(event_id)
        for field in ("name", "source", "publisher", "verification_level"):
            _required_text(event, field, event_id)
        event_source = sources.get(str(event.get("source")))
        if event_source is None or event.get("publisher") != event_source.get("publisher"):
            raise EconomicCalendarValidationError(f"{event_id} publisher is invalid")
        _timestamp(event.get("scheduled_at"), f"{event_id}.scheduled_at")
        _timestamp(event.get("retrieved_at"), f"{event_id}.retrieved_at")
        event_policy = APPROVED_SOURCES[str(event.get("source"))]
        _official_url(
            event.get("source_url"),
            f"{event_id}.source_url",
            event_policy["hosts"],
        )
        _hash(event.get("content_hash"), f"{event_id}.content_hash")
        score = event.get("confidence_score")
        if (
            not isinstance(score, (int, float))
            or isinstance(score, bool)
            or not math.isfinite(score)
            or not 0 <= score <= 1
        ):
            raise EconomicCalendarValidationError(f"{event_id} confidence invalid")
        verification = event.get("verification_level")
        if verification not in VERIFICATION_LEVELS:
            raise EconomicCalendarValidationError(
                f"{event_id} verification_level is invalid"
            )
        provenance = event.get("provenance")
        if not isinstance(provenance, list) or not provenance:
            raise EconomicCalendarValidationError(f"{event_id} lacks provenance")
        provenance_sources: Set[str] = set()
        for record in provenance:
            if not isinstance(record, Mapping):
                raise EconomicCalendarValidationError("provenance must be an object")
            source_name = _required_text(record, "source", f"{event_id}.provenance")
            source_attempt = sources.get(source_name)
            if source_attempt is None or source_attempt.get("status") != "available":
                raise EconomicCalendarValidationError(
                    f"{event_id} provenance source is unavailable"
                )
            if record.get("publisher") != source_attempt.get("publisher"):
                raise EconomicCalendarValidationError("provenance publisher is invalid")
            if record.get("priority") != source_attempt.get("priority"):
                raise EconomicCalendarValidationError("provenance priority is invalid")
            _timestamp(record.get("retrieved_at"), "provenance.retrieved_at")
            if record.get("scheduled_at") != event.get("scheduled_at"):
                raise EconomicCalendarValidationError(
                    f"{event_id} provenance schedule mismatch"
                )
            _official_url(
                record.get("source_url"),
                "provenance.source_url",
                APPROVED_SOURCES[source_name]["hosts"],
            )
            _hash(record.get("content_hash"), "provenance.content_hash")
            provenance_sources.add(source_name)
        if event.get("source") not in provenance_sources:
            raise EconomicCalendarValidationError(
                f"{event_id} top-level source lacks provenance"
            )
        conflict_group = event.get("conflict_group_id")
        if verification == "official_corroborated":
            if provenance_sources != set(APPROVED_SOURCES):
                raise EconomicCalendarValidationError(
                    "corroborated event requires both official representations"
                )
            if conflict_group is not None:
                raise EconomicCalendarValidationError(
                    "corroborated event cannot have conflict_group_id"
                )
        elif verification == "official_primary":
            if provenance_sources != {"bls_release_calendar"}:
                raise EconomicCalendarValidationError("primary verification mismatch")
        elif verification == "official_fallback":
            if provenance_sources != {"bea_release_schedule"}:
                raise EconomicCalendarValidationError("fallback verification mismatch")
        else:
            if not isinstance(conflict_group, str) or not conflict_group:
                raise EconomicCalendarValidationError(
                    "conflicting event lacks conflict_group_id"
                )
            conflict_groups.setdefault(conflict_group, []).append(event)

    for group_id, group in conflict_groups.items():
        if len(group) < 2:
            raise EconomicCalendarValidationError(
                f"{group_id} does not preserve both conflict records"
            )
        if len({item.get("scheduled_at") for item in group}) < 2:
            raise EconomicCalendarValidationError(
                f"{group_id} does not contain conflicting schedules"
            )
        if {
            record.get("source")
            for item in group
            for record in item.get("provenance", [])
            if isinstance(record, Mapping)
        } != set(APPROVED_SOURCES):
            raise EconomicCalendarValidationError(
                f"{group_id} does not preserve both source records"
            )


def _required_text(value: Mapping[str, Any], field: str, context: str) -> str:
    result = value.get(field)
    if not isinstance(result, str) or not result.strip():
        raise EconomicCalendarValidationError(f"{context}.{field} is required")
    return result


def _timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise EconomicCalendarValidationError(f"{field} must be an ISO UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EconomicCalendarValidationError(f"{field} is invalid") from exc
    if parsed.tzinfo is None:
        raise EconomicCalendarValidationError(f"{field} lacks timezone")
    return parsed


def _official_url(value: Any, field: str, approved_hosts: Set[str]) -> None:
    if not isinstance(value, str):
        raise EconomicCalendarValidationError(f"{field} must be a URL")
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or (parsed.hostname or "").casefold() not in approved_hosts
    ):
        raise EconomicCalendarValidationError(
            f"{field} is not an approved official URL"
        )


def _hash(value: Any, field: str) -> None:
    if not isinstance(value, str) or not HASH_PATTERN.fullmatch(value):
        raise EconomicCalendarValidationError(f"{field} must be a SHA-256 digest")
