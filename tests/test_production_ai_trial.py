from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.brief.intelligence_renderer import render_daily_market_brief
from src.data.freshness import enrich_artifact_freshness
from src.evaluation.evaluator import evaluate_ai_brief
from src.evaluation.trial_monitor import (
    ProductionTrialMonitoringError,
    main,
    monitor_production_trial,
)
from tests.test_ai_brief_evaluation import FIXED_NOW
from tests.test_grounded_ai_brief import _inputs, _valid_brief


def _fresh_inputs() -> tuple[dict, dict]:
    top, daily = _inputs()
    daily = enrich_artifact_freshness(daily)
    top = enrich_artifact_freshness(top, [daily])
    return top, daily


def _metadata(mode: str) -> dict:
    if mode == "grounded_ai":
        return {
            "generation_mode": "grounded_ai",
            "generation_status": "success",
            "generated_at": "2026-09-03T01:00:00Z",
            "freshness_status": "current",
            "validation_status": "validated",
            "provider": "openai_responses",
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


def _artifacts(mode: str) -> tuple[dict, dict]:
    top, daily = _fresh_inputs()
    fallback = render_daily_market_brief(daily, top).markdown
    markdown = _valid_brief(top, daily) if mode == "grounded_ai" else fallback
    metadata = _metadata(mode)
    evaluation = evaluate_ai_brief(
        markdown,
        fallback,
        top,
        daily,
        metadata,
        clock=lambda: FIXED_NOW,
    )
    manifest = {
        "run_id": "run_production_trial",
        "modules": [
            {
                "name": "grounded_ai_brief",
                "generation_metadata": metadata,
            }
        ],
    }
    return manifest, evaluation


def test_grounded_ai_trial_is_reported_only_after_quality_validation() -> None:
    manifest, evaluation = _artifacts("grounded_ai")

    result = monitor_production_trial(manifest, evaluation)

    assert result == {
        "trial_status": "grounded_ai_validated",
        "run_id": "run_production_trial",
        "generation_mode": "grounded_ai",
        "generation_status": "success",
        "provider": "openai_responses",
        "fallback_reason": None,
        "evaluation_profile": "grounded_ai_profile",
        "evaluation_status": "complete",
        "validation_status": "passed",
        "grounding_status": "passed",
        "reference_status": "passed",
        "freshness_status": evaluation["freshness_status"],
    }


def test_fallback_remains_a_valid_monitored_production_outcome() -> None:
    manifest, evaluation = _artifacts("deterministic_fallback")

    result = monitor_production_trial(manifest, evaluation)

    assert result["trial_status"] == "fallback_active"
    assert result["generation_mode"] == "deterministic_fallback"
    assert result["provider"] is None
    assert result["fallback_reason"] == "no_provider_configured"
    assert result["grounding_status"] == "not_applicable"


def test_monitor_rejects_metadata_mismatch() -> None:
    manifest, evaluation = _artifacts("grounded_ai")
    manifest["modules"][0]["generation_metadata"] = _metadata(
        "deterministic_fallback"
    )

    with pytest.raises(
        ProductionTrialMonitoringError,
        match="does not match evaluation",
    ):
        monitor_production_trial(manifest, evaluation)


def test_cli_writes_only_sanitized_summary(tmp_path: Path) -> None:
    manifest, evaluation = _artifacts("grounded_ai")
    manifest_path = tmp_path / "manifest.json"
    evaluation_path = tmp_path / "evaluation.json"
    summary_path = tmp_path / "summary.md"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    evaluation_path.write_text(json.dumps(evaluation), encoding="utf-8")

    assert main(
        [
            "--manifest",
            str(manifest_path),
            "--evaluation",
            str(evaluation_path),
            "--summary",
            str(summary_path),
        ]
    ) == 0
    summary = summary_path.read_text(encoding="utf-8")
    assert "grounded_ai_validated" in summary
    assert "openai_responses" in summary
    assert "prompt" not in summary.lower()
    assert "api_key" not in summary.lower()


def test_workflow_uses_secret_one_call_trial_and_monitoring() -> None:
    workflow = Path(".github/workflows/daily_market_brief.yml").read_text(
        encoding="utf-8"
    )

    assert "OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}" in workflow
    assert 'OPENAI_GROUNDED_BRIEF_TRANSIENT_RETRIES: "0"' in workflow
    assert workflow.count("python -m src.orchestration.pipeline") == 1
    assert workflow.count("python -m src.evaluation.trial_monitor") == 1
    assert "--evaluation src/output/ai_brief_evaluation.json" in workflow
