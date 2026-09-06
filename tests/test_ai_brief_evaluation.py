from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.brief.intelligence_renderer import render_daily_market_brief
from src.evaluation.evaluator import evaluate_ai_brief
from src.evaluation.pipeline import run_ai_brief_evaluation_pipeline
from src.evaluation.validator import validate_ai_brief_evaluation
from tests.test_grounded_ai_brief import _inputs, _valid_brief


FIXED_NOW = datetime(2026, 9, 3, 1, 2, 3, 456000, tzinfo=timezone.utc)


def _metadata(mode: str = "grounded_ai") -> dict:
    if mode == "grounded_ai":
        return {
            "generation_mode": "grounded_ai",
            "generation_status": "success",
            "generated_at": "2026-09-03T01:00:00Z",
            "freshness_status": "current",
            "validation_status": "validated",
            "provider": "static_test_writer",
            "fallback_reason": None,
        }
    return {
        "generation_mode": "deterministic_fallback",
        "generation_status": "fallback",
        "generated_at": "2026-09-03T01:00:00Z",
        "freshness_status": "current",
        "validation_status": "validated",
        "provider": None,
        "fallback_reason": "no_provider_configured",
    }


def _fallback(top: dict, daily: dict) -> str:
    return render_daily_market_brief(daily, top).markdown


def _evaluate(markdown: str, mode: str = "grounded_ai") -> dict:
    top, daily = _inputs()
    return evaluate_ai_brief(
        markdown,
        _fallback(top, daily),
        top,
        daily,
        _metadata(mode),
        clock=lambda: FIXED_NOW,
    )


def test_successful_grounded_brief_evaluation() -> None:
    top, daily = _inputs()
    artifact = _evaluate(_valid_brief(top, daily))

    validate_ai_brief_evaluation(artifact)
    assert artifact["status"] == "complete"
    assert artifact["evaluation_mode"] == "grounded_ai"
    assert artifact["evaluation_profile"] == "grounded_ai_profile"
    assert artifact["run_id"].startswith("run_20260903T010203Z_evaluation_")
    assert artifact["validation_result"]["status"] == "passed"
    assert artifact["quality_metrics"]["grounding_compliance"] == {
        "status": "passed",
        "score": 1.0,
        "violation_count": 0,
    }
    assert artifact["quality_metrics"]["unsupported_claim_detection"]["status"] == "none_detected"
    assert artifact["quality_metrics"]["reference_integrity"]["status"] == "passed"
    assert set(artifact["quality_metrics"]) == {
        "grounding_compliance",
        "citation_coverage",
        "unsupported_claim_detection",
        "reference_integrity",
        "duplication",
        "readability",
    }
    assert artifact["generation_metadata"]["provider"] == "static_test_writer"


def test_deterministic_fallback_evaluation() -> None:
    top, daily = _inputs()
    fallback = _fallback(top, daily)
    artifact = evaluate_ai_brief(
        fallback,
        fallback,
        top,
        daily,
        _metadata("deterministic_fallback"),
        clock=lambda: FIXED_NOW,
    )

    validate_ai_brief_evaluation(artifact)
    assert artifact["status"] == "complete"
    assert artifact["evaluation_mode"] == "deterministic_fallback"
    assert artifact["evaluation_profile"] == "deterministic_fallback_profile"
    assert artifact["validation_result"]["validator"] == "deterministic_renderer_validator"
    assert set(artifact["quality_metrics"]) == {
        "schema_validity",
        "artifact_completeness",
        "freshness_metadata",
        "reference_preservation",
        "section_completeness",
    }
    assert artifact["quality_metrics"]["schema_validity"]["status"] == "passed"
    assert artifact["quality_metrics"]["artifact_completeness"]["status"] == "passed"
    assert artifact["quality_metrics"]["reference_preservation"]["status"] == "passed"
    assert artifact["quality_metrics"]["section_completeness"]["status"] == "passed"
    assert artifact["quality_metrics"]["freshness_metadata"]["status"] == "failed"
    assert "citation_coverage" not in artifact["quality_metrics"]
    assert "readability" not in artifact["quality_metrics"]
    assert artifact["fallback_status"] == {
        "used": True,
        "reason": "no_provider_configured",
        "exact_match": True,
        "consistent_with_metadata": True,
    }
    assert artifact["warnings"] == ["deterministic_fallback_used"]


@pytest.mark.parametrize(
    ("generation_mode", "expected_profile"),
    (
        ("grounded_ai", "grounded_ai_profile"),
        ("deterministic_fallback", "deterministic_fallback_profile"),
    ),
)
def test_profile_selection_comes_from_generation_metadata(
    generation_mode: str,
    expected_profile: str,
) -> None:
    top, daily = _inputs()
    markdown = (
        _valid_brief(top, daily)
        if generation_mode == "grounded_ai"
        else _fallback(top, daily)
    )
    artifact = _evaluate(markdown, generation_mode)

    assert artifact["evaluation_mode"] == generation_mode
    assert artifact["evaluation_profile"] == expected_profile
    validate_ai_brief_evaluation(artifact)


def test_valid_fallback_has_no_false_grounded_profile_failure() -> None:
    top, daily = _inputs()
    fallback = _fallback(top, daily)
    assert len(fallback) > 20_000

    artifact = _evaluate(fallback, "deterministic_fallback")

    assert artifact["status"] == "complete"
    assert artifact["validation_result"]["status"] == "passed"
    assert "output_length" not in artifact["quality_metrics"]
    assert "grounding_compliance" not in artifact["quality_metrics"]
    assert artifact["quality_metrics"]["reference_preservation"]["missing_reference_count"] == 0
    assert artifact["quality_metrics"]["section_completeness"]["complete"] is True


def test_citation_coverage_is_measured_from_grounded_lines() -> None:
    top, daily = _inputs()
    artifact = _evaluate(_valid_brief(top, daily))
    coverage = artifact["quality_metrics"]["citation_coverage"]

    assert coverage["citable_line_count"] > 0
    assert coverage["cited_line_count"] == coverage["citable_line_count"]
    assert coverage["missing_citation_count"] == 0
    assert coverage["coverage_ratio"] == 1.0


def test_invalid_output_is_recorded_without_judging_market_correctness() -> None:
    top, daily = _inputs()
    invalid = _valid_brief(top, daily).replace(
        "This is a current validated priority.",
        "Gold will rise.",
        1,
    )
    artifact = _evaluate(invalid)

    validate_ai_brief_evaluation(artifact)
    assert artifact["status"] == "invalid"
    assert artifact["validation_result"]["status"] == "failed"
    assert artifact["validation_result"]["reason_code"] == "prohibited_claim"
    assert artifact["quality_metrics"]["unsupported_claim_detection"] == {
        "status": "detected",
        "detected_count": 1,
        "reason_code": "prohibited_claim",
    }


def test_pipeline_writes_valid_evaluation_artifact(tmp_path: Path) -> None:
    top, daily = _inputs()
    brief = _valid_brief(top, daily)
    fallback = _fallback(top, daily)
    inputs = {
        "top.json": top,
        "daily.json": daily,
        "metadata.json": _metadata(),
    }
    for name, payload in inputs.items():
        (tmp_path / name).write_text(json.dumps(payload), encoding="utf-8")
    (tmp_path / "ai.md").write_text(brief, encoding="utf-8")
    (tmp_path / "fallback.md").write_text(fallback, encoding="utf-8")
    output = tmp_path / "evaluation.json"

    artifact = run_ai_brief_evaluation_pipeline(
        tmp_path / "top.json",
        tmp_path / "daily.json",
        tmp_path / "ai.md",
        tmp_path / "fallback.md",
        tmp_path / "metadata.json",
        output,
    )

    assert output.is_file()
    assert json.loads(output.read_text(encoding="utf-8")) == artifact
    validate_ai_brief_evaluation(artifact)
