"""Shared Phase 7.1-B freshness metadata schema."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, Optional


FRESHNESS_CONTRACT_VERSION = "1.0"
DEFAULT_STALE_AFTER_SECONDS = 48 * 60 * 60
STALE_AFTER_SECONDS = {
    "market_snapshot": 48 * 60 * 60,
    "macro_snapshot": 120 * 60 * 60,
    "economic_calendar": 24 * 60 * 60,
    "news_items": 30 * 60 * 60,
    "events": 30 * 60 * 60,
    "observations": 48 * 60 * 60,
    "evidence": 48 * 60 * 60,
    "evidence_bundle": 48 * 60 * 60,
    "market_signals": 48 * 60 * 60,
    "market_regime": 48 * 60 * 60,
    "risk_monitor": 48 * 60 * 60,
    "daily_intelligence": 48 * 60 * 60,
}


class FreshnessStatus(str, Enum):
    CURRENT = "current"
    STALE = "stale"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class FreshnessMetadata:
    source_timestamp: Optional[str]
    retrieved_at: Optional[str]
    generated_at: str
    age_seconds: Optional[float]
    freshness_status: FreshnessStatus
    freshness_basis: str
    stale_after_seconds: Optional[int]
    freshness_contract_version: str = FRESHNESS_CONTRACT_VERSION

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["freshness_status"] = self.freshness_status.value
        return payload
