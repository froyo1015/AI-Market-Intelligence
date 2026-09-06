"""Structural validation for AI brief evaluation artifacts."""

from __future__ import annotations

from typing import Any, Mapping

from src.data.freshness import FreshnessValidationError, validate_freshness_contract
from src.evaluation.schema import (
    ARTIFACT_TYPE,
    EVALUATION_STATUSES,
    EVALUATION_MODES,
    EVALUATION_PROFILES,
    FALLBACK_METRICS,
    GROUNDED_METRICS,
    GROUNDING_STATUSES,
    REASON_CODES,
    SCHEMA_CONTRACT,
    SCHEMA_VERSION,
    UNSUPPORTED_CLAIM_STATUSES,
    VALIDATION_RESULT_STATUSES,
    VALIDATORS,
)
from src.models.generation_metadata_schema import (
    GenerationMetadataValidationError,
    validate_generation_metadata,
)


class AIBriefEvaluationValidationError(ValueError):
    """Raised when evaluation output violates its public contract."""


def validate_ai_brief_evaluation(artifact: Mapping[str, Any]) -> None:
    required = {
        "schema_version",
        "schema_contract",
        "artifact_type",
        "freshness_contract_version",
        "run_id",
        "source_timestamp",
        "retrieved_at",
        "generated_at",
        "age_seconds",
        "freshness_status",
        "freshness_basis",
        "stale_after_seconds",
        "status",
        "evaluation_mode",
        "evaluation_profile",
        "generation_metadata",
        "validation_result",
        "quality_metrics",
        "fallback_status",
        "input_refs",
        "warnings",
    }
    missing = sorted(required - set(artifact))
    if missing:
        raise AIBriefEvaluationValidationError(
            f"evaluation artifact missing fields: {missing}"
        )
    if artifact.get("schema_version") != SCHEMA_VERSION:
        raise AIBriefEvaluationValidationError("unsupported evaluation schema version")
    if artifact.get("schema_contract") != SCHEMA_CONTRACT:
        raise AIBriefEvaluationValidationError("unsupported evaluation schema contract")
    if artifact.get("artifact_type") != ARTIFACT_TYPE:
        raise AIBriefEvaluationValidationError("invalid evaluation artifact type")
    if artifact.get("status") not in EVALUATION_STATUSES:
        raise AIBriefEvaluationValidationError("invalid evaluation status")
    evaluation_mode = artifact.get("evaluation_mode")
    if evaluation_mode not in EVALUATION_MODES:
        raise AIBriefEvaluationValidationError("invalid evaluation mode")
    if artifact.get("evaluation_profile") != EVALUATION_PROFILES[evaluation_mode]:
        raise AIBriefEvaluationValidationError("evaluation profile does not match mode")
    if not isinstance(artifact.get("run_id"), str) or not artifact["run_id"]:
        raise AIBriefEvaluationValidationError("evaluation run_id is required")
    try:
        validate_freshness_contract(artifact)
        validate_generation_metadata(_mapping(artifact, "generation_metadata"))
    except (FreshnessValidationError, GenerationMetadataValidationError) as exc:
        raise AIBriefEvaluationValidationError(str(exc)) from exc

    validation = _mapping(artifact, "validation_result")
    if set(validation) != {"validator", "status", "reason_code", "evaluated_at"}:
        raise AIBriefEvaluationValidationError("validation_result fields do not match")
    if validation.get("validator") not in VALIDATORS:
        raise AIBriefEvaluationValidationError("invalid evaluation validator")
    if validation.get("status") not in VALIDATION_RESULT_STATUSES:
        raise AIBriefEvaluationValidationError("invalid validation result status")
    reason = validation.get("reason_code")
    if reason is not None and reason not in REASON_CODES:
        raise AIBriefEvaluationValidationError("invalid validation reason code")
    if validation.get("status") == "passed" and reason is not None:
        raise AIBriefEvaluationValidationError("passed validation cannot have reason")
    if validation.get("status") == "failed" and reason is None:
        raise AIBriefEvaluationValidationError("failed validation requires reason")

    metrics = _mapping(artifact, "quality_metrics")
    if evaluation_mode == "grounded_ai":
        if set(metrics) != GROUNDED_METRICS:
            raise AIBriefEvaluationValidationError("grounded metric groups do not match")
        _validate_grounding(_mapping(metrics, "grounding_compliance"))
        _validate_citations(_mapping(metrics, "citation_coverage"))
        _validate_unsupported(_mapping(metrics, "unsupported_claim_detection"))
        _validate_reference_integrity(_mapping(metrics, "reference_integrity"))
        _validate_duplication(_mapping(metrics, "duplication"))
        _validate_readability(_mapping(metrics, "readability"))
    else:
        if set(metrics) != FALLBACK_METRICS:
            raise AIBriefEvaluationValidationError("fallback metric groups do not match")
        _validate_schema_validity(_mapping(metrics, "schema_validity"))
        _validate_artifact_completeness(_mapping(metrics, "artifact_completeness"))
        _validate_freshness_metadata(_mapping(metrics, "freshness_metadata"))
        _validate_reference_preservation(_mapping(metrics, "reference_preservation"))
        _validate_section_completeness(_mapping(metrics, "section_completeness"))

    fallback = _mapping(artifact, "fallback_status")
    if set(fallback) != {
        "used",
        "reason",
        "exact_match",
        "consistent_with_metadata",
    } or any(
        not isinstance(fallback.get(key), bool)
        for key in ("used", "exact_match", "consistent_with_metadata")
    ):
        raise AIBriefEvaluationValidationError("fallback_status is invalid")
    if artifact.get("status") == "complete" and not fallback["consistent_with_metadata"]:
        raise AIBriefEvaluationValidationError("complete evaluation has fallback conflict")
    generation = _mapping(artifact, "generation_metadata")
    if generation.get("generation_mode") != evaluation_mode:
        raise AIBriefEvaluationValidationError("evaluation mode conflicts with generation metadata")
    expected_fallback = generation.get("generation_mode") == "deterministic_fallback"
    if fallback["used"] != expected_fallback:
        raise AIBriefEvaluationValidationError("fallback usage conflicts with metadata")
    if fallback["reason"] != generation.get("fallback_reason"):
        raise AIBriefEvaluationValidationError("fallback reason conflicts with metadata")

    refs = _mapping(artifact, "input_refs")
    if set(refs) != {
        "top_intelligence_run_id",
        "daily_intelligence_run_id",
        "ai_brief_sha256",
        "deterministic_fallback_sha256",
    } or any(not isinstance(value, str) or not value for value in refs.values()):
        raise AIBriefEvaluationValidationError("input_refs are invalid")
    for key in ("ai_brief_sha256", "deterministic_fallback_sha256"):
        if len(refs[key]) != 64 or any(char not in "0123456789abcdef" for char in refs[key]):
            raise AIBriefEvaluationValidationError("input digest is invalid")
    warnings = artifact.get("warnings")
    if not isinstance(warnings, list) or warnings != sorted(set(warnings)) or any(
        not isinstance(value, str) for value in warnings
    ):
        raise AIBriefEvaluationValidationError("evaluation warnings are invalid")


def _validate_grounding(value: Mapping[str, Any]) -> None:
    if set(value) != {"status", "score", "violation_count"}:
        raise AIBriefEvaluationValidationError("grounding metric fields do not match")
    if value.get("status") not in GROUNDING_STATUSES:
        raise AIBriefEvaluationValidationError("invalid grounding status")
    score = value.get("score")
    if score is not None and score not in {0.0, 1.0}:
        raise AIBriefEvaluationValidationError("invalid grounding score")
    _nonnegative_int(value.get("violation_count"), "grounding violation count")


def _validate_citations(value: Mapping[str, Any]) -> None:
    if set(value) != {
        "citable_line_count",
        "cited_line_count",
        "coverage_ratio",
        "missing_citation_count",
    }:
        raise AIBriefEvaluationValidationError("citation metric fields do not match")
    total = _nonnegative_int(value.get("citable_line_count"), "citable line count")
    cited = _nonnegative_int(value.get("cited_line_count"), "cited line count")
    missing = _nonnegative_int(value.get("missing_citation_count"), "missing citation count")
    ratio = value.get("coverage_ratio")
    if cited > total or missing != total - cited:
        raise AIBriefEvaluationValidationError("citation counts are inconsistent")
    _ratio(ratio, "citation coverage")


def _validate_unsupported(value: Mapping[str, Any]) -> None:
    if set(value) != {"status", "detected_count", "reason_code"}:
        raise AIBriefEvaluationValidationError("unsupported-claim fields do not match")
    if value.get("status") not in UNSUPPORTED_CLAIM_STATUSES:
        raise AIBriefEvaluationValidationError("invalid unsupported-claim status")
    _nonnegative_int(value.get("detected_count"), "unsupported claim count")
    reason = value.get("reason_code")
    if reason is not None and reason not in REASON_CODES:
        raise AIBriefEvaluationValidationError("invalid unsupported-claim reason")


def _validate_reference_integrity(value: Mapping[str, Any]) -> None:
    if set(value) != {
        "status",
        "cited_reference_count",
        "valid_reference_count",
        "invalid_reference_count",
        "integrity_ratio",
        "unknown_reference_hashes",
    }:
        raise AIBriefEvaluationValidationError("reference integrity fields do not match")
    _pass_fail(value.get("status"), "reference integrity")
    total = _nonnegative_int(value.get("cited_reference_count"), "cited reference count")
    valid = _nonnegative_int(value.get("valid_reference_count"), "valid reference count")
    invalid = _nonnegative_int(value.get("invalid_reference_count"), "invalid reference count")
    if valid + invalid != total:
        raise AIBriefEvaluationValidationError("reference integrity counts are inconsistent")
    _ratio(value.get("integrity_ratio"), "reference integrity ratio")
    _hashes(value.get("unknown_reference_hashes"), "unknown reference hashes")


def _validate_schema_validity(value: Mapping[str, Any]) -> None:
    if set(value) != {"status", "valid", "reason_code"}:
        raise AIBriefEvaluationValidationError("schema validity fields do not match")
    _pass_fail(value.get("status"), "schema validity")
    if not isinstance(value.get("valid"), bool):
        raise AIBriefEvaluationValidationError("schema validity flag is invalid")
    if value["valid"] != (value["status"] == "passed"):
        raise AIBriefEvaluationValidationError("schema validity is inconsistent")
    reason = value.get("reason_code")
    if reason is not None and reason not in REASON_CODES:
        raise AIBriefEvaluationValidationError("schema validity reason is invalid")


def _validate_artifact_completeness(value: Mapping[str, Any]) -> None:
    if set(value) != {
        "status",
        "required_artifact_count",
        "available_artifact_count",
        "missing_artifacts",
        "complete",
    }:
        raise AIBriefEvaluationValidationError("artifact completeness fields do not match")
    _completion_metric(value, "artifact", "missing_artifacts")


def _validate_freshness_metadata(value: Mapping[str, Any]) -> None:
    required = {
        "status",
        "checked_artifact_count",
        "valid_contract_count",
        "current_count",
        "stale_count",
        "unavailable_count",
        "unknown_count",
        "invalid_count",
    }
    if set(value) != required:
        raise AIBriefEvaluationValidationError("freshness metric fields do not match")
    _pass_fail(value.get("status"), "freshness metadata")
    checked = _nonnegative_int(value.get("checked_artifact_count"), "checked artifact count")
    valid = _nonnegative_int(value.get("valid_contract_count"), "valid freshness count")
    counts = sum(
        _nonnegative_int(value.get(key), key)
        for key in ("current_count", "stale_count", "unavailable_count", "unknown_count", "invalid_count")
    )
    if counts != checked or valid != checked - value["invalid_count"]:
        raise AIBriefEvaluationValidationError("freshness metric counts are inconsistent")


def _validate_reference_preservation(value: Mapping[str, Any]) -> None:
    if set(value) != {
        "status",
        "required_reference_count",
        "preserved_reference_count",
        "missing_reference_count",
        "preservation_ratio",
        "missing_reference_hashes",
    }:
        raise AIBriefEvaluationValidationError("reference preservation fields do not match")
    _pass_fail(value.get("status"), "reference preservation")
    required = _nonnegative_int(value.get("required_reference_count"), "required reference count")
    preserved = _nonnegative_int(value.get("preserved_reference_count"), "preserved reference count")
    missing = _nonnegative_int(value.get("missing_reference_count"), "missing reference count")
    if preserved + missing != required:
        raise AIBriefEvaluationValidationError("reference preservation counts are inconsistent")
    _ratio(value.get("preservation_ratio"), "reference preservation ratio")
    _hashes(value.get("missing_reference_hashes"), "missing reference hashes")


def _validate_section_completeness(value: Mapping[str, Any]) -> None:
    if set(value) != {
        "status",
        "required_section_count",
        "present_section_count",
        "missing_sections",
        "complete",
    }:
        raise AIBriefEvaluationValidationError("section completeness fields do not match")
    _completion_metric(value, "section", "missing_sections")


def _validate_duplication(value: Mapping[str, Any]) -> None:
    if set(value) != {
        "substantive_line_count",
        "duplicate_line_count",
        "unique_line_ratio",
        "repeated_line_hashes",
    }:
        raise AIBriefEvaluationValidationError("duplication metric fields do not match")
    _nonnegative_int(value.get("substantive_line_count"), "substantive line count")
    _nonnegative_int(value.get("duplicate_line_count"), "duplicate line count")
    _ratio(value.get("unique_line_ratio"), "unique line ratio")
    hashes = value.get("repeated_line_hashes")
    if not isinstance(hashes, list) or hashes != sorted(set(hashes)) or any(
        not isinstance(item, str) or len(item) != 16 for item in hashes
    ):
        raise AIBriefEvaluationValidationError("repeated line hashes are invalid")


def _validate_readability(value: Mapping[str, Any]) -> None:
    if set(value) != {
        "paragraph_count",
        "heading_count",
        "list_item_count",
        "sentence_count",
        "average_units_per_sentence",
        "long_sentence_count",
        "average_paragraph_characters",
    }:
        raise AIBriefEvaluationValidationError("readability metric fields do not match")
    for key in (
        "paragraph_count",
        "heading_count",
        "list_item_count",
        "sentence_count",
        "long_sentence_count",
    ):
        _nonnegative_int(value.get(key), key)
    for key in ("average_units_per_sentence", "average_paragraph_characters"):
        metric = value.get(key)
        if not isinstance(metric, (int, float)) or isinstance(metric, bool) or metric < 0:
            raise AIBriefEvaluationValidationError(f"{key} is invalid")


def _mapping(parent: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = parent.get(key)
    if not isinstance(value, Mapping):
        raise AIBriefEvaluationValidationError(f"{key} must be an object")
    return value


def _nonnegative_int(value: Any, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise AIBriefEvaluationValidationError(f"{name} is invalid")
    return value


def _ratio(value: Any, name: str) -> None:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or value < 0
        or value > 1
    ):
        raise AIBriefEvaluationValidationError(f"{name} is invalid")


def _pass_fail(value: Any, name: str) -> None:
    if value not in {"passed", "failed"}:
        raise AIBriefEvaluationValidationError(f"{name} status is invalid")


def _hashes(value: Any, name: str) -> None:
    if not isinstance(value, list) or value != sorted(set(value)) or any(
        not isinstance(item, str)
        or len(item) != 16
        or any(char not in "0123456789abcdef" for char in item)
        for item in value
    ):
        raise AIBriefEvaluationValidationError(f"{name} are invalid")


def _completion_metric(
    value: Mapping[str, Any], label: str, missing_key: str
) -> None:
    _pass_fail(value.get("status"), f"{label} completeness")
    required_key = f"required_{label}_count"
    present_key = (
        "available_artifact_count"
        if label == "artifact"
        else "present_section_count"
    )
    required = _nonnegative_int(value.get(required_key), required_key)
    present = _nonnegative_int(value.get(present_key), present_key)
    missing = value.get(missing_key)
    if not isinstance(missing, list) or missing != sorted(set(missing)) or any(
        not isinstance(item, str) or not item for item in missing
    ):
        raise AIBriefEvaluationValidationError(f"{missing_key} is invalid")
    complete = value.get("complete")
    if not isinstance(complete, bool):
        raise AIBriefEvaluationValidationError(f"{label} completeness flag is invalid")
    if present + len(missing) != required:
        raise AIBriefEvaluationValidationError(f"{label} completeness counts are inconsistent")
    if complete != (not missing) or (value.get("status") == "passed") != complete:
        raise AIBriefEvaluationValidationError(f"{label} completeness state is inconsistent")
