"""CLI for Phase 6.3-C observable risk monitoring."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from src.data.freshness import enrich_artifact_freshness
from src.models.risk_schema import RiskMonitorArtifact
from src.risk.monitor import build_risk_monitor_artifact
from src.risk.validator import validate_risk_monitor_artifact


OUTPUT_DIRECTORY = Path(__file__).resolve().parents[1] / "output"
DEFAULT_EVIDENCE_PATH = OUTPUT_DIRECTORY / "evidence_bundle.json"
DEFAULT_SIGNALS_PATH = OUTPUT_DIRECTORY / "market_signals.json"
DEFAULT_REGIME_PATH = OUTPUT_DIRECTORY / "market_regime.json"
DEFAULT_OUTPUT_PATH = OUTPUT_DIRECTORY / "risk_monitor.json"


class RiskMonitorInputError(ValueError):
    """Raised when one of the three required artifacts cannot be read."""


def run_risk_monitor_pipeline(
    evidence_path: Path = DEFAULT_EVIDENCE_PATH,
    signals_path: Path = DEFAULT_SIGNALS_PATH,
    regime_path: Path = DEFAULT_REGIME_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> RiskMonitorArtifact:
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
    artifact = build_risk_monitor_artifact(
        evidence_bundle,
        market_signals,
        market_regime,
    )
    validate_risk_monitor_artifact(
        artifact.to_dict(),
        evidence_bundle,
        market_signals,
        market_regime,
    )
    _write_artifact(
        artifact,
        output_path,
        (evidence_bundle, market_signals, market_regime),
    )
    return artifact


def _read_artifact(
    path: Path,
    expected_type: str,
    label: str,
) -> Mapping[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RiskMonitorInputError(f"{label} not found: {path}") from exc
    except OSError as exc:
        raise RiskMonitorInputError(f"{label} cannot be read: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RiskMonitorInputError(f"{label} is invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise RiskMonitorInputError(f"{label} root must be an object")
    if payload.get("artifact_type") != expected_type:
        raise RiskMonitorInputError(f"Phase 6.3-C requires {label} as an input")
    return payload


def _write_artifact(
    artifact: RiskMonitorArtifact,
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
        description="Identify deterministic observable risk conditions."
    )
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE_PATH)
    parser.add_argument("--signals", type=Path, default=DEFAULT_SIGNALS_PATH)
    parser.add_argument("--regime", type=Path, default=DEFAULT_REGIME_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        artifact = run_risk_monitor_pipeline(
            args.evidence,
            args.signals,
            args.regime,
            args.output,
        )
    except (RiskMonitorInputError, ValueError) as exc:
        print(f"Risk monitoring failed: {exc}")
        return 1
    payload = artifact.to_dict()
    print(
        f"Wrote {payload['risk_count']} observable risk item(s) to "
        f"{args.output}; status={payload['status']}"
    )
    return 1 if payload["status"] == "unavailable" else 0


def cli() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    cli()
