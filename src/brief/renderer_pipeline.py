"""CLI pipeline for Phase 6.4-B1 deterministic brief rendering."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from src.brief.intelligence_renderer import render_daily_market_brief
from src.brief.renderer_validator import (
    BriefRendererValidationError,
    validate_rendered_brief,
)
from src.models.brief_renderer_schema import DeterministicBrief
from src.top_intelligence.validator import validate_top_intelligence_artifact


OUTPUT_DIRECTORY = Path(__file__).resolve().parents[1] / "output"
DEFAULT_INPUT_PATH = OUTPUT_DIRECTORY / "daily_intelligence.json"
DEFAULT_TOP_INPUT_PATH = OUTPUT_DIRECTORY / "top_intelligence.json"
DEFAULT_OUTPUT_PATH = OUTPUT_DIRECTORY / "daily_market_brief.md"


class BriefRendererInputError(ValueError):
    """Raised when daily_intelligence.json cannot be read."""


def run_renderer_pipeline(
    input_path: Path = DEFAULT_INPUT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    top_input_path: Optional[Path] = None,
) -> DeterministicBrief:
    artifact = load_daily_intelligence(input_path)
    top_intelligence = None
    if top_input_path is not None:
        top_intelligence = load_top_intelligence(top_input_path)
        validate_top_intelligence_artifact(top_intelligence, artifact)
    result = render_daily_market_brief(artifact, top_intelligence)
    validate_rendered_brief(result.markdown, artifact, top_intelligence)
    write_rendered_brief(result.markdown, output_path)
    return result


def load_top_intelligence(input_path: Path) -> Dict[str, Any]:
    payload = _load_json_object(input_path, "top intelligence")
    if payload.get("artifact_type") != "top_intelligence":
        raise BriefRendererInputError("renderer requires top_intelligence input")
    return payload


def load_daily_intelligence(input_path: Path) -> Dict[str, Any]:
    return _load_json_object(input_path, "intelligence")


def _load_json_object(input_path: Path, label: str) -> Dict[str, Any]:
    try:
        payload = json.loads(input_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise BriefRendererInputError(f"{label} input not found: {input_path}") from exc
    except OSError as exc:
        raise BriefRendererInputError(f"{label} input cannot be read: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise BriefRendererInputError(f"{label} input is invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise BriefRendererInputError(f"{label} input root must be an object")
    return payload


def write_rendered_brief(markdown: str, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(f"{output_path.suffix}.tmp")
    temporary_path.write_text(markdown, encoding="utf-8")
    temporary_path.replace(output_path)
    return output_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render validated structured intelligence as Markdown."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--top-input", type=Path, default=DEFAULT_TOP_INPUT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = run_renderer_pipeline(args.input, args.output, args.top_input)
    except (BriefRendererInputError, BriefRendererValidationError) as exc:
        print(f"Deterministic brief rendering failed: {exc}")
        return 1
    print(
        f"Wrote {len(result.markdown.splitlines())} Markdown lines to "
        f"{args.output}; source_status={result.source_status}"
    )
    return 0


def cli() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    cli()
