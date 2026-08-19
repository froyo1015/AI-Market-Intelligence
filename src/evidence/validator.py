"""Guardrails for observation and evidence artifacts."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Dict, Iterable, Mapping, Sequence, Set

from src.evidence.schema import EvidenceRelation, confidence_label


CAUSAL_LANGUAGE = re.compile(
    r"\b(?:because|caused|causes|due to|led to|driven by)\b|因為|由於|導致|造成|驅動",
    re.IGNORECASE,
)
NUMBER_PATTERN = re.compile(r"(?<![A-Za-z0-9_])-?\d+(?:\.\d+)?")
VALID_DATA_STATUSES = {"success", "stale"}


class EvidenceValidationError(ValueError):
    """Raised when a Phase 6.1 artifact violates a frozen contract."""


def validate_observation_artifact(artifact: Mapping[str, Any]) -> None:
    _validate_envelope(artifact, "observations")
    raw_sources = artifact.get("sources")
    raw_observations = artifact.get("observations")
    if not isinstance(raw_sources, list):
        raise EvidenceValidationError("observations.sources must be a list")
    if not isinstance(raw_observations, list):
        raise EvidenceValidationError("observations.observations must be a list")

    source_ids: Set[str] = set()
    for source in raw_sources:
        if not isinstance(source, dict):
            raise EvidenceValidationError("source reference must be an object")
        source_id = _required_string(source, "source_id", "source")
        if source_id in source_ids:
            raise EvidenceValidationError(f"duplicate source_id: {source_id}")
        source_ids.add(source_id)
        _required_string(source, "provider", source_id)
        _required_string(source, "publisher", source_id)
        retrieved_at = _required_string(source, "retrieved_at", source_id)
        _validate_timestamp(retrieved_at, f"{source_id}.retrieved_at")
        published_at = source.get("published_at")
        if published_at is not None:
            if not isinstance(published_at, str):
                raise EvidenceValidationError(
                    f"{source_id}.published_at must be a timestamp or null"
                )
            _validate_timestamp(published_at, f"{source_id}.published_at")
        content_hash = _required_string(source, "content_hash", source_id)
        if not content_hash.startswith("sha256:"):
            raise EvidenceValidationError(f"{source_id} content_hash must use sha256")
        quality_tier = source.get("quality_tier")
        if quality_tier not in {1, 2, 3}:
            raise EvidenceValidationError(f"{source_id} quality_tier is invalid")
        if source.get("source_type") == "macro_market_data":
            url = source.get("url")
            if not isinstance(url, str) or not url.startswith(("http://", "https://")):
                raise EvidenceValidationError(
                    f"{source_id} macro source URL is invalid"
                )

    observation_ids: Set[str] = set()
    for observation in raw_observations:
        if not isinstance(observation, dict):
            raise EvidenceValidationError("observation must be an object")
        observation_id = _required_string(
            observation, "observation_id", "observation"
        )
        if observation_id in observation_ids:
            raise EvidenceValidationError(
                f"duplicate observation_id: {observation_id}"
            )
        observation_ids.add(observation_id)
        _required_string(observation, "subject", observation_id)
        _required_string(observation, "metric", observation_id)
        as_of = _required_string(observation, "as_of", observation_id)
        _validate_timestamp(as_of, f"{observation_id}.as_of")
        source_id = _required_string(observation, "source_id", observation_id)
        if source_id not in source_ids:
            raise EvidenceValidationError(
                f"{observation_id} references unknown source_id {source_id}"
            )
        if observation.get("status") not in VALID_DATA_STATUSES:
            raise EvidenceValidationError(f"{observation_id} status is invalid")
        if observation.get("value") is None:
            raise EvidenceValidationError(f"{observation_id} value cannot be null")
        observation_type = observation.get("observation_type")
        if observation_type not in {
            "market_price",
            "market_feature",
            "macro_value",
        }:
            raise EvidenceValidationError(
                f"{observation_id} observation_type is invalid"
            )
        calculation = observation.get("calculation")
        if observation_type == "market_feature" and not isinstance(
            calculation, dict
        ):
            raise EvidenceValidationError(
                f"{observation_id} calculated feature lacks calculation metadata"
            )
        if isinstance(calculation, dict):
            _required_string(calculation, "rule_id", observation_id)
            if not isinstance(calculation.get("input_ids"), list):
                raise EvidenceValidationError(
                    f"{observation_id} calculation.input_ids must be a list"
                )
        if _schema_minor(artifact) >= 1:
            asset_mapping = _string_sequence(
                observation.get("asset_mapping"),
                "asset_mapping",
                observation_id,
            )
            if observation_type == "macro_value" and not asset_mapping:
                raise EvidenceValidationError(
                    f"{observation_id} macro observation has no asset mapping"
                )
            _validate_confidence(observation, observation_id)


def validate_evidence_artifact(
    artifact: Mapping[str, Any],
    observation_artifact: Mapping[str, Any],
    known_event_ids: Iterable[str] = (),
) -> None:
    validate_observation_artifact(observation_artifact)
    _validate_envelope(artifact, "evidence")
    if artifact.get("run_id") != observation_artifact.get("run_id"):
        raise EvidenceValidationError("evidence and observations run_id mismatch")
    if artifact.get("schema_version") != observation_artifact.get("schema_version"):
        raise EvidenceValidationError("evidence and observations schema mismatch")

    raw_evidence = artifact.get("evidence")
    if not isinstance(raw_evidence, list):
        raise EvidenceValidationError("evidence.evidence must be a list")
    observations = {
        item["observation_id"]: item
        for item in observation_artifact.get("observations", [])
        if isinstance(item, dict) and isinstance(item.get("observation_id"), str)
    }
    sources = {
        item["source_id"]
        for item in observation_artifact.get("sources", [])
        if isinstance(item, dict) and isinstance(item.get("source_id"), str)
    }
    event_ids = set(known_event_ids)
    evidence_ids: Set[str] = set()

    for bundle in raw_evidence:
        if not isinstance(bundle, dict):
            raise EvidenceValidationError("evidence bundle must be an object")
        evidence_id = _required_string(bundle, "evidence_id", "evidence")
        if evidence_id in evidence_ids:
            raise EvidenceValidationError(f"duplicate evidence_id: {evidence_id}")
        evidence_ids.add(evidence_id)

    for bundle in raw_evidence:
        evidence_id = str(bundle["evidence_id"])
        _required_string(bundle, "claim_type", evidence_id)
        statement = _required_string(bundle, "statement", evidence_id)
        relation = bundle.get("relation")
        if relation not in {item.value for item in EvidenceRelation}:
            raise EvidenceValidationError(f"{evidence_id} relation is invalid")
        if CAUSAL_LANGUAGE.search(statement):
            raise EvidenceValidationError(
                f"{evidence_id} uses prohibited causal language"
            )

        referenced_observations = _string_sequence(
            bundle.get("observation_ids"), "observation_ids", evidence_id
        )
        referenced_events = _string_sequence(
            bundle.get("event_ids"), "event_ids", evidence_id
        )
        referenced_sources = _string_sequence(
            bundle.get("supporting_source_ids"),
            "supporting_source_ids",
            evidence_id,
        )
        contradictions = _string_sequence(
            bundle.get("contradicting_evidence_ids"),
            "contradicting_evidence_ids",
            evidence_id,
        )
        if any(item not in observations for item in referenced_observations):
            raise EvidenceValidationError(
                f"{evidence_id} references an unknown observation"
            )
        if any(item not in event_ids for item in referenced_events):
            raise EvidenceValidationError(
                f"{evidence_id} references an unknown event"
            )
        if any(item not in sources for item in referenced_sources):
            raise EvidenceValidationError(
                f"{evidence_id} references an unknown source"
            )
        if relation != EvidenceRelation.UNCONFIRMED.value and not referenced_sources:
            raise EvidenceValidationError(
                f"{evidence_id} has no supporting source"
            )
        actual_sources = {
            str(observations[item]["source_id"]) for item in referenced_observations
        }
        if not set(referenced_sources).issubset(actual_sources):
            raise EvidenceValidationError(
                f"{evidence_id} source is not linked by its observations"
            )
        if any(item not in evidence_ids for item in contradictions):
            raise EvidenceValidationError(
                f"{evidence_id} references unknown contradicting evidence"
            )
        if evidence_id in contradictions:
            raise EvidenceValidationError(
                f"{evidence_id} cannot contradict itself"
            )

        if relation == EvidenceRelation.OBSERVED.value and not (
            referenced_observations or referenced_events
        ):
            raise EvidenceValidationError(
                f"{evidence_id} observed relation has no supporting input"
            )
        if relation == EvidenceRelation.ASSOCIATED.value and not (
            referenced_observations and referenced_events
        ):
            raise EvidenceValidationError(
                f"{evidence_id} associated relation requires event and observation"
            )
        if relation == EvidenceRelation.SUPPORTED_INTERPRETATION.value and (
            len(referenced_observations) + len(referenced_events) < 2
        ):
            raise EvidenceValidationError(
                f"{evidence_id} supported interpretation requires two inputs"
            )

        score = bundle.get("confidence_score")
        if not _is_number(score) or not 0.0 <= float(score) <= 1.0:
            raise EvidenceValidationError(
                f"{evidence_id} confidence_score must be between 0 and 1"
            )
        expected_label = confidence_label(float(score)).value
        if bundle.get("confidence_label") != expected_label:
            raise EvidenceValidationError(
                f"{evidence_id} confidence label does not match score"
            )
        if not isinstance(bundle.get("limitations"), list):
            raise EvidenceValidationError(
                f"{evidence_id} limitations must be a list"
            )
        if _schema_minor(artifact) >= 1:
            _string_sequence(
                bundle.get("affected_assets"),
                "affected_assets",
                evidence_id,
            )
        _validate_claim_numbers(statement, referenced_observations, observations, evidence_id)


def _validate_envelope(artifact: Mapping[str, Any], artifact_type: str) -> None:
    schema_version = artifact.get("schema_version")
    if not isinstance(schema_version, str) or not re.fullmatch(r"1\.\d+", schema_version):
        raise EvidenceValidationError(f"{artifact_type} schema_version is unsupported")
    if artifact.get("artifact_type") != artifact_type:
        raise EvidenceValidationError(f"expected artifact_type {artifact_type}")
    _required_string(artifact, "run_id", artifact_type)
    report_date = _required_string(artifact, "report_date", artifact_type)
    generated_at = _required_string(artifact, "generated_at", artifact_type)
    try:
        date.fromisoformat(report_date)
    except ValueError as exc:
        raise EvidenceValidationError(
            f"{artifact_type}.report_date is invalid"
        ) from exc
    _validate_timestamp(generated_at, f"{artifact_type}.generated_at")
    if artifact.get("status") not in {"complete", "partial", "failed"}:
        raise EvidenceValidationError(f"{artifact_type} status is invalid")
    if not isinstance(artifact.get("warnings"), list):
        raise EvidenceValidationError(f"{artifact_type} warnings must be a list")


def _validate_claim_numbers(
    statement: str,
    observation_ids: Sequence[str],
    observations: Mapping[str, Mapping[str, Any]],
    evidence_id: str,
) -> None:
    available = []
    for observation_id in observation_ids:
        value = observations[observation_id].get("value")
        if _is_number(value):
            available.extend((float(value), abs(float(value))))
    for raw_number in NUMBER_PATTERN.findall(statement):
        claimed = float(raw_number)
        if not any(abs(claimed - value) <= 1e-9 for value in available):
            raise EvidenceValidationError(
                f"{evidence_id} contains unsupported number {raw_number}"
            )


def _required_string(
    value: Mapping[str, Any], field: str, context: str
) -> str:
    item = value.get(field)
    if not isinstance(item, str) or not item:
        raise EvidenceValidationError(f"{context}.{field} must be a non-empty string")
    return item


def _string_sequence(value: Any, field: str, context: str) -> Sequence[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise EvidenceValidationError(f"{context}.{field} must be a string list")
    return tuple(value)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _validate_confidence(value: Mapping[str, Any], context: str) -> None:
    score = value.get("confidence_score")
    if not _is_number(score) or not 0.0 <= float(score) <= 1.0:
        raise EvidenceValidationError(
            f"{context} confidence_score must be between 0 and 1"
        )
    if value.get("confidence_label") != confidence_label(float(score)).value:
        raise EvidenceValidationError(
            f"{context} confidence label does not match score"
        )


def _schema_minor(artifact: Mapping[str, Any]) -> int:
    value = artifact.get("schema_version")
    if not isinstance(value, str):
        return 0
    try:
        return int(value.split(".", 1)[1])
    except (IndexError, ValueError):
        return 0


def _validate_timestamp(value: str, context: str) -> None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceValidationError(f"{context} is invalid") from exc
    if parsed.tzinfo is None:
        raise EvidenceValidationError(f"{context} must include timezone")
