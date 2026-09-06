"""Official BLS/BEA economic-calendar adapters and bounded parsers."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, time, timezone
from html.parser import HTMLParser
from typing import Callable, Dict, List, Optional, Protocol, Tuple
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


BLS_CALENDAR_URL = "https://www.bls.gov/schedule/news_release/bls.ics"
BLS_PUBLISHER = "U.S. Bureau of Labor Statistics"
BEA_CALENDAR_URL = "https://www.bea.gov/news/schedule/full"
BEA_PUBLISHER = "U.S. Bureau of Economic Analysis"
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
    source_format: str = "ics"


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
            source_format="ics",
        )


class BEAEconomicCalendarAdapter:
    """Fetch the official BEA release schedule as independent fallback."""

    source_name = "bea_release_schedule"
    publisher = BEA_PUBLISHER
    source_url = BEA_CALENDAR_URL

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
                "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.1",
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
                f"BEA calendar download failed: {_safe_error(exc)}"
            ) from exc
        if len(raw) > MAX_CALENDAR_BYTES:
            raise CalendarSourceValidationError(
                "BEA calendar exceeds size limit"
            )
        try:
            content = raw.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise CalendarSourceValidationError(
                "BEA calendar is not valid UTF-8"
            ) from exc
        normalized = content.casefold()
        if "<html" not in normalized or "release schedule" not in normalized:
            raise CalendarSourceValidationError(
                "BEA response is not a release calendar"
            )
        return CalendarSourcePayload(
            content=content,
            retrieved_at=retrieved_at,
            source=self.source_name,
            publisher=self.publisher,
            source_url=self.source_url,
            source_format="bea_html",
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


def parse_bea_html_events(
    content: str,
    source_url: str,
    default_timezone: ZoneInfo = BLS_TIMEZONE,
) -> Tuple[List[ParsedCalendarEvent], List[str]]:
    """Parse official BEA release-table rows without inferring missing times."""
    parser = _OfficialReleaseTableParser()
    try:
        parser.feed(content)
        parser.close()
    except Exception as exc:
        raise CalendarSourceValidationError(
            f"BEA calendar parsing failed: {_safe_error(exc)}"
        ) from exc

    year = _bea_calendar_year(parser.rows)
    events: List[ParsedCalendarEvent] = []
    warnings: List[str] = []
    for index, row in enumerate(parser.rows, start=1):
        if len(row.cells) < 3:
            continue
        raw_schedule = row.cells[0]
        name = " ".join(row.cells[2].split())
        if raw_schedule.casefold().startswith("year "):
            continue
        if not name or raw_schedule.casefold().startswith("to be announced"):
            continue
        try:
            scheduled_at = _parse_bea_schedule(
                raw_schedule,
                year,
                default_timezone,
            )
            event_url = urljoin(source_url, row.href or source_url)
            raw_content = " | ".join(row.cells)
            events.append(
                ParsedCalendarEvent(
                    name=name,
                    scheduled_at=scheduled_at,
                    provider_event_id=row.href,
                    source_url=event_url,
                    raw_content=raw_content,
                )
            )
        except Exception as exc:
            warnings.append(f"HTML row {index} skipped: {_safe_error(exc)}")
    return events, warnings


@dataclass(frozen=True)
class _HTMLCalendarRow:
    cells: List[str]
    href: Optional[str]


class _OfficialReleaseTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: List[_HTMLCalendarRow] = []
        self._in_row = False
        self._in_cell = False
        self._cells: List[str] = []
        self._cell_parts: List[str] = []
        self._href: Optional[str] = None

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        normalized = tag.casefold()
        if normalized == "tr":
            self._in_row = True
            self._cells = []
            self._href = None
        elif self._in_row and normalized in {"td", "th"}:
            self._in_cell = True
            self._cell_parts = []
        elif self._in_cell and normalized == "a":
            attributes = dict(attrs)
            if self._href is None and attributes.get("href"):
                self._href = attributes["href"]

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._cell_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.casefold()
        if self._in_row and normalized in {"td", "th"} and self._in_cell:
            self._cells.append(" ".join(" ".join(self._cell_parts).split()))
            self._in_cell = False
            self._cell_parts = []
        elif normalized == "tr" and self._in_row:
            self.rows.append(_HTMLCalendarRow(list(self._cells), self._href))
            self._in_row = False


def _bea_calendar_year(rows: List[_HTMLCalendarRow]) -> int:
    for row in rows:
        if row.cells:
            match = re.search(r"\bYear\s+(\d{4})\b", row.cells[0], re.IGNORECASE)
            if match:
                return int(match.group(1))
    raise CalendarSourceValidationError("BEA calendar year is missing")


def _parse_bea_schedule(
    raw_schedule: str,
    year: int,
    default_timezone: ZoneInfo,
) -> datetime:
    normalized = " ".join(raw_schedule.replace("\xa0", " ").split())
    match = re.fullmatch(
        r"([A-Za-z]+\s+\d{1,2})\s+(\d{1,2}:\d{2}\s+[AP]M)",
        normalized,
        re.IGNORECASE,
    )
    if not match:
        raise EconomicCalendarError(f"unrecognized BEA release schedule: {normalized}")
    try:
        parsed_date = datetime.strptime(f"{match.group(1)} {year}", "%B %d %Y")
        parsed_time = datetime.strptime(match.group(2).upper(), "%I:%M %p").time()
    except ValueError as exc:
        raise EconomicCalendarError(f"invalid BEA release schedule: {normalized}") from exc
    return datetime.combine(
        parsed_date.date(), parsed_time, default_timezone
    ).astimezone(timezone.utc)


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
