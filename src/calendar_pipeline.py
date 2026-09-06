"""Build a deterministic resilient next-48-hours official economic calendar."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from src.calendar_validator import validate_economic_calendar_artifact
from src.data.freshness import enrich_artifact_freshness
from src.data.calendar_adapter import (
    BLS_CALENDAR_URL,
    BEAEconomicCalendarAdapter,
    BLSEconomicCalendarAdapter,
    CalendarSourceAccessError,
    CalendarSourcePayload,
    CalendarSourceValidationError,
    EconomicCalendarAdapter,
    ParsedCalendarEvent,
    content_hash,
    parse_bea_html_events,
    parse_ics_events,
)
from src.models.calendar_schema import (
    CalendarSourceAttempt,
    EconomicCalendar,
    EconomicCalendarEvent,
)


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
    fallback_adapter: Optional[EconomicCalendarAdapter] = None,
    now: Optional[datetime] = None,
    window_hours: int = 48,
) -> EconomicCalendar:
    if window_hours <= 0 or window_hours > 168:
        raise ValueError("window_hours must be between 1 and 168")
    generated_at = _as_utc(now or datetime.now(timezone.utc))
    window_end = generated_at + timedelta(hours=window_hours)
    primary = adapter or BLSEconomicCalendarAdapter()
    fallback = (
        fallback_adapter
        if adapter is not None
        else fallback_adapter or BEAEconomicCalendarAdapter()
    )
    results = [_load_source(primary, 1, generated_at)]
    if fallback is not None:
        results.append(_load_source(fallback, 2, generated_at))

    available = [result for result in results if result.status == "available"]
    accepted_by_source: Dict[str, int] = {result.source: 0 for result in results}
    events, conflict_warnings = _reconcile_events(
        available,
        generated_at,
        window_end,
        accepted_by_source,
    )
    source_attempts = [
        result.to_attempt(accepted_by_source.get(result.source, 0))
        for result in results
    ]
    warnings = [
        warning
        for result in results
        for warning in result.warnings
    ] + conflict_warnings

    primary_result = results[0]
    has_conflict = bool(conflict_warnings)
    if not available:
        status = "failed"
        failure_type = "all_sources_unavailable"
        retryable = any(result.retryable for result in results)
    elif primary_result.status != "available":
        status = "partial"
        failure_type = primary_result.failure_type
        retryable = primary_result.retryable
    elif has_conflict:
        status = "partial"
        failure_type = "source_conflict"
        retryable = False
    elif primary_result.parse_warnings:
        status = "partial"
        failure_type = "event_validation_error"
        retryable = False
    else:
        status = "complete"
        failure_type = None
        retryable = False

    if not events and available:
        warnings.append(
            f"No BLS releases found in the next {window_hours} hours; "
            "this does not cover Fed, Treasury, BEA, or private calendars."
        )

    if len(available) > 1:
        artifact_source = "official_us_economic_calendars"
        artifact_url = BLS_CALENDAR_URL
    elif available:
        artifact_source = available[0].source
        artifact_url = available[0].source_url
    else:
        artifact_source = "official_us_economic_calendars"
        artifact_url = BLS_CALENDAR_URL

    calendar = EconomicCalendar(
        generated_at=generated_at,
        window_start=generated_at,
        window_end=window_end,
        source=artifact_source,
        source_url=artifact_url,
        events=events,
        status=status,
        failure_type=failure_type,
        retryable=retryable,
        warnings=warnings,
        sources=source_attempts,
    )
    validate_economic_calendar_artifact(calendar.to_dict())
    return calendar


@dataclass(frozen=True)
class _SourceResult:
    source: str
    publisher: str
    source_url: str
    source_format: str
    priority: int
    status: str
    retrieved_at: Optional[datetime]
    events: Tuple[ParsedCalendarEvent, ...]
    parse_warnings: Tuple[str, ...]
    failure_type: Optional[str]
    retryable: bool
    error: Optional[str]

    @property
    def warnings(self) -> List[str]:
        values = [f"{self.source}: {warning}" for warning in self.parse_warnings]
        if self.error:
            values.append(f"{self.source}: {self.error}")
        return values

    def to_attempt(self, accepted_event_count: int) -> CalendarSourceAttempt:
        return CalendarSourceAttempt(
            source=self.source,
            publisher=self.publisher,
            source_url=self.source_url,
            priority=self.priority,
            source_format=self.source_format,
            status=self.status,
            retrieved_at=self.retrieved_at,
            failure_type=self.failure_type,
            retryable=self.retryable,
            error=self.error,
            parsed_event_count=len(self.events),
            accepted_event_count=accepted_event_count,
        )


def _load_source(
    adapter: EconomicCalendarAdapter,
    priority: int,
    now: datetime,
) -> _SourceResult:
    source = str(getattr(adapter, "source_name", f"calendar_source_{priority}"))
    publisher = str(getattr(adapter, "publisher", "unknown"))
    raw_url = str(getattr(adapter, "source_url", BLS_CALENDAR_URL))
    source_url = raw_url
    source_format = "bea_html" if priority == 2 else "ics"
    try:
        payload = adapter.fetch(now=now)
        source = payload.source
        publisher = payload.publisher
        source_url = payload.source_url
        source_format = payload.source_format
        if source_format == "ics":
            parsed_events, parse_warnings = parse_ics_events(payload.content)
        elif source_format == "bea_html":
            parsed_events, parse_warnings = parse_bea_html_events(
                payload.content,
                payload.source_url,
            )
        else:
            raise CalendarSourceValidationError(
                f"unsupported calendar source format: {source_format}"
            )
        if not parsed_events:
            raise CalendarSourceValidationError(
                f"{source} contained no valid calendar event records"
            )
        return _SourceResult(
            source=source,
            publisher=publisher,
            source_url=source_url,
            source_format=source_format,
            priority=priority,
            status="available",
            retrieved_at=payload.retrieved_at,
            events=tuple(parsed_events),
            parse_warnings=tuple(parse_warnings),
            failure_type=None,
            retryable=False,
            error=None,
        )
    except CalendarSourceAccessError as exc:
        return _failed_source_result(
            source, publisher, source_url, source_format, priority, "access", True, exc
        )
    except Exception as exc:
        return _failed_source_result(
            source,
            publisher,
            source_url,
            source_format,
            priority,
            "validation",
            False,
            exc,
        )


def _failed_source_result(
    source: str,
    publisher: str,
    source_url: str,
    source_format: str,
    priority: int,
    failure_kind: str,
    retryable: bool,
    error: Exception,
) -> _SourceResult:
    role = "primary" if priority == 1 else "fallback"
    return _SourceResult(
        source=source,
        publisher=publisher,
        source_url=source_url,
        source_format=source_format,
        priority=priority,
        status="unavailable" if failure_kind == "access" else "invalid",
        retrieved_at=None,
        events=(),
        parse_warnings=(),
        failure_type=f"{role}_source_{failure_kind}_error",
        retryable=retryable,
        error=_safe_error(error),
    )


def _reconcile_events(
    results: Sequence[_SourceResult],
    window_start: datetime,
    window_end: datetime,
    accepted_by_source: Dict[str, int],
) -> Tuple[List[EconomicCalendarEvent], List[str]]:
    grouped: Dict[str, List[Tuple[_SourceResult, ParsedCalendarEvent]]] = {}
    for result in results:
        for parsed in result.events:
            if window_start <= parsed.scheduled_at <= window_end:
                grouped.setdefault(_normalized_event_name(parsed.name), []).append(
                    (result, parsed)
                )

    output: List[EconomicCalendarEvent] = []
    warnings: List[str] = []
    for normalized_name, records in sorted(grouped.items()):
        schedules = {parsed.scheduled_at for _, parsed in records}
        sources = {result.source for result, _ in records}
        conflict = len(sources) > 1 and len(schedules) > 1
        conflict_group_id = _conflict_group_id(normalized_name) if conflict else None
        if conflict:
            warnings.append(
                "Official calendar source conflict preserved for "
                f"{records[0][1].name} ({conflict_group_id})."
            )
        by_schedule: Dict[datetime, List[Tuple[_SourceResult, ParsedCalendarEvent]]] = {}
        for record in records:
            by_schedule.setdefault(record[1].scheduled_at, []).append(record)
        for scheduled_at, matching in sorted(by_schedule.items()):
            matching.sort(key=lambda item: (item[0].priority, item[0].source))
            selected_result, selected_event = matching[0]
            for result, _ in matching:
                accepted_by_source[result.source] = accepted_by_source.get(result.source, 0) + 1
            provenance = [
                _provenance_record(result, parsed) for result, parsed in matching
            ]
            if conflict:
                verification_level = "official_conflict"
                score = 0.60
                label = "medium"
            elif len({result.source for result, _ in matching}) > 1:
                verification_level = "official_corroborated"
                score = 0.95
                label = "high"
            elif selected_result.priority == 1:
                verification_level = "official_primary"
                score = 0.95
                label = "high"
            else:
                verification_level = "official_fallback"
                score = 0.90
                label = "high"
            impact, topics, affected_assets = classify_event(selected_event.name)
            output.append(
                EconomicCalendarEvent(
                    event_id=_event_id(selected_event.name, scheduled_at),
                    event_type="economic_event",
                    name=selected_event.name,
                    scheduled_at=scheduled_at,
                    country="US",
                    impact=impact,
                    affected_assets=affected_assets,
                    topics=topics,
                    source=selected_result.source,
                    publisher=selected_result.publisher,
                    source_url=selected_event.source_url,
                    retrieved_at=selected_result.retrieved_at or window_start,
                    status="scheduled",
                    confidence_score=score,
                    confidence_label=label,
                    provider_event_id=selected_event.provider_event_id,
                    content_hash=content_hash(selected_event.raw_content),
                    verification_level=verification_level,
                    conflict_group_id=conflict_group_id,
                    provenance=provenance,
                )
            )
    output.sort(key=lambda item: (item.scheduled_at, item.event_id, item.source))
    return output, warnings


def _provenance_record(
    result: _SourceResult,
    event: ParsedCalendarEvent,
) -> Dict[str, object]:
    return {
        "source": result.source,
        "publisher": result.publisher,
        "source_url": event.source_url,
        "retrieved_at": _iso(result.retrieved_at),
        "scheduled_at": _iso(event.scheduled_at),
        "content_hash": content_hash(event.raw_content),
        "priority": result.priority,
    }


def _normalized_event_name(name: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", name.casefold()).split())


def _conflict_group_id(normalized_name: str) -> str:
    suffix = hashlib.sha256(normalized_name.encode("utf-8")).hexdigest()[:16]
    return f"cal_conflict_{suffix}"


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
    domain_payload = calendar.to_dict()
    validate_economic_calendar_artifact(domain_payload)
    payload = enrich_artifact_freshness(domain_payload)
    temporary_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
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


def _iso(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    return _as_utc(value).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    cli()
