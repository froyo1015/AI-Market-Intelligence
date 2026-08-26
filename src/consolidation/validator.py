"""Guardrails for Phase 6.2-D consolidated factual evidence."""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Any, Mapping, Sequence, Set

from src.consolidation.builder import CAUSAL_OR_PREDICTIVE_LANGUAGE


EXPECTED_COVERAGE = {
    "market_observations",
    "macro_observations",
    "economic_calendar",
    "news_events",
    "existing_evidence",
}
VALID_BUNDLE_TYPES = {
    "evidence_fact",
    "observation",
    "calendar_event",
    "news_event",
}
VALID_AVAILABILITY = {"available", "partial", "unavailable"}
VALID_FRESHNESS = {"fresh", "stale", "mixed", "unknown"}
VALID_VERIFICATION = {
    "official",
    "corroborated",
    "observed",
    "single_source",
    "unverified",
}
PROHIBITED_KEYS = {
    "bullish",
    "bearish",
    "llm",
    "llm_output",
    "market_prediction",
    "prediction",
    "price_impact",
    "rank",
    "ranking",
    "recommendation",
    "sentiment",
    "signal",
    "trading_signal",
}
HASH_PATTERN = re.compile(r"sha256:[0-9a-f]{64}")
BUNDLE_ID_PATTERN = re.compile(r"ebd_[0-9a-f]{20}")


class ConsolidatedEvidenceValidationError(ValueError):
    """Raised when an evidence bundle violates the Phase 6.2-D contract."""


def validate_consolidated_evidence_artifact(artifact: Mapping[str, Any]) -> None:
    if artifact.get("schema_version") != "1.0":
        raise ConsolidatedEvidenceValidationError("unsupported schema_version")
    if artifact.get("artifact_type") != "evidence_bundle":
        raise ConsolidatedEvidenceValidationError("invalid artifact_type")
    _required_string(artifact, "run_id", "artifact")
    try:
        date.fromisoformat(_required_string(artifact, "report_date", "artifact"))
    except ValueError as exc:
        raise ConsolidatedEvidenceValidationError("invalid report_date") from exc
    _timestamp(_required_string(artifact, "generated_at", "artifact"), "generated_at")
    if artifact.get("status") not in VALID_AVAILABILITY:
        raise ConsolidatedEvidenceValidationError("invalid artifact status")
    _string_list(artifact.get("warnings"), "warnings", "artifact")
    _reject_prohibited_keys(artifact)

    coverage = artifact.get("coverage")
    bundles = artifact.get("bundles")
    rejections = artifact.get("rejections")
    if not isinstance(coverage, list):
        raise ConsolidatedEvidenceValidationError("coverage must be a list")
    if not isinstance(bundles, list):
        raise ConsolidatedEvidenceValidationError("bundles must be a list")
    if not isinstance(rejections, list):
        raise ConsolidatedEvidenceValidationError("rejections must be a list")
    if artifact.get("bundle_count") != len(bundles):
        raise ConsolidatedEvidenceValidationError("bundle_count mismatch")
    if artifact.get("rejection_count") != len(rejections):
        raise ConsolidatedEvidenceValidationError("rejection_count mismatch")

    coverage_types: Set[str] = set()
    for record in coverage:
        if not isinstance(record, dict):
            raise ConsolidatedEvidenceValidationError("coverage record must be object")
        input_type = _required_string(record, "input_type", "coverage")
        if input_type in coverage_types:
            raise ConsolidatedEvidenceValidationError("duplicate coverage input_type")
        coverage_types.add(input_type)
        _required_string(record, "artifact", input_type)
        if record.get("status") not in VALID_AVAILABILITY:
            raise ConsolidatedEvidenceValidationError(
                f"{input_type} coverage status is invalid"
            )
        for field in ("record_count", "stale_record_count"):
            value = record.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ConsolidatedEvidenceValidationError(
                    f"{input_type}.{field} is invalid"
                )
        if record["stale_record_count"] > record["record_count"]:
            raise ConsolidatedEvidenceValidationError(
                f"{input_type} stale count exceeds record count"
            )
        if record.get("generated_at") is not None:
            _timestamp(str(record["generated_at"]), f"{input_type}.generated_at")
        _string_list(record.get("warnings"), "warnings", input_type)
    if coverage_types != EXPECTED_COVERAGE:
        raise ConsolidatedEvidenceValidationError("coverage classes are incomplete")

    for rejection in rejections:
        if not isinstance(rejection, dict):
            raise ConsolidatedEvidenceValidationError("rejection must be object")
        _required_string(rejection, "record_type", "rejection")
        _required_string(rejection, "input_artifact", "rejection")
        _string_list(
            rejection.get("reason_codes"),
            "reason_codes",
            "rejection",
            nonempty=True,
        )

    bundle_ids: Set[str] = set()
    for bundle in bundles:
        if not isinstance(bundle, dict):
            raise ConsolidatedEvidenceValidationError("bundle must be object")
        bundle_id = _required_string(bundle, "id", "bundle")
        if not BUNDLE_ID_PATTERN.fullmatch(bundle_id) or bundle_id in bundle_ids:
            raise ConsolidatedEvidenceValidationError(
                f"invalid or duplicate bundle id: {bundle_id}"
            )
        bundle_ids.add(bundle_id)
        _validate_bundle(bundle)

    if not bundles:
        expected_status = "unavailable"
    elif (
        any(record["status"] != "available" for record in coverage)
        or rejections
        or any(bundle["data_quality"]["status"] != "available" for bundle in bundles)
    ):
        expected_status = "partial"
    else:
        expected_status = "available"
    if artifact.get("status") != expected_status:
        raise ConsolidatedEvidenceValidationError(
            f"artifact status must be {expected_status}"
        )


def _validate_bundle(bundle: Mapping[str, Any]) -> None:
    bundle_id = str(bundle["id"])
    bundle_type = bundle.get("type")
    if bundle_type not in VALID_BUNDLE_TYPES:
        raise ConsolidatedEvidenceValidationError(f"{bundle_id}.type is invalid")
    assets = _string_list(bundle.get("related_assets"), "related_assets", bundle_id)
    if assets != sorted(set(assets)):
        raise ConsolidatedEvidenceValidationError(
            f"{bundle_id}.related_assets must be sorted and unique"
        )
    sources = _object_list(bundle.get("source_records"), "source_records", bundle_id)
    observations = _object_list(bundle.get("observations"), "observations", bundle_id)
    events = _object_list(bundle.get("events"), "events", bundle_id)
    evidence_records = _object_list(
        bundle.get("evidence_records"), "evidence_records", bundle_id
    )
    if not observations and not events and not evidence_records:
        raise ConsolidatedEvidenceValidationError(f"{bundle_id} has no factual record")
    if not sources:
        raise ConsolidatedEvidenceValidationError(f"{bundle_id} has no source record")
    if bundle_type == "observation" and not (
        len(observations) == 1 and not events and not evidence_records
    ):
        raise ConsolidatedEvidenceValidationError(
            f"{bundle_id} observation bundle shape is invalid"
        )
    if bundle_type in {"calendar_event", "news_event"} and not (
        len(events) == 1 and not observations and not evidence_records
    ):
        raise ConsolidatedEvidenceValidationError(
            f"{bundle_id} event bundle shape is invalid"
        )
    if bundle_type == "evidence_fact" and not evidence_records:
        raise ConsolidatedEvidenceValidationError(
            f"{bundle_id} evidence_fact lacks Evidence records"
        )

    source_ids = _unique_ids(sources, "source_id", bundle_id)
    observation_ids = _unique_ids(observations, "observation_id", bundle_id)
    event_ids = _unique_ids(events, "event_id", bundle_id)
    evidence_ids = _unique_ids(evidence_records, "evidence_id", bundle_id)
    for source in sources:
        _validate_source(source, bundle_id)
    for observation in observations:
        if observation.get("source_id") not in source_ids:
            raise ConsolidatedEvidenceValidationError(
                f"{bundle_id} observation has dangling source_id"
            )
        _timestamp(
            _required_string(observation, "as_of", bundle_id),
            f"{bundle_id}.observation.as_of",
        )
        if observation.get("status") not in {"success", "stale"}:
            raise ConsolidatedEvidenceValidationError(
                f"{bundle_id} observation status is invalid"
            )
    for record in evidence_records:
        statement = _required_string(record, "statement", bundle_id)
        if CAUSAL_OR_PREDICTIVE_LANGUAGE.search(statement):
            raise ConsolidatedEvidenceValidationError(
                f"{bundle_id} contains causal or predictive language"
            )
        referenced_observations = set(
            _string_list(
                record.get("observation_ids"),
                "observation_ids",
                bundle_id,
            )
        )
        if not referenced_observations.issubset(observation_ids):
            raise ConsolidatedEvidenceValidationError(
                f"{bundle_id} Evidence has dangling observation ID"
            )
        if not set(_string_list(record.get("event_ids"), "event_ids", bundle_id)).issubset(
            event_ids
        ):
            raise ConsolidatedEvidenceValidationError(
                f"{bundle_id} Evidence has dangling event ID"
            )
        if not set(
            _string_list(record.get("supporting_source_ids"), "source_ids", bundle_id)
        ).issubset(source_ids):
            raise ConsolidatedEvidenceValidationError(
                f"{bundle_id} Evidence has dangling source ID"
            )
    expected_assets = {
        asset
        for observation in observations
        for asset in _string_list(
            observation.get("asset_mapping"), "asset_mapping", bundle_id
        )
    }
    expected_assets.update(
        asset
        for event in events
        for field in ("affected_assets", "candidate_assets")
        for asset in (
            _string_list(event.get(field), field, bundle_id)
            if event.get(field) is not None
            else []
        )
    )
    expected_assets.update(
        asset
        for record in evidence_records
        for asset in _string_list(
            record.get("affected_assets"), "affected_assets", bundle_id
        )
    )
    if assets != sorted(expected_assets):
        raise ConsolidatedEvidenceValidationError(
            f"{bundle_id} related_assets do not preserve input mappings"
        )

    provenance = bundle.get("provenance")
    if not isinstance(provenance, dict):
        raise ConsolidatedEvidenceValidationError(f"{bundle_id}.provenance is invalid")
    if provenance.get("source_ids") != sorted(source_ids):
        raise ConsolidatedEvidenceValidationError(f"{bundle_id} source provenance mismatch")
    if provenance.get("observation_ids") != sorted(observation_ids):
        raise ConsolidatedEvidenceValidationError(
            f"{bundle_id} observation provenance mismatch"
        )
    if provenance.get("event_ids") != sorted(event_ids):
        raise ConsolidatedEvidenceValidationError(f"{bundle_id} event provenance mismatch")
    if provenance.get("evidence_ids") != sorted(evidence_ids):
        raise ConsolidatedEvidenceValidationError(
            f"{bundle_id} Evidence provenance mismatch"
        )
    _string_list(
        provenance.get("input_artifacts"), "input_artifacts", bundle_id, nonempty=True
    )
    _string_list(provenance.get("input_run_ids"), "input_run_ids", bundle_id)
    if provenance.get("consolidation_rule_id") != "exact_fact_consolidation_v1":
        raise ConsolidatedEvidenceValidationError(
            f"{bundle_id} consolidation rule is invalid"
        )
    dedupe_key = _required_string(provenance, "deduplication_key", bundle_id)
    if not HASH_PATTERN.fullmatch(dedupe_key):
        raise ConsolidatedEvidenceValidationError(f"{bundle_id} dedupe key is invalid")
    if bundle_id != f"ebd_{dedupe_key.removeprefix('sha256:')[:20]}":
        raise ConsolidatedEvidenceValidationError(
            f"{bundle_id} does not match deduplication key"
        )

    timestamps = bundle.get("timestamps")
    if not isinstance(timestamps, dict):
        raise ConsolidatedEvidenceValidationError(f"{bundle_id}.timestamps is invalid")
    for field in (
        "observed_at",
        "occurred_at",
        "scheduled_at",
        "published_at",
        "retrieved_at",
    ):
        values = _string_list(timestamps.get(field), field, bundle_id)
        if values != sorted(set(values)):
            raise ConsolidatedEvidenceValidationError(
                f"{bundle_id}.{field} must be sorted and unique"
            )
        for value in values:
            _timestamp(value, f"{bundle_id}.{field}")
    _timestamp(
        _required_string(timestamps, "consolidated_at", bundle_id),
        f"{bundle_id}.consolidated_at",
    )
    if set(timestamps["observed_at"]) != {
        _utc_string(str(item["as_of"])) for item in observations
    }:
        raise ConsolidatedEvidenceValidationError(
            f"{bundle_id} observed timestamps are incomplete"
        )
    if set(timestamps["occurred_at"]) != {
        _utc_string(str(item["occurred_at"]))
        for item in events
        if item.get("occurred_at") is not None
    }:
        raise ConsolidatedEvidenceValidationError(
            f"{bundle_id} occurrence timestamps are incomplete"
        )
    if set(timestamps["scheduled_at"]) != {
        _utc_string(str(item["scheduled_at"]))
        for item in events
        if item.get("scheduled_at") is not None
    }:
        raise ConsolidatedEvidenceValidationError(
            f"{bundle_id} scheduled timestamps are incomplete"
        )
    if set(timestamps["published_at"]) != {
        _utc_string(str(item["published_at"]))
        for item in sources
        if item.get("published_at") is not None
    }:
        raise ConsolidatedEvidenceValidationError(
            f"{bundle_id} publication timestamps are incomplete"
        )
    if set(timestamps["retrieved_at"]) != {
        _utc_string(str(item["retrieved_at"])) for item in sources
    }:
        raise ConsolidatedEvidenceValidationError(
            f"{bundle_id} retrieval timestamps are incomplete"
        )

    if bundle.get("verification_level") not in VALID_VERIFICATION:
        raise ConsolidatedEvidenceValidationError(
            f"{bundle_id}.verification_level is invalid"
        )
    if any(
        source.get("quality_tier") == 1
        and source.get("source_type") in {"official", "official_calendar"}
        for source in sources
    ):
        expected_verification = "official"
    elif len(
        {
            (str(source.get("provider")), str(source.get("publisher")))
            for source in sources
        }
    ) >= 2:
        expected_verification = "corroborated"
    elif observations and any(
        item.get("relation") == "observed" for item in evidence_records
    ):
        expected_verification = "observed"
    elif sources:
        expected_verification = "single_source"
    else:
        expected_verification = "unverified"
    if bundle.get("verification_level") != expected_verification:
        raise ConsolidatedEvidenceValidationError(
            f"{bundle_id}.verification_level conflicts with provenance"
        )
    quality = bundle.get("data_quality")
    freshness = bundle.get("freshness")
    if not isinstance(quality, dict) or not isinstance(freshness, dict):
        raise ConsolidatedEvidenceValidationError(
            f"{bundle_id} quality or freshness is invalid"
        )
    if quality.get("status") not in VALID_AVAILABILITY:
        raise ConsolidatedEvidenceValidationError(
            f"{bundle_id}.data_quality.status is invalid"
        )
    _string_list(quality.get("issues"), "issues", bundle_id)
    expected_counts = {
        "source_count": len(sources),
        "observation_count": len(observations),
        "event_count": len(events),
        "evidence_count": len(evidence_records),
    }
    if any(quality.get(field) != value for field, value in expected_counts.items()):
        raise ConsolidatedEvidenceValidationError(f"{bundle_id} quality counts mismatch")
    if freshness.get("status") not in VALID_FRESHNESS:
        raise ConsolidatedEvidenceValidationError(
            f"{bundle_id}.freshness.status is invalid"
        )
    stale_ids = _string_list(
        freshness.get("stale_record_ids"), "stale_record_ids", bundle_id
    )
    factual_ids = observation_ids | event_ids | evidence_ids
    if not set(stale_ids).issubset(factual_ids):
        raise ConsolidatedEvidenceValidationError(
            f"{bundle_id} freshness has unknown record ID"
        )
    expected_quality = "partial" if stale_ids else "available"
    if quality.get("status") != expected_quality:
        raise ConsolidatedEvidenceValidationError(
            f"{bundle_id} data quality conflicts with freshness"
        )
    if stale_ids:
        expected_freshness = (
            "stale" if set(stale_ids) == factual_ids else "mixed"
        )
        if freshness.get("status") != expected_freshness:
            raise ConsolidatedEvidenceValidationError(
                f"{bundle_id} freshness status conflicts with stale IDs"
            )


def _validate_source(source: Mapping[str, Any], context: str) -> None:
    for field in ("provider", "publisher", "source_type", "title"):
        _required_string(source, field, context)
    if source.get("quality_tier") not in {1, 2, 3}:
        raise ConsolidatedEvidenceValidationError(
            f"{context} source quality tier is invalid"
        )
    content_hash = _required_string(source, "content_hash", context)
    if not HASH_PATTERN.fullmatch(content_hash):
        raise ConsolidatedEvidenceValidationError(
            f"{context} source content hash is invalid"
        )
    _timestamp(
        _required_string(source, "retrieved_at", context),
        f"{context}.source.retrieved_at",
    )
    if source.get("published_at") is not None:
        _timestamp(str(source["published_at"]), f"{context}.source.published_at")


def _reject_prohibited_keys(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).casefold() in PROHIBITED_KEYS:
                raise ConsolidatedEvidenceValidationError(
                    f"prohibited Phase 6.2-D field: {key}"
                )
            _reject_prohibited_keys(child)
    elif isinstance(value, list):
        for child in value:
            _reject_prohibited_keys(child)


def _required_string(value: Mapping[str, Any], field: str, context: str) -> str:
    item = value.get(field)
    if not isinstance(item, str) or not item.strip():
        raise ConsolidatedEvidenceValidationError(
            f"{context}.{field} must be a non-empty string"
        )
    return item


def _string_list(
    value: Any,
    field: str,
    context: str,
    nonempty: bool = False,
) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item for item in value
    ):
        raise ConsolidatedEvidenceValidationError(
            f"{context}.{field} must be a string list"
        )
    if nonempty and not value:
        raise ConsolidatedEvidenceValidationError(
            f"{context}.{field} cannot be empty"
        )
    return value


def _object_list(value: Any, field: str, context: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise ConsolidatedEvidenceValidationError(
            f"{context}.{field} must be an object list"
        )
    return value


def _unique_ids(
    records: Sequence[Mapping[str, Any]], field: str, context: str
) -> Set[str]:
    values = [_required_string(item, field, context) for item in records]
    if len(values) != len(set(values)):
        raise ConsolidatedEvidenceValidationError(
            f"{context} contains duplicate {field}"
        )
    return set(values)


def _timestamp(value: str, context: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ConsolidatedEvidenceValidationError(
            f"{context} is not a valid timestamp"
        ) from exc
    if parsed.tzinfo is None:
        raise ConsolidatedEvidenceValidationError(
            f"{context} must include timezone"
        )
    return parsed


def _utc_string(value: str) -> str:
    return (
        _timestamp(value, "timestamp")
        .astimezone(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )
