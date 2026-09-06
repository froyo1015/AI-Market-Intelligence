"""Generate canonical events.json from a validated news_items.json artifact."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from src.data.freshness import enrich_artifact_freshness
from src.events.normalizer import normalize_news_items
from src.events.validator import (
    NewsNormalizationValidationError,
    validate_events_artifact,
    validate_news_items_artifact,
)
from src.models.event_schema import EventsArtifact


DEFAULT_INPUT_PATH = Path(__file__).resolve().parents[1] / "output" / "news_items.json"
DEFAULT_OUTPUT_PATH = Path(__file__).resolve().parents[1] / "output" / "events.json"


def build_events_artifact(
    news_artifact: Mapping[str, Any],
    now: Optional[datetime] = None,
) -> EventsArtifact:
    validate_news_items_artifact(news_artifact)
    generated_at = _iso_utc(now or datetime.now(timezone.utc))
    input_status = str(news_artifact["status"])
    inherited_warnings = [
        f"News input: {warning}" for warning in news_artifact.get("warnings", [])
    ]
    if input_status == "failed":
        artifact = EventsArtifact(
            run_id=str(news_artifact["run_id"]),
            report_date=str(news_artifact["report_date"]),
            generated_at=generated_at,
            status="failed",
            warnings=[*inherited_warnings, "News normalization skipped: input artifact failed."],
            input_artifact="news_items.json",
            input_run_id=str(news_artifact["run_id"]),
            events=[],
            normalization_rejections=[],
        )
    else:
        events, rejections = normalize_news_items(
            news_artifact["items"],
            generated_at,
        )
        warning_list = list(inherited_warnings)
        if rejections:
            warning_list.append(
                f"{len(rejections)} accepted NewsItem(s) could not be normalized "
                "by the frozen deterministic rules."
            )
        if not news_artifact["items"]:
            warning_list.append("No accepted NewsItems were available to normalize.")
        if news_artifact["items"] and not events:
            status = "failed"
        elif input_status == "partial" or rejections:
            status = "partial"
        else:
            status = "complete"
        artifact = EventsArtifact(
            run_id=str(news_artifact["run_id"]),
            report_date=str(news_artifact["report_date"]),
            generated_at=generated_at,
            status=status,
            warnings=warning_list,
            input_artifact="news_items.json",
            input_run_id=str(news_artifact["run_id"]),
            events=events,
            normalization_rejections=rejections,
        )
    validate_events_artifact(artifact.to_dict(), news_artifact)
    return artifact


def read_news_items_artifact(input_path: Path = DEFAULT_INPUT_PATH) -> Mapping[str, Any]:
    try:
        payload = json.loads(input_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise NewsNormalizationValidationError(
            f"Unable to read valid news artifact: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise NewsNormalizationValidationError("news artifact root must be an object")
    return payload


def write_events_artifact(
    artifact: EventsArtifact,
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


def run_events_pipeline(
    input_path: Path = DEFAULT_INPUT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> EventsArtifact:
    news_artifact = read_news_items_artifact(input_path)
    artifact = build_events_artifact(news_artifact)
    write_events_artifact(artifact, output_path, (news_artifact,))
    return artifact


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Normalize validated NewsItems into Phase 6.2-C2 events."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        artifact = run_events_pipeline(args.input, args.output)
    except NewsNormalizationValidationError as exc:
        print(f"News normalization failed contract validation: {exc}")
        return 1
    payload = artifact.to_dict()
    print(
        f"Wrote {payload['event_count']} normalized event(s) and "
        f"{payload['normalization_rejection_count']} rejection(s) to "
        f"{args.output}; status={payload['status']}"
    )
    return 1 if payload["status"] == "failed" else 0


def cli() -> None:
    raise SystemExit(main())


def _iso_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    cli()
