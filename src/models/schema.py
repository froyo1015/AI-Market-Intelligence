"""Dataclass schemas for instruments and JSON snapshot output."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class AssetType(str, Enum):
    EQUITY = "equity"
    CRYPTO = "crypto"
    COMMODITY = "commodity"
    FOREX = "forex"


class SnapshotStatus(str, Enum):
    SUCCESS = "success"
    STALE = "stale"
    FAILED = "failed"


@dataclass(frozen=True)
class Instrument:
    symbol: str
    provider_symbol: str
    asset_type: AssetType
    stale_after_days: int


@dataclass(frozen=True)
class MarketSnapshotRecord:
    symbol: str
    asset_type: AssetType
    price: Optional[float]
    daily_change: Optional[float]
    weekly_change: Optional[float]
    sma20: Optional[float]
    volatility_20d: Optional[float]
    trend: str
    timestamp: datetime
    source: str
    status: SnapshotStatus
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["asset_type"] = self.asset_type.value
        payload["status"] = self.status.value
        payload["timestamp"] = _iso_utc(self.timestamp)
        if self.error is None:
            payload.pop("error")
        return payload


@dataclass(frozen=True)
class MarketSnapshot:
    generated_at: datetime
    source: str
    records: List[MarketSnapshotRecord]
    schema_version: str = "1.0"
    change_unit: str = "percent"
    volatility_unit: str = "annualized_percent"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generated_at": _iso_utc(self.generated_at),
            "source": self.source,
            "change_unit": self.change_unit,
            "volatility_unit": self.volatility_unit,
            "records": [record.to_dict() for record in self.records],
        }


def _iso_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return value.isoformat().replace("+00:00", "Z")

