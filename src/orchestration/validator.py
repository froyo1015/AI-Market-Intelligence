"""Validation for the Phase 6.4-D run manifest."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from src.data.freshness import FreshnessValidationError, validate_freshness_summary
from src.models.generation_metadata_schema import (
    GenerationMetadataValidationError,
    validate_generation_metadata,
)

from src.models.run_manifest_schema import (
    FRESHNESS_STATUSES,
    MODULE_STATUSES,
    RUN_STATUSES,
)


class RunManifestValidationError(ValueError):
    """Raised when a run manifest violates its frozen contract."""


def validate_run_manifest(
    manifest: Mapping[str, Any],
    expected_order: Sequence[str],
    approved_public_files: Sequence[str],
) -> None:
    required = {
        "schema_version",
        "artifact_type",
        "freshness_contract_version",
        "run_id",
        "execution_timestamp",
        "execution_started_at",
        "execution_completed_at",
        "status",
        "source_timestamp",
        "retrieved_at",
        "generated_at",
        "age_seconds",
        "freshness_status",
        "execution_order",
        "modules",
        "artifact_versions",
        "failures",
        "publication",
    }
    missing = sorted(required - set(manifest))
    if missing:
        raise RunManifestValidationError(f"manifest missing fields: {missing}")
    if manifest["artifact_type"] != "run_manifest":
        raise RunManifestValidationError("artifact_type must be run_manifest")
    if manifest["schema_version"] != "1.0":
        raise RunManifestValidationError("unsupported run manifest schema")
    if manifest["execution_timestamp"] != manifest["execution_started_at"]:
        raise RunManifestValidationError("execution timestamp must identify run start")
    if manifest["status"] not in RUN_STATUSES:
        raise RunManifestValidationError("invalid run status")
    if manifest["freshness_status"] not in FRESHNESS_STATUSES:
        raise RunManifestValidationError("invalid run freshness status")
    try:
        validate_freshness_summary(manifest)
    except FreshnessValidationError as exc:
        raise RunManifestValidationError(str(exc)) from exc
    if manifest["execution_order"] != list(expected_order):
        raise RunManifestValidationError("execution order does not match contract")

    modules = manifest["modules"]
    if not isinstance(modules, list) or len(modules) != len(expected_order):
        raise RunManifestValidationError("module records do not match execution order")
    if [module.get("name") for module in modules] != list(expected_order):
        raise RunManifestValidationError("module record order is invalid")
    for sequence, module in enumerate(modules, start=1):
        if module.get("sequence") != sequence:
            raise RunManifestValidationError("module sequence is invalid")
        if module.get("status") not in MODULE_STATUSES:
            raise RunManifestValidationError("module status is invalid")
        if module.get("freshness_status") not in FRESHNESS_STATUSES:
            raise RunManifestValidationError("module freshness status is invalid")
        try:
            validate_freshness_summary(module)
        except FreshnessValidationError as exc:
            raise RunManifestValidationError(str(exc)) from exc
        if module.get("status") == "blocked" and not module.get("failure"):
            raise RunManifestValidationError("blocked module must describe its failure")
        for artifact in module.get("artifacts", []):
            try:
                validate_freshness_summary(artifact)
            except FreshnessValidationError as exc:
                raise RunManifestValidationError(str(exc)) from exc
            if artifact.get("data_status") not in {"success", "partial", "unavailable"}:
                raise RunManifestValidationError("artifact data status is invalid")
            source_health = artifact.get("source_health")
            if not isinstance(source_health, list) or any(
                not isinstance(item, dict) for item in source_health
            ):
                raise RunManifestValidationError("artifact source health is invalid")
            for source in source_health:
                if source.get("status") not in {"available", "unavailable", "invalid"}:
                    raise RunManifestValidationError("source health status is invalid")
                if not isinstance(source.get("source"), str):
                    raise RunManifestValidationError("source health identity is invalid")
            digest = artifact.get("sha256", "")
            if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
                raise RunManifestValidationError("artifact SHA-256 is invalid")

    publication = manifest["publication"]
    approved = set(approved_public_files)
    if set(publication.get("approved_files", [])) != approved:
        raise RunManifestValidationError("publication allowlist is incomplete")
    if not set(publication.get("published_files", [])).issubset(approved):
        raise RunManifestValidationError("publication contains an unapproved file")
    failure_modules = {item.get("module") for item in manifest["failures"]}
    for module in modules:
        if module.get("status") in {"unavailable", "blocked", "failed"}:
            if module.get("name") not in failure_modules:
                raise RunManifestValidationError(
                    "degraded module must have a run-level failure record"
                )

    grounded_module = next(
        (module for module in modules if module.get("name") == "grounded_ai_brief"),
        None,
    )
    if grounded_module is None:
        raise RunManifestValidationError("grounded brief module is missing")
    metadata = grounded_module.get("generation_metadata")
    if not isinstance(metadata, dict):
        raise RunManifestValidationError("grounded brief generation metadata is missing")
    try:
        validate_generation_metadata(metadata)
    except GenerationMetadataValidationError as exc:
        raise RunManifestValidationError(str(exc)) from exc
