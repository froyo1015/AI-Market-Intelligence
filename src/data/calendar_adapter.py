"""Official BLS economic release calendar adapter and bounded ICS parser."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, time, timezone
from typing import Callable, Dict, List, Optional, Protocol, Tuple
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


BLS_CALENDAR_URL = "https://www.bls.gov/schedule/news_release/bls.ics"
BLS_PUBLISHER = "U.S. Bureau of Labor Statistics"
BLS_TIMEZONE = ZoneInfo("America/New_York")
MAX_CALENDAR_BYTES = 2_000_000


class EconomicCalendarError(RuntimeError):
    """Raised when the calendar source cannot produce a usable payload."""


class CalendarSourceAccessError(EconomicCalendarError):
    """Raised for retryable transport or source access failures."""


class CalendarSourceValidationError(EconomicCalendarError):
    """Raised when a retrieved source payload violates its contract."""


@dataclass(frozen=True)
class CalendarSourcePayload:
    content: str
    retrieved_at: datetime
    source: str
    publisher: str
    source_url: str


@dataclass(frozen=True)
class ParsedCalendarEvent:
    name: str
    scheduled_at: datetime
    provider_event_id: Optional[str]
    source_url: str
    raw_content: str


class EconomicCalendarAdapter(Protocol):
    source_name: str
    publisher: str
    source_url: str

    def fetch(self, now: Optional[datetime] = None) -> CalendarSourcePayload:
        """Fetch a calendar payload with source and retrieval metadata."""


class BLSEconomicCalendarAdapter:
    """Fetch the official BLS release calendar without an API key."""

    source_name = "bls_release_calendar"
    publisher = BLS_PUBLISHER
    source_url = BLS_CALENDAR_URL

    def __init__(
        self,
        timeout: int = 20,
        opener: Callable[..., object] = urlopen,
    ) -> None:
        self.timeout = timeout
        self._opener = opener

    def fetch(self, now: Optional[datetime] = None) -> CalendarSourcePayload:
        retrieved_at = _as_utc(now or datetime.now(timezone.utc))
        request = Request(
            self.source_url,
            headers={
                "Accept": "text/calendar,text/plain;q=0.9,*/*;q=0.1",
                "User-Agent": (
                    "AI-Market-Intelligence/0.2 "
                    "(+https://github.com/froyo1015/AI-Market-Intelligence)"
                ),
            },
        )
        try:
            with self._opener(request, timeout=self.timeout) as response:
                raw = response.read(MAX_CALENDAR_BYTES + 1)
        except Exception as exc:
            raise CalendarSourceAccessError(
                f"BLS calendar download failed: {_safe_error(exc)}"
            ) from exc
        if len(raw) > MAX_CALENDAR_BYTES:
            raise CalendarSourceValidationError("BLS calendar exceeds size limit")
        try:
            content = raw.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise CalendarSourceValidationError(
                "BLS calendar is not valid UTF-8"
            ) from exc
        if "BEGIN:VCALENDAR" not in content or "END:VCALENDAR" not in content:
            raise CalendarSourceValidationError(
                "BLS response is not an iCalendar document"
            )
        return CalendarSourcePayload(
            content=content,
            retrieved_at=retrieved_at,
            source=self.source_name,
            publisher=self.publisher,
            source_url=self.source_url,
        )


def parse_ics_events(
    content: str,
    default_timezone: ZoneInfo = BLS_TIMEZONE,
) -> Tuple[List[ParsedCalendarEvent], List[str]]:
    """Parse only the VEVENT fields needed by the frozen calendar contract."""
    lines = _unfold_lines(content)
    blocks: List[List[str]] = []
    current: Optional[List[str]] = None
    for line in lines:
        if line == "BEGIN:VEVENT":
            current = []
        elif line == "END:VEVENT" and current is not None:
            blocks.append(current)
            current = None
        elif current is not None:
            current.append(line)

    events: List[ParsedCalendarEvent] = []
    warnings: List[str] = []
    for index, block in enumerate(blocks, start=1):
        try:
            properties = _properties(block)
            summary = _unescape_ics(_required(properties, "SUMMARY")[1]).strip()
            if not summary:
                raise EconomicCalendarError("empty SUMMARY")
            dt_params, dt_value = _required(properties, "DTSTART")
            scheduled_at = _parse_datetime(dt_value, dt_params, default_timezone)
            uid = _optional_value(properties, "UID")
            event_url = _optional_value(properties, "URL") or BLS_CALENDAR_URL
            raw_content = "\n".join(["BEGIN:VEVENT", *block, "END:VEVENT"])
            events.append(
                ParsedCalendarEvent(
                    name=summary,
                    scheduled_at=scheduled_at,
                    provider_event_id=_unescape_ics(uid) if uid else None,
                    source_url=_unescape_ics(event_url),
                    raw_content=raw_content,
                )
            )
        except Exception as exc:
            warnings.append(f"VEVENT {index} skipped: {_safe_error(exc)}")
    return events, warnings


def _unfold_lines(content: str) -> List[str]:
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    unfolded: List[str] = []
    for line in normalized.split("\n"):
        if line.startswith((" ", "\t")) and unfolded:
            unfolded[-1] += line[1:]
        else:
            unfolded.append(line)
    return unfolded


def _properties(lines: List[str]) -> Dict[str, List[Tuple[Dict[str, str], str]]]:
    result: Dict[str, List[Tuple[Dict[str, str], str]]] = {}
    for line in lines:
        if ":" not in line:
            continue
        raw_key, value = line.split(":", 1)
        segments = raw_key.split(";")
        key = segments[0].upper()
        params: Dict[str, str] = {}
        for segment in segments[1:]:
            if "=" in segment:
                param_key, param_value = segment.split("=", 1)
                params[param_key.upper()] = param_value.strip('"')
        result.setdefault(key, []).append((params, value))
    return result


def _required(
    properties: Dict[str, List[Tuple[Dict[str, str], str]]],
    key: str,
) -> Tuple[Dict[str, str], str]:
    values = properties.get(key)
    if not values:
        raise EconomicCalendarError(f"missing {key}")
    return values[0]


def _optional_value(
    properties: Dict[str, List[Tuple[Dict[str, str], str]]],
    key: str,
) -> Optional[str]:
    values = properties.get(key)
    return values[0][1] if values else None


def _parse_datetime(
    value: str,
    params: Dict[str, str],
    default_timezone: ZoneInfo,
) -> datetime:
    if params.get("VALUE", "").upper() == "DATE" or len(value) == 8:
        parsed_date = datetime.strptime(value, "%Y%m%d").date()
        return datetime.combine(parsed_date, time.min, default_timezone).astimezone(
            timezone.utc
        )
    if value.endswith("Z"):
        return datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(
            tzinfo=timezone.utc
        )
    parsed = datetime.strptime(value, "%Y%m%dT%H%M%S")
    timezone_name = params.get("TZID")
    event_timezone = ZoneInfo(timezone_name) if timezone_name else default_timezone
    return parsed.replace(tzinfo=event_timezone).astimezone(timezone.utc)


def content_hash(raw_content: str) -> str:
    digest = hashlib.sha256(raw_content.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _unescape_ics(value: str) -> str:
    return (
        value.replace("\\n", "\n")
        .replace("\\N", "\n")
        .replace("\\,", ",")
        .replace("\\;", ";")
        .replace("\\\\", "\\")
    )


def _safe_error(exc: Exception) -> str:
    return " ".join(str(exc).split())[:240]


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
