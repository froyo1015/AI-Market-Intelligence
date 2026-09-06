"""CLI pipeline for Phase 7.2-A deterministic selection."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

from src.data.freshness import enrich_artifact_freshness
from src.top_intelligence.selector import build_top_intelligence_artifact
from src.top_intelligence.validator import validate_top_intelligence_artifact


OUTPUT_DIRECTORY = Path(__file__).resolve().parents[1] / "output"
DEFAULT_INPUT_PATH = OUTPUT_DIRECTORY / "daily_intelligence.json"
DEFAULT_OUTPUT_PATH = OUTPUT_DIRECTORY / "top_intelligence.json"


class TopIntelligenceInputError(ValueError):
    """Raised when the canonical structured input cannot be read."""


def run_top_intelligence_pipeline(
    input_path: Path = DEFAULT_INPUT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    daily = _load(input_path)
    domain = build_top_intelligence_artifact(daily, now=now).to_dict()
    artifact = enrich_artifact_freshness(domain, supporting_artifacts=[daily])
    validate_top_intelligence_artifact(artifact, daily)
    _write(artifact, output_path)
    return artifact


def _load(path: Path) -> Dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TopIntelligenceInputError(f"cannot read daily intelligence: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("artifact_type") != "daily_intelligence":
        raise TopIntelligenceInputError("selector requires daily_intelligence input")
    return payload


def _write(payload: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Select current Top Market Intelligence.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args(argv)
    try:
        artifact = run_top_intelligence_pipeline(args.input, args.output)
    except (TopIntelligenceInputError, ValueError) as exc:
        print(f"Top intelligence selection failed: {exc}")
        return 1
    print(f"Wrote {artifact['selected_count']} Top Intelligence item(s) to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
