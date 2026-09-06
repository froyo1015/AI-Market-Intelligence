"""Validate and summarize the production grounded-AI trial outcome safely."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

from src.evaluation.validator import validate_ai_brief_evaluation
from src.models.generation_metadata_schema import validate_generation_metadata


class ProductionTrialMonitoringError(ValueError):
    """Raised when production generation and evaluation records disagree."""


def monitor_production_trial(
    manifest: Mapping[str, Any], evaluation: Mapping[str, Any]
) -> Dict[str, Any]:
    """Return a secret-free monitoring result for one completed run."""
    validate_ai_brief_evaluation(evaluation)
    modules = manifest.get("modules")
    if not isinstance(modules, list):
        raise ProductionTrialMonitoringError("run manifest modules are unavailable")
    grounded = next(
        (
            module
            for module in modules
            if isinstance(module, Mapping)
            and module.get("name") == "grounded_ai_brief"
        ),
        None,
    )
    if grounded is None:
        raise ProductionTrialMonitoringError("grounded brief module is unavailable")
    metadata = grounded.get("generation_metadata")
    if not isinstance(metadata, Mapping):
        raise ProductionTrialMonitoringError("generation metadata is unavailable")
    validate_generation_metadata(metadata)
    if dict(metadata) != evaluation.get("generation_metadata"):
        raise ProductionTrialMonitoringError(
            "generation metadata does not match evaluation"
        )

    mode = str(metadata["generation_mode"])
    if mode == "grounded_ai":
        _validate_grounded_trial(metadata, evaluation)
        trial_status = "grounded_ai_validated"
        grounding_status = evaluation["quality_metrics"][
            "grounding_compliance"
        ]["status"]
        reference_status = evaluation["quality_metrics"][
            "reference_integrity"
        ]["status"]
    elif mode == "deterministic_fallback":
        _validate_fallback_trial(metadata, evaluation)
        trial_status = "fallback_active"
        grounding_status = "not_applicable"
        reference_status = evaluation["quality_metrics"][
            "reference_preservation"
        ]["status"]
    else:
        raise ProductionTrialMonitoringError("generation is unavailable")

    return {
        "trial_status": trial_status,
        "run_id": str(manifest.get("run_id", "unknown")),
        "generation_mode": mode,
        "generation_status": str(metadata["generation_status"]),
        "provider": metadata.get("provider"),
        "fallback_reason": metadata.get("fallback_reason"),
        "evaluation_profile": str(evaluation["evaluation_profile"]),
        "evaluation_status": str(evaluation["status"]),
        "validation_status": str(evaluation["validation_result"]["status"]),
        "grounding_status": grounding_status,
        "reference_status": reference_status,
        "freshness_status": str(evaluation["freshness_status"]),
    }


def _validate_grounded_trial(
    metadata: Mapping[str, Any], evaluation: Mapping[str, Any]
) -> None:
    metrics = evaluation.get("quality_metrics", {})
    valid = (
        metadata.get("generation_status") == "success"
        and metadata.get("provider") == "openai_responses"
        and metadata.get("validation_status") == "validated"
        and metadata.get("fallback_reason") is None
        and evaluation.get("evaluation_mode") == "grounded_ai"
        and evaluation.get("evaluation_profile") == "grounded_ai_profile"
        and evaluation.get("status") == "complete"
        and evaluation.get("validation_result", {}).get("status") == "passed"
        and metrics.get("grounding_compliance", {}).get("status") == "passed"
        and metrics.get("reference_integrity", {}).get("status") == "passed"
    )
    if not valid:
        raise ProductionTrialMonitoringError(
            "grounded AI trial did not pass the production quality contract"
        )


def _validate_fallback_trial(
    metadata: Mapping[str, Any], evaluation: Mapping[str, Any]
) -> None:
    metrics = evaluation.get("quality_metrics", {})
    required = {
        "schema_validity",
        "artifact_completeness",
        "freshness_metadata",
        "reference_preservation",
        "section_completeness",
    }
    valid = (
        metadata.get("generation_status") == "fallback"
        and metadata.get("validation_status") == "validated"
        and metadata.get("fallback_reason") is not None
        and evaluation.get("evaluation_mode") == "deterministic_fallback"
        and evaluation.get("evaluation_profile")
        == "deterministic_fallback_profile"
        and evaluation.get("status") == "complete"
        and evaluation.get("validation_result", {}).get("status") == "passed"
        and set(metrics) == required
        and metrics.get("schema_validity", {}).get("status") == "passed"
        and metrics.get("artifact_completeness", {}).get("status") == "passed"
        and metrics.get("freshness_metadata", {}).get("status") == "passed"
        and metrics.get("reference_preservation", {}).get("status") == "passed"
        and metrics.get("section_completeness", {}).get("status") == "passed"
    )
    if not valid:
        raise ProductionTrialMonitoringError(
            "deterministic fallback did not pass the production quality contract"
        )


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProductionTrialMonitoringError(f"cannot read {path.name}") from exc
    if not isinstance(payload, dict):
        raise ProductionTrialMonitoringError(f"{path.name} must contain an object")
    return payload


def _write_summary(result: Mapping[str, Any], path: Path) -> None:
    lines = [
        "## Grounded AI production trial",
        "",
        f"- Trial status: `{result['trial_status']}`",
        f"- Generation mode: `{result['generation_mode']}`",
        f"- Provider: `{result['provider'] or 'not configured'}`",
        f"- Evaluation profile: `{result['evaluation_profile']}`",
        f"- Evaluation status: `{result['evaluation_status']}`",
        f"- Grounding: `{result['grounding_status']}`",
        f"- References: `{result['reference_status']}`",
        f"- Freshness: `{result['freshness_status']}`",
    ]
    if result.get("fallback_reason"):
        lines.append(f"- Fallback reason: `{result['fallback_reason']}`")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Monitor one grounded AI production trial safely."
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--evaluation", type=Path, required=True)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args(argv)
    try:
        result = monitor_production_trial(
            _load_json(args.manifest),
            _load_json(args.evaluation),
        )
    except ProductionTrialMonitoringError as exc:
        print(f"Production trial monitoring failed: {exc}")
        return 1
    if args.summary is not None:
        _write_summary(result, args.summary)
    print(json.dumps(result, sort_keys=True))
    return 0


def cli() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    cli()
