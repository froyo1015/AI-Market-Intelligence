"""Run the Phase 2.1 AI Analyst Layer with a mock LLM adapter."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from src.ai.llm_adapter import LLMAdapter, MockLLMAdapter
from src.ai.prompt_builder import build_analyst_prompt


OUTPUT_DIRECTORY = Path(__file__).resolve().parents[1] / "output"
DEFAULT_SNAPSHOT_PATH = OUTPUT_DIRECTORY / "market_snapshot.json"
DEFAULT_CONTEXT_PATH = OUTPUT_DIRECTORY / "market_context.json"
DEFAULT_OUTPUT_PATH = OUTPUT_DIRECTORY / "ai_market_brief.md"
REQUIRED_HEADINGS = (
    "# 今日市場焦點",
    "## 美股",
    "## Crypto",
    "## 黃金",
    "## 外匯",
    "## 今日風險",
)


class AnalystError(ValueError):
    """Raised when analyst input or output is invalid."""


def load_json(path: Path) -> Dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AnalystError(f"input not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise AnalystError(f"input is not valid JSON ({path}): {exc}") from exc
    if not isinstance(payload, dict):
        raise AnalystError(f"input root must be a JSON object: {path}")
    return payload


def analyze(
    market_snapshot: Dict[str, Any],
    market_context: Dict[str, Any],
    adapter: Optional[LLMAdapter] = None,
) -> str:
    provider = adapter or MockLLMAdapter()
    prompt = build_analyst_prompt(market_snapshot, market_context)
    response = provider.generate(prompt)
    _validate_response(response)
    return response


def run_analyst(
    snapshot_path: Path = DEFAULT_SNAPSHOT_PATH,
    context_path: Path = DEFAULT_CONTEXT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    adapter: Optional[LLMAdapter] = None,
) -> str:
    market_snapshot = load_json(snapshot_path)
    market_context = load_json(context_path)
    response = analyze(market_snapshot, market_context, adapter)
    _write_output(response, output_path)
    return response


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a Chinese analyst brief with the Mock LLM adapter."
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=DEFAULT_SNAPSHOT_PATH,
        help=f"Market snapshot path (default: {DEFAULT_SNAPSHOT_PATH})",
    )
    parser.add_argument(
        "--context",
        type=Path,
        default=DEFAULT_CONTEXT_PATH,
        help=f"Market context path (default: {DEFAULT_CONTEXT_PATH})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"Output Markdown path (default: {DEFAULT_OUTPUT_PATH})",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    response = run_analyst(args.snapshot, args.context, args.output)
    print(f"Wrote Mock Analyst output ({len(response.splitlines())} lines) to {args.output}")
    return 0


def cli() -> None:
    raise SystemExit(main())


def _validate_response(response: str) -> None:
    if not isinstance(response, str) or not response.strip():
        raise AnalystError("LLM adapter returned an empty response")
    missing = [heading for heading in REQUIRED_HEADINGS if heading not in response]
    if missing:
        raise AnalystError(
            f"LLM adapter response is missing headings: {', '.join(missing)}"
        )


def _write_output(response: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(f"{output_path.suffix}.tmp")
    temporary_path.write_text(response, encoding="utf-8")
    temporary_path.replace(output_path)


if __name__ == "__main__":
    cli()

