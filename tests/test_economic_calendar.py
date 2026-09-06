from __future__ import annotations

import copy
from datetime import datetime, timezone

import pytest

from src.calendar_validator import (
    EconomicCalendarValidationError,
    validate_economic_calendar_artifact,
)
from src.calendar_pipeline import build_economic_calendar, classify_event
from src.data.calendar_adapter import (
    CalendarSourceAccessError,
    CalendarSourcePayload,
    parse_bea_html_events,
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

HTML_FIXTURE = """<!doctype html>
<html><head><title>Release Schedule</title></head><body>
<table>
<tr><th>Year 2026</th><th></th><th>Release</th><th></th></tr>
<tr>
  <td><div>August 20</div><small>08:30 AM</small></td>
  <td>News</td>
  <td>Consumer Price Index for July 2026</td>
  <td><a href="/news/2026/example">View</a></td>
</tr>
</table>
</body></html>
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


class FakeBEACalendarAdapter:
    source_name = "bea_release_schedule"
    publisher = "U.S. Bureau of Economic Analysis"
    source_url = "https://www.bea.gov/news/schedule/full"

    def __init__(self, content: str = HTML_FIXTURE) -> None:
        self.content = content

    def fetch(self, now=None) -> CalendarSourcePayload:
        return CalendarSourcePayload(
            content=self.content,
            retrieved_at=now,
            source=self.source_name,
            publisher=self.publisher,
            source_url=self.source_url,
            source_format="bea_html",
        )


class FailedBEACalendarAdapter(FakeBEACalendarAdapter):
    def fetch(self, now=None) -> CalendarSourcePayload:
        raise CalendarSourceAccessError("simulated fallback outage")


def test_ics_parser_unfolds_lines_and_normalizes_timezones() -> None:
    events, warnings = parse_ics_events(ICS_FIXTURE)

    assert warnings == []
    assert len(events) == 3
    assert events[0].scheduled_at.isoformat() == "2026-08-20T12:30:00+00:00"
    assert events[1].name == "Job Openings and Labor Turnover Survey,for July 2026"
    assert events[2].scheduled_at.isoformat() == "2026-08-30T04:00:00+00:00"


def test_html_parser_preserves_official_schedule_and_link() -> None:
    events, warnings = parse_bea_html_events(
        HTML_FIXTURE,
        "https://www.bea.gov/news/schedule/full",
    )

    assert warnings == []
    assert len(events) == 1
    assert events[0].scheduled_at.isoformat() == "2026-08-20T12:30:00+00:00"
    assert events[0].source_url == "https://www.bea.gov/news/2026/example"


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
    assert event["verification_level"] == "official_primary"
    assert [item["source"] for item in event["provenance"]] == [
        "bls_release_calendar"
    ]


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
    assert payload["failure_type"] == "all_sources_unavailable"
    assert payload["retryable"] is True
    assert payload["events"] == []
    assert "simulated provider outage" in payload["warnings"][0]
    assert payload["sources"][0]["failure_type"] == "primary_source_access_error"


def test_primary_failure_uses_official_fallback_with_provenance() -> None:
    payload = build_economic_calendar(
        adapter=FailedCalendarAdapter(),
        fallback_adapter=FakeBEACalendarAdapter(),
        now=datetime(2026, 8, 19, 12, tzinfo=timezone.utc),
    ).to_dict()

    assert payload["status"] == "partial"
    assert payload["failure_type"] == "primary_source_access_error"
    assert len(payload["events"]) == 1
    event = payload["events"][0]
    assert event["source"] == "bea_release_schedule"
    assert event["verification_level"] == "official_fallback"
    assert event["scheduled_at"] == "2026-08-20T12:30:00Z"
    assert event["retrieved_at"] == "2026-08-19T12:00:00Z"
    assert event["provenance"][0]["publisher"] == (
        "U.S. Bureau of Economic Analysis"
    )
    assert [item["status"] for item in payload["sources"]] == [
        "unavailable",
        "available",
    ]


def test_primary_success_remains_complete_when_fallback_is_unavailable() -> None:
    payload = build_economic_calendar(
        adapter=FakeCalendarAdapter(),
        fallback_adapter=FailedBEACalendarAdapter(),
        now=datetime(2026, 8, 19, 12, tzinfo=timezone.utc),
    ).to_dict()

    assert payload["status"] == "complete"
    assert payload["failure_type"] is None
    assert len(payload["events"]) == 1
    assert payload["events"][0]["verification_level"] == "official_primary"
    assert payload["sources"][1]["failure_type"] == "fallback_source_access_error"


def test_both_calendar_sources_unavailable_emit_no_events() -> None:
    payload = build_economic_calendar(
        adapter=FailedCalendarAdapter(),
        fallback_adapter=FailedBEACalendarAdapter(),
        now=datetime(2026, 8, 19, 12, tzinfo=timezone.utc),
    ).to_dict()

    assert payload["status"] == "failed"
    assert payload["failure_type"] == "all_sources_unavailable"
    assert payload["events"] == []
    assert {item["failure_type"] for item in payload["sources"]} == {
        "primary_source_access_error",
        "fallback_source_access_error",
    }


def test_agreeing_sources_merge_event_but_preserve_both_provenance_links() -> None:
    payload = build_economic_calendar(
        adapter=FakeCalendarAdapter(),
        fallback_adapter=FakeBEACalendarAdapter(),
        now=datetime(2026, 8, 19, 12, tzinfo=timezone.utc),
    ).to_dict()

    assert payload["status"] == "complete"
    assert len(payload["events"]) == 1
    event = payload["events"][0]
    assert event["verification_level"] == "official_corroborated"
    assert event["conflict_group_id"] is None
    assert {item["source"] for item in event["provenance"]} == {
        "bls_release_calendar",
        "bea_release_schedule",
    }


def test_conflicting_official_schedules_are_preserved_as_separate_records() -> None:
    conflicting_html = HTML_FIXTURE.replace("08:30 AM", "09:30 AM")
    payload = build_economic_calendar(
        adapter=FakeCalendarAdapter(),
        fallback_adapter=FakeBEACalendarAdapter(conflicting_html),
        now=datetime(2026, 8, 19, 12, tzinfo=timezone.utc),
    ).to_dict()

    assert payload["status"] == "partial"
    assert payload["failure_type"] == "source_conflict"
    assert len(payload["events"]) == 2
    assert {item["scheduled_at"] for item in payload["events"]} == {
        "2026-08-20T12:30:00Z",
        "2026-08-20T13:30:00Z",
    }
    assert {item["verification_level"] for item in payload["events"]} == {
        "official_conflict"
    }
    assert len({item["conflict_group_id"] for item in payload["events"]}) == 1
    assert {
        provenance["source"]
        for event in payload["events"]
        for provenance in event["provenance"]
    } == {"bls_release_calendar", "bea_release_schedule"}


def test_calendar_validator_rejects_lost_provenance() -> None:
    payload = build_economic_calendar(
        adapter=FakeCalendarAdapter(),
        fallback_adapter=FakeBEACalendarAdapter(),
        now=datetime(2026, 8, 19, 12, tzinfo=timezone.utc),
    ).to_dict()
    tampered = copy.deepcopy(payload)
    tampered["events"][0]["provenance"] = tampered["events"][0]["provenance"][:1]

    with pytest.raises(EconomicCalendarValidationError):
        validate_economic_calendar_artifact(tampered)


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
