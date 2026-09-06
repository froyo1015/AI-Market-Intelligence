"""CLI and atomic artifact pipeline for AI brief evaluation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

from src.evaluation.evaluator import evaluate_ai_brief
from src.evaluation.validator import validate_ai_brief_evaluation


OUTPUT_DIRECTORY = Path(__file__).resolve().parents[1] / "output"
DEFAULT_TOP_PATH = OUTPUT_DIRECTORY / "top_intelligence.json"
DEFAULT_DAILY_PATH = OUTPUT_DIRECTORY / "daily_intelligence.json"
DEFAULT_AI_BRIEF_PATH = OUTPUT_DIRECTORY / "ai_market_brief.md"
DEFAULT_FALLBACK_PATH = OUTPUT_DIRECTORY / "daily_market_brief.md"
DEFAULT_METADATA_PATH = OUTPUT_DIRECTORY / "generation_metadata.json"
DEFAULT_OUTPUT_PATH = OUTPUT_DIRECTORY / "ai_brief_evaluation.json"


class AIBriefEvaluationInputError(ValueError):
    """Raised when evaluation inputs cannot be read safely."""


def run_ai_brief_evaluation_pipeline(
    top_path: Path = DEFAULT_TOP_PATH,
    daily_path: Path = DEFAULT_DAILY_PATH,
    ai_brief_path: Path = DEFAULT_AI_BRIEF_PATH,
    fallback_path: Path = DEFAULT_FALLBACK_PATH,
    generation_metadata_path: Path = DEFAULT_METADATA_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> Dict[str, Any]:
    top = _load_json(top_path, "top_intelligence")
    daily = _load_json(daily_path, "daily_intelligence")
    metadata = _load_json(generation_metadata_path, None)
    ai_brief = _load_text(ai_brief_path, required=False)
    fallback = _load_text(fallback_path, required=True)
    artifact = evaluate_ai_brief(
        ai_brief,
        fallback,
        top,
        daily,
        metadata,
    )
    validate_ai_brief_evaluation(artifact)
    _write_json(artifact, output_path)
    return artifact


def _load_json(path: Path, expected_type: Optional[str]) -> Dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AIBriefEvaluationInputError(f"cannot read {path.name}") from exc
    if not isinstance(payload, dict):
        raise AIBriefEvaluationInputError(f"{path.name} must contain an object")
    if expected_type is not None and payload.get("artifact_type") != expected_type:
        raise AIBriefEvaluationInputError(
            f"{path.name} is not a {expected_type} artifact"
        )
    return payload


def _load_text(path: Path, required: bool) -> str:
    try:
        value = path.read_text(encoding="utf-8")
    except OSError as exc:
        if not required:
            return ""
        raise AIBriefEvaluationInputError(f"cannot read {path.name}") from exc
    if required and not value.strip():
        raise AIBriefEvaluationInputError(f"{path.name} is empty")
    return value


def _write_json(payload: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate grounded AI brief quality deterministically."
    )
    parser.add_argument("--top", type=Path, default=DEFAULT_TOP_PATH)
    parser.add_argument("--daily", type=Path, default=DEFAULT_DAILY_PATH)
    parser.add_argument("--brief", type=Path, default=DEFAULT_AI_BRIEF_PATH)
    parser.add_argument("--fallback", type=Path, default=DEFAULT_FALLBACK_PATH)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args(argv)
    try:
        artifact = run_ai_brief_evaluation_pipeline(
            args.top,
            args.daily,
            args.brief,
            args.fallback,
            args.metadata,
            args.output,
        )
    except AIBriefEvaluationInputError as exc:
        print(f"AI brief evaluation failed: {exc}")
        return 1
    print(
        f"Wrote AI brief evaluation to {args.output}; "
        f"status={artifact['status']}"
    )
    return 0


def cli() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    cli()
