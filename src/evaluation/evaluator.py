"""Compute deterministic, non-market-quality metrics for one brief."""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Mapping, Optional

from src.brief.renderer_validator import validate_rendered_brief
from src.brief.renderer_validator import REFERENCE_KEYS
from src.data.freshness import (
    FreshnessValidationError,
    enrich_artifact_freshness,
    validate_freshness_contract,
)
from src.evaluation.schema import EVALUATION_PROFILES, FALLBACK_REQUIRED_SECTIONS
from src.grounded_brief.validator import validate_grounded_brief
from src.models.generation_metadata_schema import validate_generation_metadata


CITATION_PATTERN = re.compile(r"\[refs:\s*([^\]]+)\]\s*$", re.IGNORECASE)
SOURCE_LINE_PATTERN = re.compile(r"^Source\s*/\s*Evidence:\s*.+$", re.IGNORECASE)
WORD_PATTERN = re.compile(r"[\w'-]+", re.UNICODE)
SENTENCE_PATTERN = re.compile(r"[^.!?。！？]+[.!?。！？]?", re.UNICODE)


def evaluate_ai_brief(
    markdown: str,
    deterministic_fallback: str,
    top_intelligence: Mapping[str, Any],
    daily_intelligence: Mapping[str, Any],
    generation_metadata: Mapping[str, Any],
    clock: Optional[Callable[[], datetime]] = None,
) -> Dict[str, Any]:
    """Evaluate writing-contract quality without judging market correctness."""
    validate_generation_metadata(generation_metadata)
    if not isinstance(markdown, str):
        markdown = ""
    if not isinstance(deterministic_fallback, str):
        deterministic_fallback = ""

    generated_at = _iso((clock or (lambda: datetime.now(timezone.utc)))())
    mode = str(generation_metadata["generation_mode"])
    if mode not in EVALUATION_PROFILES:
        raise ValueError("generation mode has no calibrated evaluation profile")
    profile = EVALUATION_PROFILES[mode]
    exact_fallback_match = markdown.encode("utf-8") == deterministic_fallback.encode(
        "utf-8"
    )
    validation = _evaluate_validation(
        mode,
        markdown,
        deterministic_fallback,
        top_intelligence,
        daily_intelligence,
        exact_fallback_match,
        generated_at,
    )
    status = "complete" if validation["status"] == "passed" else "invalid"
    reason_code = validation["reason_code"]
    fallback_used = mode == "deterministic_fallback"
    fallback_consistent = (
        exact_fallback_match if fallback_used else mode != "unavailable"
    )
    quality_metrics = (
        _grounded_metrics(markdown, top_intelligence, daily_intelligence, validation)
        if mode == "grounded_ai"
        else _fallback_metrics(
            markdown,
            top_intelligence,
            daily_intelligence,
            validation,
        )
    )
    warnings = []
    if fallback_used:
        warnings.append("deterministic_fallback_used")
    if status == "invalid" and reason_code:
        warnings.append(f"validation_failed:{reason_code}")

    brief_sha = _sha256(markdown)
    fallback_sha = _sha256(deterministic_fallback)
    identity = "|".join(
        (
            str(top_intelligence.get("run_id", "unknown")),
            str(daily_intelligence.get("run_id", "unknown")),
            brief_sha,
            str(generation_metadata.get("generation_mode")),
            str(generation_metadata.get("generated_at")),
        )
    )
    artifact = {
        "schema_version": "2.0",
        "schema_contract": "ai_brief_evaluation_v2",
        "artifact_type": "ai_brief_evaluation",
        "run_id": f"run_{_compact_timestamp(generated_at)}_evaluation_{_sha256(identity)[:16]}",
        "generated_at": generated_at,
        "status": status,
        "evaluation_mode": mode,
        "evaluation_profile": profile,
        "generation_metadata": dict(generation_metadata),
        "validation_result": validation,
        "quality_metrics": quality_metrics,
        "fallback_status": {
            "used": fallback_used,
            "reason": generation_metadata.get("fallback_reason"),
            "exact_match": exact_fallback_match,
            "consistent_with_metadata": fallback_consistent,
        },
        "input_refs": {
            "top_intelligence_run_id": str(
                top_intelligence.get("run_id", "unknown")
            ),
            "daily_intelligence_run_id": str(
                daily_intelligence.get("run_id", "unknown")
            ),
            "ai_brief_sha256": brief_sha,
            "deterministic_fallback_sha256": fallback_sha,
        },
        "warnings": sorted(warnings),
    }
    return enrich_artifact_freshness(artifact, [daily_intelligence])


def _evaluate_validation(
    mode: str,
    markdown: str,
    deterministic_fallback: str,
    top: Mapping[str, Any],
    daily: Mapping[str, Any],
    exact_fallback_match: bool,
    evaluated_at: str,
) -> Dict[str, Any]:
    validator = (
        "grounded_brief_validator"
        if mode == "grounded_ai"
        else "deterministic_renderer_validator"
    )
    try:
        if mode == "grounded_ai":
            validate_grounded_brief(markdown, top, daily)
        else:
            if not exact_fallback_match:
                return {
                    "validator": validator,
                    "status": "failed",
                    "reason_code": "fallback_mismatch",
                    "evaluated_at": evaluated_at,
                }
            validate_rendered_brief(deterministic_fallback, daily, top)
    except ValueError as exc:
        return {
            "validator": validator,
            "status": "failed",
            "reason_code": _validation_reason(exc),
            "evaluated_at": evaluated_at,
        }
    return {
        "validator": validator,
        "status": "passed",
        "reason_code": None,
        "evaluated_at": evaluated_at,
    }


def _validation_reason(exc: ValueError) -> str:
    message = str(exc).lower()
    if "unknown citation" in message or "reference" in message:
        return "unsupported_reference"
    if "citation" in message:
        return "citation_violation"
    if "asset" in message:
        return "unsupported_asset"
    if "event" in message:
        return "unsupported_event"
    if "numerical" in message or "number" in message:
        return "unsupported_number"
    if "prohibited" in message:
        return "prohibited_claim"
    if "heading" in message or "top item" in message or "structure" in message:
        return "structure_violation"
    return "validation_failure"


def _citation_coverage(markdown: str) -> Dict[str, Any]:
    lines = [
        line.strip()
        for line in markdown.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    cited = sum(
        bool(CITATION_PATTERN.search(line) or SOURCE_LINE_PATTERN.fullmatch(line))
        for line in lines
    )
    count = len(lines)
    return {
        "citable_line_count": count,
        "cited_line_count": cited,
        "coverage_ratio": round(cited / count, 6) if count else 1.0,
        "missing_citation_count": count - cited,
    }


def _grounded_metrics(
    markdown: str,
    top: Mapping[str, Any],
    daily: Mapping[str, Any],
    validation: Mapping[str, Any],
) -> Dict[str, Any]:
    passed = validation["status"] == "passed"
    return {
        "grounding_compliance": {
            "status": "passed" if passed else "failed",
            "score": 1.0 if passed else 0.0,
            "violation_count": 0 if passed else 1,
        },
        "citation_coverage": _citation_coverage(markdown),
        "unsupported_claim_detection": {
            "status": "none_detected" if passed else "detected",
            "detected_count": 0 if passed else 1,
            "reason_code": None if passed else validation["reason_code"],
        },
        "reference_integrity": _grounded_reference_integrity(markdown, top, daily),
        "duplication": _duplication(markdown),
        "readability": _readability(markdown),
    }


def _fallback_metrics(
    markdown: str,
    top: Mapping[str, Any],
    daily: Mapping[str, Any],
    validation: Mapping[str, Any],
) -> Dict[str, Any]:
    schema_valid = validation["status"] == "passed"
    present = {
        "ai_market_brief.md": bool(markdown.strip()),
        "daily_intelligence.json": bool(daily),
        "top_intelligence.json": bool(top),
    }
    missing = sorted(name for name, available in present.items() if not available)
    sections = _section_completeness(markdown)
    references = _fallback_reference_preservation(markdown, top, daily)
    return {
        "schema_validity": {
            "status": "passed" if schema_valid else "failed",
            "valid": schema_valid,
            "reason_code": validation["reason_code"],
        },
        "artifact_completeness": {
            "status": "passed" if not missing else "failed",
            "required_artifact_count": len(present),
            "available_artifact_count": len(present) - len(missing),
            "missing_artifacts": missing,
            "complete": not missing,
        },
        "freshness_metadata": _fallback_freshness(top, daily),
        "reference_preservation": references,
        "section_completeness": sections,
    }


def _grounded_reference_integrity(
    markdown: str,
    top: Mapping[str, Any],
    daily: Mapping[str, Any],
) -> Dict[str, Any]:
    cited = sorted(set(_extract_grounded_references(markdown)))
    allowed = _reference_universe(top) | _reference_universe(daily)
    invalid = sorted(value for value in cited if value not in allowed)
    valid_count = len(cited) - len(invalid)
    return {
        "status": "passed" if not invalid else "failed",
        "cited_reference_count": len(cited),
        "valid_reference_count": valid_count,
        "invalid_reference_count": len(invalid),
        "integrity_ratio": round(valid_count / len(cited), 6) if cited else 1.0,
        "unknown_reference_hashes": sorted(_sha256(value)[:16] for value in invalid),
    }


def _extract_grounded_references(markdown: str) -> list[str]:
    references = []
    for line in markdown.splitlines():
        citation = CITATION_PATTERN.search(line)
        if citation:
            references.extend(_split_references(citation.group(1)))
        elif SOURCE_LINE_PATTERN.fullmatch(line.strip()):
            references.extend(_split_references(line.split(":", 1)[1]))
    return references


def _split_references(value: str) -> list[str]:
    return [item.strip().strip("`") for item in value.split(",") if item.strip()]


def _reference_universe(value: Any, parent_key: str = "") -> set[str]:
    references: set[str] = set()
    if isinstance(value, Mapping):
        for key, child in value.items():
            if isinstance(child, str) and _is_reference_key(str(key)):
                references.add(child)
            elif isinstance(child, list) and _is_reference_list_key(str(key)):
                references.update(str(item) for item in child if isinstance(item, str) and item)
            references.update(_reference_universe(child, str(key)))
    elif isinstance(value, list):
        for child in value:
            references.update(_reference_universe(child, parent_key))
    return references


def _is_reference_key(key: str) -> bool:
    return key in {
        "id",
        "run_id",
        "item_id",
        "object_id",
        "source_object_id",
        "source_id",
        "observation_id",
        "event_id",
        "evidence_id",
        "signal_id",
        "risk_id",
    } or key.endswith("_run_id")


def _is_reference_list_key(key: str) -> bool:
    return key in REFERENCE_KEYS or key.endswith("_refs") or key.endswith("_ids")


def _fallback_reference_preservation(
    markdown: str,
    top: Mapping[str, Any],
    daily: Mapping[str, Any],
) -> Dict[str, Any]:
    required = _renderer_reference_universe(top, daily)
    missing = sorted(value for value in required if value not in markdown)
    preserved = len(required) - len(missing)
    return {
        "status": "passed" if not missing else "failed",
        "required_reference_count": len(required),
        "preserved_reference_count": preserved,
        "missing_reference_count": len(missing),
        "preservation_ratio": round(preserved / len(required), 6) if required else 1.0,
        "missing_reference_hashes": sorted(_sha256(value)[:16] for value in missing),
    }


def _renderer_reference_universe(
    top: Mapping[str, Any], daily: Mapping[str, Any]
) -> set[str]:
    required: set[str] = set()
    for value in daily.get("input_refs", {}).values():
        if isinstance(value, str) and value:
            required.add(value)
    if isinstance(daily.get("run_id"), str):
        required.add(str(daily["run_id"]))
    for item in top.get("items", []):
        if not isinstance(item, Mapping):
            continue
        required.update(_explicit_object_references(item))
    for section in (
        "market_regime",
        "cross_asset_signals",
        "upcoming_events",
        "data_quality_risks",
        "observed_market_stress",
    ):
        values = daily.get(section, [])
        objects = values if isinstance(values, list) else [values]
        for item in objects:
            if isinstance(item, Mapping):
                object_id = item.get("object_id")
                if isinstance(object_id, str) and object_id:
                    required.add(object_id)
                required.update(_explicit_object_references(item))
    catalog = daily.get("provenance_catalog", {})
    if isinstance(catalog, Mapping):
        for collection, identifier in (
            ("evidence_bundles", "id"),
            ("source_records", "source_id"),
            ("observation_records", "observation_id"),
            ("event_records", "event_id"),
            ("evidence_records", "evidence_id"),
        ):
            records = catalog.get(collection, [])
            if not isinstance(records, list):
                continue
            required.update(
                str(record[identifier])
                for record in records
                if isinstance(record, Mapping)
                and isinstance(record.get(identifier), str)
                and record[identifier]
            )
    return required


def _explicit_object_references(item: Mapping[str, Any]) -> set[str]:
    required: set[str] = set()
    refs = item.get("evidence_refs", {})
    if isinstance(refs, Mapping):
        for values in refs.values():
            if isinstance(values, list):
                required.update(str(value) for value in values if isinstance(value, str) and value)
    source_refs = item.get("source_refs", [])
    if isinstance(source_refs, list):
        required.update(str(value) for value in source_refs if isinstance(value, str) and value)
    return required


def _fallback_freshness(
    top: Mapping[str, Any], daily: Mapping[str, Any]
) -> Dict[str, Any]:
    statuses = []
    valid = 0
    for artifact in (top, daily):
        try:
            validate_freshness_contract(artifact)
        except FreshnessValidationError:
            statuses.append("invalid")
        else:
            valid += 1
            statuses.append(str(artifact.get("freshness_status", "unknown")))
    return {
        "status": "passed" if valid == 2 else "failed",
        "checked_artifact_count": 2,
        "valid_contract_count": valid,
        "current_count": statuses.count("current"),
        "stale_count": statuses.count("stale"),
        "unavailable_count": statuses.count("unavailable"),
        "unknown_count": statuses.count("unknown"),
        "invalid_count": statuses.count("invalid"),
    }


def _section_completeness(markdown: str) -> Dict[str, Any]:
    headings = {line.strip() for line in markdown.splitlines() if line.startswith("#")}
    missing = sorted(
        heading for heading in FALLBACK_REQUIRED_SECTIONS if heading not in headings
    )
    return {
        "status": "passed" if not missing else "failed",
        "required_section_count": len(FALLBACK_REQUIRED_SECTIONS),
        "present_section_count": len(FALLBACK_REQUIRED_SECTIONS) - len(missing),
        "missing_sections": missing,
        "complete": not missing,
    }


def _duplication(markdown: str) -> Dict[str, Any]:
    normalized = []
    for raw in markdown.splitlines():
        line = " ".join(raw.strip().lower().split())
        if not line or line.startswith("#") or SOURCE_LINE_PATTERN.fullmatch(line):
            continue
        if CITATION_PATTERN.fullmatch(line):
            continue
        normalized.append(line)
    counts = Counter(normalized)
    duplicate_count = sum(count - 1 for count in counts.values() if count > 1)
    repeated_hashes = sorted(
        _sha256(line)[:16] for line, count in counts.items() if count > 1
    )
    total = len(normalized)
    return {
        "substantive_line_count": total,
        "duplicate_line_count": duplicate_count,
        "unique_line_ratio": (
            round(len(counts) / total, 6) if total else 1.0
        ),
        "repeated_line_hashes": repeated_hashes,
    }


def _readability(markdown: str) -> Dict[str, Any]:
    headings = 0
    list_items = 0
    paragraphs = []
    for block in re.split(r"\n\s*\n", markdown):
        value = block.strip()
        if not value:
            continue
        block_lines = value.splitlines()
        headings += sum(line.lstrip().startswith("#") for line in block_lines)
        list_items += sum(
            bool(re.match(r"^\s*[-*+]\s+", line)) for line in block_lines
        )
        prose = " ".join(
            line.strip()
            for line in block_lines
            if line.strip()
            and not line.lstrip().startswith("#")
            and not re.match(r"^\s*[-*+]\s+", line)
        )
        if prose:
            paragraphs.append(prose)
    sentences = [
        item.strip()
        for paragraph in paragraphs
        for item in SENTENCE_PATTERN.findall(paragraph)
        if item.strip()
    ]
    sentence_units = [len(WORD_PATTERN.findall(item)) for item in sentences]
    return {
        "paragraph_count": len(paragraphs),
        "heading_count": headings,
        "list_item_count": list_items,
        "sentence_count": len(sentences),
        "average_units_per_sentence": (
            round(sum(sentence_units) / len(sentence_units), 3)
            if sentence_units
            else 0.0
        ),
        "long_sentence_count": sum(value > 35 for value in sentence_units),
        "average_paragraph_characters": (
            round(sum(len(value) for value in paragraphs) / len(paragraphs), 3)
            if paragraphs
            else 0.0
        ),
    }


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _compact_timestamp(value: str) -> str:
    compact = value.replace("-", "").replace(":", "").replace("+00:00", "Z")
    if "." in compact:
        compact = compact.split(".", 1)[0] + "Z"
    return compact


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
