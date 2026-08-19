from __future__ import annotations

from datetime import datetime, timezone

from src.calendar_pipeline import build_economic_calendar, classify_event
from src.data.calendar_adapter import (
    CalendarSourceAccessError,
    CalendarSourcePayload,
    parse_ics_events,
)


ICS_FIXTURE = r"""BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:cpi-20260820@bls.gov
DTSTART;TZID=America/New_York:20260820T083000
SUMMARY:Consumer Price Index for July 2026
URL:https://www.bls.gov/schedule/news_release/cpi.htm
END:VEVENT
BEGIN:VEVENT
UID:jolts-20260821@bls.gov
DTSTART:20260821T140000Z
SUMMARY:Job Openings and Labor Turnover Survey\,
 for July 2026
END:VEVENT
BEGIN:VEVENT
UID:outside-window@bls.gov
DTSTART;VALUE=DATE:20260830
SUMMARY:Productivity and Costs
END:VEVENT
END:VCALENDAR
"""


class FakeCalendarAdapter:
    source_name = "bls_release_calendar"
    publisher = "U.S. Bureau of Labor Statistics"
    source_url = "https://www.bls.gov/schedule/news_release/bls.ics"

    def fetch(self, now=None) -> CalendarSourcePayload:
        return CalendarSourcePayload(
            content=ICS_FIXTURE,
            retrieved_at=now,
            source=self.source_name,
            publisher=self.publisher,
            source_url=self.source_url,
        )


class FailedCalendarAdapter(FakeCalendarAdapter):
    def fetch(self, now=None) -> CalendarSourcePayload:
        raise CalendarSourceAccessError("simulated provider outage")


def test_ics_parser_unfolds_lines_and_normalizes_timezones() -> None:
    events, warnings = parse_ics_events(ICS_FIXTURE)

    assert warnings == []
    assert len(events) == 3
    assert events[0].scheduled_at.isoformat() == "2026-08-20T12:30:00+00:00"
    assert events[1].name == "Job Openings and Labor Turnover Survey,for July 2026"
    assert events[2].scheduled_at.isoformat() == "2026-08-30T04:00:00+00:00"


def test_calendar_pipeline_filters_next_48_hours_and_preserves_provenance() -> None:
    calendar = build_economic_calendar(
        adapter=FakeCalendarAdapter(),
        now=datetime(2026, 8, 19, 12, tzinfo=timezone.utc),
    )
    payload = calendar.to_dict()

    assert payload["status"] == "complete"
    assert payload["failure_type"] is None
    assert payload["retryable"] is False
    assert payload["window_end"] == "2026-08-21T12:00:00Z"
    assert len(payload["events"]) == 1
    event = payload["events"][0]
    assert event["event_type"] == "economic_event"
    assert event["name"] == "Consumer Price Index for July 2026"
    assert event["scheduled_at"] == "2026-08-20T12:30:00Z"
    assert event["country"] == "US"
    assert event["impact"] == "high"
    assert event["status"] == "scheduled"
    assert event["source"] == "bls_release_calendar"
    assert event["publisher"] == "U.S. Bureau of Labor Statistics"
    assert event["source_url"].startswith("https://www.bls.gov/")
    assert event["content_hash"].startswith("sha256:")
    assert "GOLD" in event["affected_assets"]


def test_calendar_ids_are_deterministic() -> None:
    kwargs = {
        "adapter": FakeCalendarAdapter(),
        "now": datetime(2026, 8, 19, 12, tzinfo=timezone.utc),
    }
    first = build_economic_calendar(**kwargs).to_dict()
    second = build_economic_calendar(**kwargs).to_dict()

    assert first["events"][0]["event_id"] == second["events"][0]["event_id"]
    assert first["events"][0]["content_hash"] == second["events"][0]["content_hash"]


def test_provider_failure_produces_failed_artifact_without_fake_events() -> None:
    payload = build_economic_calendar(
        adapter=FailedCalendarAdapter(),
        now=datetime(2026, 8, 19, 12, tzinfo=timezone.utc),
    ).to_dict()

    assert payload["status"] == "failed"
    assert payload["failure_type"] == "source_access_error"
    assert payload["retryable"] is True
    assert payload["events"] == []
    assert "simulated provider outage" in payload["warnings"][0]


def test_malformed_event_is_isolated_and_marks_artifact_partial() -> None:
    malformed = ICS_FIXTURE.replace(
        "SUMMARY:Productivity and Costs", "DESCRIPTION:missing summary"
    )

    class PartlyMalformedAdapter(FakeCalendarAdapter):
        def fetch(self, now=None) -> CalendarSourcePayload:
            payload = super().fetch(now)
            return CalendarSourcePayload(
                content=malformed,
                retrieved_at=payload.retrieved_at,
                source=payload.source,
                publisher=payload.publisher,
                source_url=payload.source_url,
            )

    payload = build_economic_calendar(
        adapter=PartlyMalformedAdapter(),
        now=datetime(2026, 8, 19, 12, tzinfo=timezone.utc),
        window_hours=168,
    ).to_dict()

    assert payload["status"] == "partial"
    assert payload["failure_type"] == "event_validation_error"
    assert payload["retryable"] is False
    assert len(payload["events"]) == 2
    assert "missing SUMMARY" in payload["warnings"][0]


def test_classification_is_rule_based_not_predictive() -> None:
    assert classify_event("Employment Situation for July 2026") == (
        "high",
        ["labor_market"],
        ["SPY", "QQQ", "GOLD", "DXY", "US10Y", "VIX"],
    )
    assert classify_event("Employment Cost Index")[1] == ["labor_market"]
    assert classify_event("Regional employment statistics")[0] == "low"
