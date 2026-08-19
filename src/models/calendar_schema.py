"""Schemas for the Phase 6.2-B economic calendar artifact."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class EconomicCalendarEvent:
    event_id: str
    event_type: str
    name: str
    scheduled_at: datetime
    country: str
    impact: str
    affected_assets: List[str]
    topics: List[str]
    source: str
    publisher: str
    source_url: str
    retrieved_at: datetime
    status: str
    confidence_score: float
    confidence_label: str
    provider_event_id: Optional[str]
    content_hash: str

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["scheduled_at"] = _iso_utc(self.scheduled_at)
        payload["retrieved_at"] = _iso_utc(self.retrieved_at)
        return payload


@dataclass(frozen=True)
class EconomicCalendar:
    generated_at: datetime
    window_start: datetime
    window_end: datetime
    source: str
    source_url: str
    events: List[EconomicCalendarEvent]
    status: str
    failure_type: Optional[str]
    retryable: bool
    warnings: List[str]
    schema_version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        generated_at = _as_utc(self.generated_at)
        return {
            "schema_version": self.schema_version,
            "artifact_type": "economic_calendar",
            "run_id": generated_at.strftime("run_%Y%m%dT%H%M%SZ_calendar"),
            "report_date": generated_at.date().isoformat(),
            "generated_at": _iso_utc(generated_at),
            "window_start": _iso_utc(self.window_start),
            "window_end": _iso_utc(self.window_end),
            "source": self.source,
            "source_url": self.source_url,
            "status": self.status,
            "failure_type": self.failure_type,
            "retryable": self.retryable,
            "warnings": list(self.warnings),
            "events": [event.to_dict() for event in self.events],
        }


def _iso_utc(value: datetime) -> str:
    return _as_utc(value).isoformat().replace("+00:00", "Z")


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
