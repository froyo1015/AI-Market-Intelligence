"""CLI for Phase 6.3-A cross-asset relationship evaluation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from src.data.freshness import enrich_artifact_freshness
from src.models.cross_asset_schema import MarketSignalsArtifact
from src.signals.engine import build_market_signals_artifact
from src.signals.validator import validate_market_signals_artifact


OUTPUT_DIRECTORY = Path(__file__).resolve().parents[1] / "output"
DEFAULT_INPUT_PATH = OUTPUT_DIRECTORY / "evidence_bundle.json"
DEFAULT_OUTPUT_PATH = OUTPUT_DIRECTORY / "market_signals.json"


class MarketSignalsInputError(ValueError):
    """Raised when the sole evidence bundle input cannot be read."""


def run_market_signals_pipeline(
    input_path: Path = DEFAULT_INPUT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> MarketSignalsArtifact:
    evidence_bundle = read_evidence_bundle(input_path)
    artifact = build_market_signals_artifact(evidence_bundle)
    validate_market_signals_artifact(artifact.to_dict(), evidence_bundle)
    write_market_signals_artifact(artifact, output_path, (evidence_bundle,))
    return artifact


def read_evidence_bundle(path: Path = DEFAULT_INPUT_PATH) -> Mapping[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise MarketSignalsInputError(f"evidence bundle not found: {path}") from exc
    except OSError as exc:
        raise MarketSignalsInputError(f"evidence bundle cannot be read: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise MarketSignalsInputError(f"evidence bundle is invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise MarketSignalsInputError("evidence bundle root must be an object")
    if payload.get("artifact_type") != "evidence_bundle":
        raise MarketSignalsInputError(
            "Phase 6.3-A accepts only evidence_bundle.json input"
        )
    return payload


def write_market_signals_artifact(
    artifact: MarketSignalsArtifact,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    supporting_artifacts: Sequence[Mapping[str, Any]] = (),
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(f"{output_path.suffix}.tmp")
    payload = enrich_artifact_freshness(
        artifact.to_dict(), supporting_artifacts=supporting_artifacts
    )
    temporary_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(output_path)
    return output_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate deterministic observed cross-asset relationships."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        artifact = run_market_signals_pipeline(args.input, args.output)
    except (MarketSignalsInputError, ValueError) as exc:
        print(f"Cross-asset relationship evaluation failed: {exc}")
        return 1
    payload = artifact.to_dict()
    print(
        f"Wrote {payload['signal_count']} relationship evaluation(s), "
        f"observed={payload['observed_count']}, to {args.output}; "
        f"status={payload['status']}"
    )
    return 1 if payload["status"] == "unavailable" else 0


def cli() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    cli()
