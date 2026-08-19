"""Schemas for the Phase 6.2-A macro snapshot artifact."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class MacroSnapshotRecord:
    symbol: str
    provider_symbol: str
    name: str
    metric: str
    value: Optional[float]
    value_unit: str
    daily_change: Optional[float]
    weekly_change: Optional[float]
    change_metric: str
    change_unit: str
    timestamp: datetime
    source: str
    source_url: str
    semantic_reference_url: str
    status: str
    price_basis: str
    asset_mapping: List[str]
    confidence_score: float
    confidence_label: str
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["timestamp"] = _iso_utc(self.timestamp)
        if self.error is None:
            payload.pop("error")
        return payload


@dataclass(frozen=True)
class MacroSnapshot:
    generated_at: datetime
    source: str
    records: List[MacroSnapshotRecord]
    schema_version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        statuses = [record.status for record in self.records]
        if statuses and all(status == "failed" for status in statuses):
            status = "failed"
        elif any(status != "success" for status in statuses):
            status = "partial"
        else:
            status = "complete"
        return {
            "schema_version": self.schema_version,
            "artifact_type": "macro_snapshot",
            "generated_at": _iso_utc(self.generated_at),
            "source": self.source,
            "status": status,
            "records": [record.to_dict() for record in self.records],
        }


def _iso_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return value.isoformat().replace("+00:00", "Z")
