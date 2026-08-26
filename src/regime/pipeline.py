"""CLI for Phase 6.3-B current-condition market regime classification."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from src.models.regime_schema import MarketRegimeArtifact
from src.regime.classifier import build_market_regime_artifact
from src.regime.validator import validate_market_regime_artifact


OUTPUT_DIRECTORY = Path(__file__).resolve().parents[1] / "output"
DEFAULT_EVIDENCE_PATH = OUTPUT_DIRECTORY / "evidence_bundle.json"
DEFAULT_SIGNALS_PATH = OUTPUT_DIRECTORY / "market_signals.json"
DEFAULT_OUTPUT_PATH = OUTPUT_DIRECTORY / "market_regime.json"


class MarketRegimeInputError(ValueError):
    """Raised when either required regime input cannot be read."""


def run_market_regime_pipeline(
    evidence_path: Path = DEFAULT_EVIDENCE_PATH,
    signals_path: Path = DEFAULT_SIGNALS_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> MarketRegimeArtifact:
    evidence_bundle = _read_artifact(
        evidence_path,
        expected_type="evidence_bundle",
        label="evidence_bundle.json",
    )
    market_signals = _read_artifact(
        signals_path,
        expected_type="market_signals",
        label="market_signals.json",
    )
    artifact = build_market_regime_artifact(evidence_bundle, market_signals)
    validate_market_regime_artifact(
        artifact.to_dict(),
        evidence_bundle,
        market_signals,
    )
    _write_artifact(artifact, output_path)
    return artifact


def _read_artifact(
    path: Path,
    expected_type: str,
    label: str,
) -> Mapping[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise MarketRegimeInputError(f"{label} not found: {path}") from exc
    except OSError as exc:
        raise MarketRegimeInputError(f"{label} cannot be read: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise MarketRegimeInputError(f"{label} is invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise MarketRegimeInputError(f"{label} root must be an object")
    if payload.get("artifact_type") != expected_type:
        raise MarketRegimeInputError(
            f"Phase 6.3-B requires {label} as an input"
        )
    return payload


def _write_artifact(
    artifact: MarketRegimeArtifact,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(f"{output_path.suffix}.tmp")
    temporary_path.write_text(
        json.dumps(artifact.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(output_path)
    return output_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Classify deterministic current observed market conditions."
    )
    parser.add_argument(
        "--evidence",
        type=Path,
        default=DEFAULT_EVIDENCE_PATH,
    )
    parser.add_argument(
        "--signals",
        type=Path,
        default=DEFAULT_SIGNALS_PATH,
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        artifact = run_market_regime_pipeline(
            args.evidence,
            args.signals,
            args.output,
        )
    except (MarketRegimeInputError, ValueError) as exc:
        print(f"Market regime classification failed: {exc}")
        return 1
    payload = artifact.to_dict()
    print(
        f"Wrote current-condition classification {payload['classification']} "
        f"to {args.output}; status={payload['status']}"
    )
    return 1 if payload["status"] == "unavailable" else 0


def cli() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    cli()
