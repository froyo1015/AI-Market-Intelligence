"""Schema constants for AI brief evaluation artifacts."""

from __future__ import annotations


SCHEMA_VERSION = "2.0"
SCHEMA_CONTRACT = "ai_brief_evaluation_v2"
ARTIFACT_TYPE = "ai_brief_evaluation"
EVALUATION_MODES = {"grounded_ai", "deterministic_fallback"}
EVALUATION_PROFILES = {
    "grounded_ai": "grounded_ai_profile",
    "deterministic_fallback": "deterministic_fallback_profile",
}
EVALUATION_STATUSES = {"complete", "invalid", "unavailable"}
VALIDATION_RESULT_STATUSES = {"passed", "failed", "not_applicable"}
GROUNDING_STATUSES = {"passed", "failed", "not_applicable"}
UNSUPPORTED_CLAIM_STATUSES = {"none_detected", "detected", "not_applicable"}
VALIDATORS = {
    "grounded_brief_validator",
    "deterministic_renderer_validator",
    "none",
}
REASON_CODES = {
    "citation_violation",
    "unsupported_reference",
    "unsupported_asset",
    "unsupported_event",
    "unsupported_number",
    "prohibited_claim",
    "structure_violation",
    "fallback_mismatch",
    "validation_failure",
    "generation_unavailable",
}
GROUNDED_METRICS = {
    "grounding_compliance",
    "citation_coverage",
    "unsupported_claim_detection",
    "reference_integrity",
    "duplication",
    "readability",
}
FALLBACK_METRICS = {
    "schema_validity",
    "artifact_completeness",
    "freshness_metadata",
    "reference_preservation",
    "section_completeness",
}

FALLBACK_REQUIRED_SECTIONS = (
    "# Daily Market Intelligence Brief",
    "# Today's Top Market Intelligence",
    "## Data Quality and Coverage",
    "## Current Market Regime",
    "## Cross-Asset Observations",
    "## Upcoming Event Risks",
    "## Data Quality Risks",
    "## Observed Market Stress",
    "## Sources and Provenance",
)
