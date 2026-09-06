"""Validated public metadata for the grounded brief generation outcome."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, Mapping, Optional


GENERATION_MODES = {"grounded_ai", "deterministic_fallback", "unavailable"}
GENERATION_STATUSES = {"success", "fallback", "failed"}
FRESHNESS_STATUSES = {"current", "stale", "unavailable", "unknown"}
VALIDATION_STATUSES = {"validated", "unavailable", "unknown"}
FALLBACK_REASONS = {
    "no_provider_configured",
    "provider_timeout",
    "provider_rate_limit",
    "invalid_llm_output",
    "malformed_provider_response",
    "provider_error",
    "pipeline_failure",
    "missing_generation_metadata",
}


class GenerationMetadataValidationError(ValueError):
    """Raised when public generation metadata is inconsistent or unsafe."""


@dataclass(frozen=True)
class GenerationMetadata:
    generation_mode: str
    generation_status: str
    generated_at: str
    freshness_status: str
    validation_status: str
    provider: Optional[str]
    fallback_reason: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        validate_generation_metadata(payload)
        return payload


def validate_generation_metadata(payload: Mapping[str, Any]) -> None:
    required = {
        "generation_mode",
        "generation_status",
        "generated_at",
        "freshness_status",
        "validation_status",
        "provider",
        "fallback_reason",
    }
    missing = sorted(required - set(payload))
    if missing:
        raise GenerationMetadataValidationError(
            f"generation metadata missing fields: {missing}"
        )
    extra = sorted(set(payload) - required)
    if extra:
        raise GenerationMetadataValidationError(
            f"generation metadata contains unsupported fields: {extra}"
        )

    mode = payload.get("generation_mode")
    status = payload.get("generation_status")
    freshness = payload.get("freshness_status")
    validation = payload.get("validation_status")
    provider = payload.get("provider")
    reason = payload.get("fallback_reason")

    if mode not in GENERATION_MODES:
        raise GenerationMetadataValidationError("invalid generation_mode")
    if status not in GENERATION_STATUSES:
        raise GenerationMetadataValidationError("invalid generation_status")
    if freshness not in FRESHNESS_STATUSES:
        raise GenerationMetadataValidationError("invalid generation freshness_status")
    if validation not in VALIDATION_STATUSES:
        raise GenerationMetadataValidationError("invalid generation validation_status")
    _validate_timestamp(payload.get("generated_at"))
    if provider is not None and (not isinstance(provider, str) or not provider.strip()):
        raise GenerationMetadataValidationError("provider must be null or a non-empty identifier")
    if reason is not None and reason not in FALLBACK_REASONS:
        raise GenerationMetadataValidationError("fallback_reason is not normalized")

    if mode == "grounded_ai":
        if status != "success" or validation != "validated":
            raise GenerationMetadataValidationError("grounded_ai state is inconsistent")
        if provider is None or reason is not None:
            raise GenerationMetadataValidationError("grounded_ai provider/reason is invalid")
    elif mode == "deterministic_fallback":
        if status != "fallback" or validation != "validated" or reason is None:
            raise GenerationMetadataValidationError("fallback state is inconsistent")
    elif status != "failed" or validation == "validated" or reason is None:
        raise GenerationMetadataValidationError("unavailable state is inconsistent")


def _validate_timestamp(value: Any) -> None:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise GenerationMetadataValidationError("generated_at must be a UTC timestamp")
    try:
        datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as exc:
        raise GenerationMetadataValidationError("generated_at is invalid") from exc
