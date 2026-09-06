"""CLI for Phase 6.2-D evidence consolidation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

from src.consolidation.builder import build_consolidated_evidence_artifact
from src.consolidation.validator import validate_consolidated_evidence_artifact
from src.data.freshness import enrich_artifact_freshness
from src.models.evidence_bundle_schema import ConsolidatedEvidenceArtifact


OUTPUT_DIRECTORY = Path(__file__).resolve().parents[1] / "output"
DEFAULT_OBSERVATIONS_PATH = OUTPUT_DIRECTORY / "observations.json"
DEFAULT_EVIDENCE_PATH = OUTPUT_DIRECTORY / "evidence.json"
DEFAULT_CALENDAR_PATH = OUTPUT_DIRECTORY / "economic_calendar.json"
DEFAULT_NEWS_EVENTS_PATH = OUTPUT_DIRECTORY / "events.json"
DEFAULT_OUTPUT_PATH = OUTPUT_DIRECTORY / "evidence_bundle.json"


def run_consolidation_pipeline(
    observations_path: Path = DEFAULT_OBSERVATIONS_PATH,
    evidence_path: Path = DEFAULT_EVIDENCE_PATH,
    calendar_path: Path = DEFAULT_CALENDAR_PATH,
    news_events_path: Path = DEFAULT_NEWS_EVENTS_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> ConsolidatedEvidenceArtifact:
    paths = {
        "observations.json": observations_path,
        "evidence.json": evidence_path,
        "economic_calendar.json": calendar_path,
        "events.json": news_events_path,
    }
    payloads: Dict[str, Optional[Mapping[str, Any]]] = {}
    errors: Dict[str, str] = {}
    for artifact_name, path in paths.items():
        payload, error = read_optional_artifact(path)
        payloads[artifact_name] = payload
        if error:
            errors[artifact_name] = error
    artifact = build_consolidated_evidence_artifact(
        observations_artifact=payloads["observations.json"],
        evidence_artifact=payloads["evidence.json"],
        calendar_artifact=payloads["economic_calendar.json"],
        news_events_artifact=payloads["events.json"],
        input_errors=errors,
    )
    validate_consolidated_evidence_artifact(artifact.to_dict())
    freshness_inputs = tuple(
        payload for payload in payloads.values() if payload is not None
    )
    write_consolidated_evidence_artifact(
        artifact, output_path, freshness_inputs
    )
    return artifact


def read_optional_artifact(
    path: Path,
) -> Tuple[Optional[Mapping[str, Any]], Optional[str]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, f"Input artifact is missing: {path}"
    except OSError as exc:
        return None, f"Input artifact cannot be read: {path}: {exc}"
    except json.JSONDecodeError as exc:
        return None, f"Input artifact is invalid JSON: {path}: {exc}"
    if not isinstance(payload, dict):
        return None, f"Input artifact root must be an object: {path}"
    return payload, None


def write_consolidated_evidence_artifact(
    artifact: ConsolidatedEvidenceArtifact,
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
        description="Consolidate observations, events, and Evidence records."
    )
    parser.add_argument("--observations", type=Path, default=DEFAULT_OBSERVATIONS_PATH)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE_PATH)
    parser.add_argument("--calendar", type=Path, default=DEFAULT_CALENDAR_PATH)
    parser.add_argument("--news-events", type=Path, default=DEFAULT_NEWS_EVENTS_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    artifact = run_consolidation_pipeline(
        observations_path=args.observations,
        evidence_path=args.evidence,
        calendar_path=args.calendar,
        news_events_path=args.news_events,
        output_path=args.output,
    )
    payload = artifact.to_dict()
    print(
        f"Wrote {payload['bundle_count']} consolidated evidence bundle(s) "
        f"and {payload['rejection_count']} rejection(s) to {args.output}; "
        f"status={payload['status']}"
    )
    return 1 if payload["status"] == "unavailable" else 0


def cli() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    cli()
