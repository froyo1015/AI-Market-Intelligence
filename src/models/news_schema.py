"""Runtime schemas for Phase 6.2-C1 news source ingestion."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo


REPORT_TIMEZONE = ZoneInfo("Asia/Taipei")


@dataclass(frozen=True)
class NewsItem:
    item_id: str
    provider_item_id: Optional[str]
    headline: str
    source_excerpt: Optional[str]
    publisher: str
    provider: str
    source_type: str
    quality_tier: int
    source_url: str
    canonical_url: str
    published_at: datetime
    retrieved_at: datetime
    language: str
    content_hash: str

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["published_at"] = _iso_utc(self.published_at)
        payload["retrieved_at"] = _iso_utc(self.retrieved_at)
        return payload


@dataclass(frozen=True)
class NewsRejection:
    provider_item_id: Optional[str]
    source_url: Optional[str]
    reason_codes: List[str]
    matched_item_id: Optional[str] = None
    matched_event_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NewsItemsArtifact:
    generated_at: datetime
    window_start: datetime
    window_end: datetime
    source: str
    source_url: str
    status: str
    failure_type: Optional[str]
    retryable: bool
    warnings: List[str]
    items: List[NewsItem]
    rejections: List[NewsRejection]
    schema_version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        generated_at = _as_utc(self.generated_at)
        return {
            "schema_version": self.schema_version,
            "artifact_type": "news_items",
            "run_id": generated_at.strftime("run_%Y%m%dT%H%M%SZ_news"),
            "report_date": (
                generated_at.astimezone(REPORT_TIMEZONE).date().isoformat()
            ),
            "generated_at": _iso_utc(generated_at),
            "window_start": _iso_utc(self.window_start),
            "window_end": _iso_utc(self.window_end),
            "source": self.source,
            "source_url": self.source_url,
            "status": self.status,
            "failure_type": self.failure_type,
            "retryable": self.retryable,
            "warnings": list(self.warnings),
            "accepted_count": len(self.items),
            "rejected_count": len(self.rejections),
            "rejections": [rejection.to_dict() for rejection in self.rejections],
            "items": [item.to_dict() for item in self.items],
        }


def _iso_utc(value: datetime) -> str:
    return _as_utc(value).isoformat().replace("+00:00", "Z")


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
