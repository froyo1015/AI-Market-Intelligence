"""Tier-1 Federal Reserve RSS adapter for Phase 6.2-C1 ingestion."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, List, Optional, Protocol, Tuple
from urllib.request import Request, urlopen
from xml.etree import ElementTree


FEDERAL_RESERVE_RSS_URL = "https://www.federalreserve.gov/feeds/press_all.xml"
FEDERAL_RESERVE_PUBLISHER = "Board of Governors of the Federal Reserve System"
MAX_NEWS_FEED_BYTES = 2_000_000


class NewsSourceError(RuntimeError):
    """Base error for a news source that cannot satisfy its contract."""


class NewsSourceAccessError(NewsSourceError):
    """Retryable network or source-access failure."""


class NewsSourceValidationError(NewsSourceError):
    """Non-retryable malformed or unexpected source response."""


@dataclass(frozen=True)
class NewsSourcePayload:
    content: str
    retrieved_at: datetime
    source: str
    publisher: str
    source_url: str
    source_type: str
    quality_tier: int


@dataclass(frozen=True)
class RawNewsItem:
    provider_item_id: Optional[str]
    title: Optional[str]
    description: Optional[str]
    link: Optional[str]
    published_at: Optional[str]


class NewsSourceAdapter(Protocol):
    source_name: str
    publisher: str
    source_url: str
    source_type: str
    quality_tier: int

    def fetch(self, now: Optional[datetime] = None) -> NewsSourcePayload:
        """Fetch one source payload without interpreting its market meaning."""


class FederalReserveNewsAdapter:
    """Fetch the Federal Reserve Board's official all-press-releases RSS."""

    source_name = "federal_reserve_press_releases"
    publisher = FEDERAL_RESERVE_PUBLISHER
    source_url = FEDERAL_RESERVE_RSS_URL
    source_type = "official"
    quality_tier = 1

    def __init__(
        self,
        timeout: int = 20,
        opener: Callable[..., object] = urlopen,
    ) -> None:
        self.timeout = timeout
        self._opener = opener

    def fetch(self, now: Optional[datetime] = None) -> NewsSourcePayload:
        retrieved_at = _as_utc(now or datetime.now(timezone.utc))
        request = Request(
            self.source_url,
            headers={
                "Accept": "application/rss+xml,application/xml,text/xml;q=0.9",
                "User-Agent": (
                    "AI-Market-Intelligence/0.2 "
                    "(+https://github.com/froyo1015/AI-Market-Intelligence)"
                ),
            },
        )
        try:
            with self._opener(request, timeout=self.timeout) as response:
                raw = response.read(MAX_NEWS_FEED_BYTES + 1)
        except Exception as exc:
            raise NewsSourceAccessError(
                f"Federal Reserve RSS download failed: {_safe_error(exc)}"
            ) from exc
        if len(raw) > MAX_NEWS_FEED_BYTES:
            raise NewsSourceValidationError(
                "Federal Reserve RSS exceeds the configured size limit"
            )
        try:
            content = raw.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise NewsSourceValidationError(
                "Federal Reserve RSS is not valid UTF-8"
            ) from exc
        _reject_unsafe_xml(content)
        if "<rss" not in content or "<channel" not in content:
            raise NewsSourceValidationError(
                "Federal Reserve response is not an RSS document"
            )
        return NewsSourcePayload(
            content=content,
            retrieved_at=retrieved_at,
            source=self.source_name,
            publisher=self.publisher,
            source_url=self.source_url,
            source_type=self.source_type,
            quality_tier=self.quality_tier,
        )


def parse_federal_reserve_rss(content: str) -> Tuple[str, List[RawNewsItem]]:
    """Extract source fields only; do not create events or asset mappings."""
    _reject_unsafe_xml(content)
    try:
        root = ElementTree.fromstring(content)
    except ElementTree.ParseError as exc:
        raise NewsSourceValidationError(
            f"Federal Reserve RSS XML is malformed: {_safe_error(exc)}"
        ) from exc
    if root.tag.casefold() != "rss":
        raise NewsSourceValidationError("Federal Reserve feed root is not rss")
    channel = root.find("channel")
    if channel is None:
        raise NewsSourceValidationError("Federal Reserve RSS has no channel")
    language = _text(channel.find("language")) or "en"
    items = [
        RawNewsItem(
            provider_item_id=_text(element.find("guid")),
            title=_text(element.find("title")),
            description=_text(element.find("description")),
            link=_text(element.find("link")),
            published_at=_text(element.find("pubDate")),
        )
        for element in channel.findall("item")
    ]
    return language, items


def _text(element: Optional[ElementTree.Element]) -> Optional[str]:
    if element is None or element.text is None:
        return None
    value = " ".join(element.text.split())
    return value or None


def _reject_unsafe_xml(content: str) -> None:
    uppercase = content.upper()
    if "<!DOCTYPE" in uppercase or "<!ENTITY" in uppercase:
        raise NewsSourceValidationError(
            "Federal Reserve RSS contains a prohibited XML declaration"
        )


def _safe_error(exc: Exception) -> str:
    return " ".join(str(exc).split())[:240]


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
