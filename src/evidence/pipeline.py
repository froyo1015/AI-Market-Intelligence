"""CLI for the Phase 6.1 market observation and evidence pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

from src.data.freshness import enrich_artifact_freshness
from src.evidence.builder import (
    EvidenceBuildError,
    build_evidence_artifact,
    build_observation_artifact,
)
from src.evidence.validator import (
    validate_evidence_artifact,
    validate_observation_artifact,
)


OUTPUT_DIRECTORY = Path(__file__).resolve().parents[1] / "output"
DEFAULT_SNAPSHOT_PATH = OUTPUT_DIRECTORY / "market_snapshot.json"
DEFAULT_OBSERVATIONS_PATH = OUTPUT_DIRECTORY / "observations.json"
DEFAULT_EVIDENCE_PATH = OUTPUT_DIRECTORY / "evidence.json"
DEFAULT_MACRO_SNAPSHOT_PATH = OUTPUT_DIRECTORY / "macro_snapshot.json"


def load_snapshot(path: Path) -> Dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvidenceBuildError(f"market snapshot not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise EvidenceBuildError(f"market snapshot is invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise EvidenceBuildError("market snapshot root must be an object")
    return payload


def run_evidence_pipeline(
    snapshot_path: Path = DEFAULT_SNAPSHOT_PATH,
    observations_path: Path = DEFAULT_OBSERVATIONS_PATH,
    evidence_path: Path = DEFAULT_EVIDENCE_PATH,
    macro_snapshot_path: Optional[Path] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    snapshot = load_snapshot(snapshot_path)
    macro_snapshot = (
        load_snapshot(macro_snapshot_path)
        if macro_snapshot_path is not None
        else None
    )
    observations = build_observation_artifact(snapshot, macro_snapshot)
    evidence = build_evidence_artifact(observations)
    validate_observation_artifact(observations)
    validate_evidence_artifact(evidence, observations)
    freshness_inputs = tuple(
        item for item in (snapshot, macro_snapshot) if item is not None
    )
    _write_json(observations, observations_path, freshness_inputs)
    _write_json(evidence, evidence_path, (observations,))
    return observations, evidence


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate validated market observations and evidence JSON."
    )
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT_PATH)
    parser.add_argument(
        "--observations", type=Path, default=DEFAULT_OBSERVATIONS_PATH
    )
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE_PATH)
    parser.add_argument(
        "--macro-snapshot",
        type=Path,
        default=None,
        help=(
            "Optional macro snapshot to merge into observations; "
            f"normally generated at {DEFAULT_MACRO_SNAPSHOT_PATH}"
        ),
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    observations, evidence = run_evidence_pipeline(
        snapshot_path=args.snapshot,
        observations_path=args.observations,
        evidence_path=args.evidence,
        macro_snapshot_path=args.macro_snapshot,
    )
    print(
        f"Wrote {len(observations['observations'])} observations "
        f"to {args.observations}"
    )
    print(f"Wrote {len(evidence['evidence'])} evidence bundles to {args.evidence}")
    return 1 if evidence["status"] == "failed" else 0


def cli() -> None:
    raise SystemExit(main())


def _write_json(
    payload: Dict[str, Any],
    output_path: Path,
    supporting_artifacts: Sequence[Mapping[str, Any]] = (),
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(f"{output_path.suffix}.tmp")
    serialized = enrich_artifact_freshness(
        payload, supporting_artifacts=supporting_artifacts
    )
    temporary_path.write_text(
        json.dumps(serialized, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(output_path)


if __name__ == "__main__":
    cli()
