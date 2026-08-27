"""CLI for Phase 6.4-A structured intelligence composition."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from src.intelligence.composer import build_daily_intelligence_artifact
from src.intelligence.validator import validate_daily_intelligence_artifact
from src.models.intelligence_schema import DailyIntelligenceArtifact


OUTPUT_DIRECTORY = Path(__file__).resolve().parents[1] / "output"
DEFAULT_EVIDENCE_PATH = OUTPUT_DIRECTORY / "evidence_bundle.json"
DEFAULT_SIGNALS_PATH = OUTPUT_DIRECTORY / "market_signals.json"
DEFAULT_REGIME_PATH = OUTPUT_DIRECTORY / "market_regime.json"
DEFAULT_RISK_PATH = OUTPUT_DIRECTORY / "risk_monitor.json"
DEFAULT_OUTPUT_PATH = OUTPUT_DIRECTORY / "daily_intelligence.json"


class DailyIntelligenceInputError(ValueError):
    """Raised when one of the four required artifacts cannot be read."""


def run_daily_intelligence_pipeline(
    evidence_path: Path = DEFAULT_EVIDENCE_PATH,
    signals_path: Path = DEFAULT_SIGNALS_PATH,
    regime_path: Path = DEFAULT_REGIME_PATH,
    risk_path: Path = DEFAULT_RISK_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> DailyIntelligenceArtifact:
    evidence_bundle = _read_artifact(
        evidence_path,
        "evidence_bundle",
        "evidence_bundle.json",
    )
    market_signals = _read_artifact(
        signals_path,
        "market_signals",
        "market_signals.json",
    )
    market_regime = _read_artifact(
        regime_path,
        "market_regime",
        "market_regime.json",
    )
    risk_monitor = _read_artifact(
        risk_path,
        "risk_monitor",
        "risk_monitor.json",
    )
    artifact = build_daily_intelligence_artifact(
        evidence_bundle,
        market_signals,
        market_regime,
        risk_monitor,
    )
    validate_daily_intelligence_artifact(
        artifact.to_dict(),
        evidence_bundle,
        market_signals,
        market_regime,
        risk_monitor,
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
        raise DailyIntelligenceInputError(f"{label} not found: {path}") from exc
    except OSError as exc:
        raise DailyIntelligenceInputError(f"{label} cannot be read: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise DailyIntelligenceInputError(f"{label} is invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise DailyIntelligenceInputError(f"{label} root must be an object")
    if payload.get("artifact_type") != expected_type:
        raise DailyIntelligenceInputError(
            f"Phase 6.4-A requires {label} as an input"
        )
    return payload


def _write_artifact(
    artifact: DailyIntelligenceArtifact,
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
        description="Assemble validated structured daily intelligence."
    )
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE_PATH)
    parser.add_argument("--signals", type=Path, default=DEFAULT_SIGNALS_PATH)
    parser.add_argument("--regime", type=Path, default=DEFAULT_REGIME_PATH)
    parser.add_argument("--risk", type=Path, default=DEFAULT_RISK_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        artifact = run_daily_intelligence_pipeline(
            args.evidence,
            args.signals,
            args.regime,
            args.risk,
            args.output,
        )
    except (DailyIntelligenceInputError, ValueError) as exc:
        print(f"Daily intelligence composition failed: {exc}")
        return 1
    payload = artifact.to_dict()
    print(
        f"Wrote {payload['object_counts']['total']} validated intelligence "
        f"object(s) to {args.output}; status={payload['status']}"
    )
    return 1 if payload["status"] == "unavailable" else 0


def cli() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    cli()
