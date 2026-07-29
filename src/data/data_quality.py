"""Presentation-side data freshness assessment for daily market reports."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Mapping, Optional

from src.data.asset_metadata import get_asset_metadata


class FreshnessLevel(str, Enum):
    CURRENT = "current"
    DELAYED = "delayed"
    STALE = "stale"
    FAILED = "failed"
    UNKNOWN = "unknown"


FRESHNESS_PRESENTATION: Mapping[FreshnessLevel, tuple[str, str]] = {
    FreshnessLevel.CURRENT: ("🟢", "資料在日報時效範圍內"),
    FreshnessLevel.DELAYED: ("🟠", "資料延遲，請核對時間"),
    FreshnessLevel.STALE: ("🔴", "資料過期，不宜作即時判斷"),
    FreshnessLevel.FAILED: ("⚫", "資料取得失敗"),
    FreshnessLevel.UNKNOWN: ("⚪", "資料時間未知"),
}


@dataclass(frozen=True)
class FreshnessAssessment:
    level: FreshnessLevel
    indicator: str
    label: str
    age_hours: Optional[float]
    data_timestamp: str
    report_generated_at: str

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["level"] = self.level.value
        return payload

    @property
    def display(self) -> str:
        age = format_age(self.age_hours)
        return f"{self.indicator} {self.level.value} — {self.label}（{age}）"


def assess_record_freshness(
    record: Mapping[str, Any],
    report_generated_at: Any,
) -> FreshnessAssessment:
    """Classify one daily record relative to report generation time."""
    symbol = str(record.get("symbol", ""))
    status = str(record.get("status", "failed"))
    raw_timestamp = record.get("timestamp")
    data_timestamp = raw_timestamp if isinstance(raw_timestamp, str) else "未知"
    report_timestamp = (
        report_generated_at if isinstance(report_generated_at, str) else "未知"
    )

    if status == "failed" or record.get("price") is None:
        return _assessment(
            FreshnessLevel.FAILED,
            None,
            data_timestamp,
            report_timestamp,
        )
    if status == "stale":
        return _assessment(
            FreshnessLevel.STALE,
            _age_hours(data_timestamp, report_timestamp),
            data_timestamp,
            report_timestamp,
        )

    data_time = _parse_timestamp(data_timestamp)
    report_time = _parse_timestamp(report_timestamp)
    if data_time is None or report_time is None:
        return _assessment(
            FreshnessLevel.UNKNOWN,
            None,
            data_timestamp,
            report_timestamp,
        )

    age_hours = (report_time - data_time).total_seconds() / 3600
    if age_hours < -0.1:
        return _assessment(
            FreshnessLevel.UNKNOWN,
            round(age_hours, 2),
            data_timestamp,
            report_timestamp,
        )
    age_hours = max(age_hours, 0.0)

    try:
        metadata = get_asset_metadata(symbol)
    except KeyError:
        return _assessment(
            FreshnessLevel.UNKNOWN,
            round(age_hours, 2),
            data_timestamp,
            report_timestamp,
        )

    if age_hours <= metadata.current_after_hours:
        level = FreshnessLevel.CURRENT
    elif age_hours <= metadata.stale_after_hours:
        level = FreshnessLevel.DELAYED
    else:
        level = FreshnessLevel.STALE

    return _assessment(
        level,
        round(age_hours, 2),
        data_timestamp,
        report_timestamp,
    )


def build_data_quality_context(
    snapshot: Mapping[str, Any],
) -> Dict[str, Any]:
    """Return report-ready metadata, per-record freshness, and a summary."""
    generated_at = snapshot.get("generated_at")
    records = snapshot.get("records")
    raw_records = records if isinstance(records, list) else []
    quality_records: Dict[str, Dict[str, Any]] = {}
    counts = {level.value: 0 for level in FreshnessLevel}
    parsed_times = []

    for raw_record in raw_records:
        if not isinstance(raw_record, dict):
            continue
        symbol = raw_record.get("symbol")
        if not isinstance(symbol, str):
            continue
        try:
            metadata = get_asset_metadata(symbol)
        except KeyError:
            continue
        freshness = assess_record_freshness(raw_record, generated_at)
        counts[freshness.level.value] += 1
        parsed_time = _parse_timestamp(freshness.data_timestamp)
        if parsed_time is not None and freshness.level is not FreshnessLevel.FAILED:
            parsed_times.append(parsed_time)
        quality_records[symbol] = {
            "metadata": metadata.to_dict(),
            "freshness": freshness.to_dict(),
        }

    return {
        "generated_at": generated_at if isinstance(generated_at, str) else "未知",
        "summary": {
            "counts": counts,
            "earliest_data_time": _format_timestamp(min(parsed_times))
            if parsed_times
            else "未知",
            "latest_data_time": _format_timestamp(max(parsed_times))
            if parsed_times
            else "未知",
        },
        "records": quality_records,
    }


def format_age(age_hours: Optional[float]) -> str:
    if age_hours is None:
        return "age unknown"
    if age_hours < 0:
        return "future timestamp"
    if age_hours < 1:
        return "<1h old"
    if age_hours < 48:
        return f"{age_hours:.1f}h old"
    return f"{age_hours / 24:.1f}d old"


def format_quality_counts(counts: Mapping[str, Any]) -> str:
    return (
        f"🟢 {int(counts.get('current', 0))} current · "
        f"🟠 {int(counts.get('delayed', 0))} delayed · "
        f"🔴 {int(counts.get('stale', 0))} stale · "
        f"⚫ {int(counts.get('failed', 0))} failed · "
        f"⚪ {int(counts.get('unknown', 0))} unknown"
    )


def _assessment(
    level: FreshnessLevel,
    age_hours: Optional[float],
    data_timestamp: str,
    report_timestamp: str,
) -> FreshnessAssessment:
    indicator, label = FRESHNESS_PRESENTATION[level]
    return FreshnessAssessment(
        level=level,
        indicator=indicator,
        label=label,
        age_hours=age_hours,
        data_timestamp=data_timestamp,
        report_generated_at=report_timestamp,
    )


def _age_hours(data_timestamp: str, report_timestamp: str) -> Optional[float]:
    data_time = _parse_timestamp(data_timestamp)
    report_time = _parse_timestamp(report_timestamp)
    if data_time is None or report_time is None:
        return None
    return round((report_time - data_time).total_seconds() / 3600, 2)


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value or value == "未知":
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _format_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
