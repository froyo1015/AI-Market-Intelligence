"""Build a deterministic next-48-hours official economic calendar."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Sequence

from src.data.calendar_adapter import (
    BLS_CALENDAR_URL,
    BLSEconomicCalendarAdapter,
    CalendarSourceAccessError,
    EconomicCalendarAdapter,
    content_hash,
    parse_ics_events,
)
from src.models.calendar_schema import EconomicCalendar, EconomicCalendarEvent


DEFAULT_OUTPUT_PATH = (
    Path(__file__).resolve().parent / "output" / "economic_calendar.json"
)

HIGH_IMPACT_RULES = (
    "consumer price index",
    "employment situation",
    "producer price index",
    "employment cost index",
)
MEDIUM_IMPACT_RULES = (
    "job openings and labor turnover",
    "import and export price indexes",
    "productivity and costs",
    "real earnings",
)


def build_economic_calendar(
    adapter: Optional[EconomicCalendarAdapter] = None,
    now: Optional[datetime] = None,
    window_hours: int = 48,
) -> EconomicCalendar:
    if window_hours <= 0 or window_hours > 168:
        raise ValueError("window_hours must be between 1 and 168")
    generated_at = _as_utc(now or datetime.now(timezone.utc))
    window_end = generated_at + timedelta(hours=window_hours)
    provider = adapter or BLSEconomicCalendarAdapter()
    source = getattr(provider, "source_name", "economic_calendar")
    source_url = getattr(provider, "source_url", BLS_CALENDAR_URL)

    try:
        payload = provider.fetch(now=generated_at)
        parsed_events, parse_warnings = parse_ics_events(payload.content)
    except CalendarSourceAccessError as exc:
        return EconomicCalendar(
            generated_at=generated_at,
            window_start=generated_at,
            window_end=window_end,
            source=source,
            source_url=source_url,
            events=[],
            status="failed",
            failure_type="source_access_error",
            retryable=True,
            warnings=[f"Economic calendar unavailable: {_safe_error(exc)}"],
        )
    except Exception as exc:
        return EconomicCalendar(
            generated_at=generated_at,
            window_start=generated_at,
            window_end=window_end,
            source=source,
            source_url=source_url,
            events=[],
            status="failed",
            failure_type="source_validation_error",
            retryable=False,
            warnings=[f"Economic calendar invalid: {_safe_error(exc)}"],
        )

    events = []
    for parsed in parsed_events:
        if not generated_at <= parsed.scheduled_at <= window_end:
            continue
        impact, topics, affected_assets = classify_event(parsed.name)
        events.append(
            EconomicCalendarEvent(
                event_id=_event_id(parsed.name, parsed.scheduled_at),
                event_type="economic_event",
                name=parsed.name,
                scheduled_at=parsed.scheduled_at,
                country="US",
                impact=impact,
                affected_assets=affected_assets,
                topics=topics,
                source=payload.source,
                publisher=payload.publisher,
                source_url=parsed.source_url,
                retrieved_at=payload.retrieved_at,
                status="scheduled",
                confidence_score=0.95,
                confidence_label="high",
                provider_event_id=parsed.provider_event_id,
                content_hash=content_hash(parsed.raw_content),
            )
        )
    events.sort(key=lambda item: (item.scheduled_at, item.event_id))

    warnings = list(parse_warnings)
    if not events:
        warnings.append(
            f"No BLS releases found in the next {window_hours} hours; "
            "this does not cover Fed, Treasury, BEA, or private calendars."
        )
    status = "partial" if parse_warnings and parsed_events else "complete"
    failure_type = "event_validation_error" if parse_warnings else None
    if not parsed_events:
        status = "failed"
        failure_type = "source_validation_error"
        warnings.append("BLS calendar contained no valid VEVENT records.")
    return EconomicCalendar(
        generated_at=generated_at,
        window_start=generated_at,
        window_end=window_end,
        source=payload.source,
        source_url=payload.source_url,
        events=events,
        status=status,
        failure_type=failure_type,
        retryable=False,
        warnings=warnings,
    )


def classify_event(name: str) -> tuple[str, list[str], list[str]]:
    normalized = " ".join(name.casefold().split())
    if any(rule in normalized for rule in HIGH_IMPACT_RULES):
        impact = "high"
    elif any(rule in normalized for rule in MEDIUM_IMPACT_RULES):
        impact = "medium"
    else:
        impact = "low"

    if any(
        term in normalized
        for term in ("employment", "job openings", "unemployment", "payroll")
    ):
        topics = ["labor_market"]
        assets = ["SPY", "QQQ", "GOLD", "DXY", "US10Y", "VIX"]
    elif any(term in normalized for term in ("price", "earnings", "cost")):
        topics = ["inflation"]
        assets = ["SPY", "QQQ", "GOLD", "DXY", "US10Y", "EURUSD", "USDJPY"]
    else:
        topics = ["us_economy"]
        assets = ["SPY", "QQQ", "DXY", "US10Y"]
    return impact, topics, assets


def write_economic_calendar(
    calendar: EconomicCalendar,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(f"{output_path.suffix}.tmp")
    temporary_path.write_text(
        json.dumps(calendar.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(output_path)
    return output_path


def run_calendar_pipeline(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    window_hours: int = 48,
) -> EconomicCalendar:
    calendar = build_economic_calendar(window_hours=window_hours)
    write_economic_calendar(calendar, output_path)
    return calendar


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate the Phase 6.2-B official economic calendar."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--window-hours", type=int, default=48)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    calendar = run_calendar_pipeline(args.output, args.window_hours)
    payload = calendar.to_dict()
    print(
        f"Wrote {len(calendar.events)} scheduled events to {args.output}; "
        f"status={payload['status']}"
    )
    return 1 if payload["status"] == "failed" else 0


def cli() -> None:
    raise SystemExit(main())


def _event_id(name: str, scheduled_at: datetime) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.casefold()).strip("_")[:36]
    canonical = f"{name.casefold()}|{_as_utc(scheduled_at).isoformat()}"
    suffix = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:10]
    return f"evt_{scheduled_at:%Y%m%d}_{slug}_{suffix}"


def _safe_error(exc: Exception) -> str:
    return f"{type(exc).__name__}: {' '.join(str(exc).split())}"[:300]


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


if __name__ == "__main__":
    cli()
