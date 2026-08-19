"""Build canonical observations and evidence from the existing market snapshot."""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
from zoneinfo import ZoneInfo

from src.data.data_quality import FreshnessLevel, assess_record_freshness
from src.evidence.schema import (
    ArtifactStatus,
    EvidenceBundle,
    EvidenceRelation,
    Observation,
    ObservationType,
    SourceReference,
    confidence_label,
)


SCHEMA_VERSION = "1.1"
REPORT_TIMEZONE = ZoneInfo("Asia/Taipei")
SOURCE_URLS = {
    "yahoo_finance": "https://finance.yahoo.com/",
}

METRICS: Sequence[Tuple[str, ObservationType, Optional[str], Optional[str], str]] = (
    ("price", ObservationType.MARKET_PRICE, None, "latest", "market_snapshot_import_v1"),
    (
        "daily_change",
        ObservationType.MARKET_FEATURE,
        "percent",
        "daily",
        "daily_change_v1",
    ),
    (
        "weekly_change",
        ObservationType.MARKET_FEATURE,
        "percent",
        "weekly",
        "weekly_change_v1",
    ),
    ("sma20", ObservationType.MARKET_FEATURE, None, "20d", "sma20_v1"),
    (
        "volatility_20d",
        ObservationType.MARKET_FEATURE,
        "annualized_percent",
        "20d",
        "volatility_20d_v1",
    ),
    ("trend", ObservationType.MARKET_FEATURE, None, "20d", "trend_vs_sma20_v1"),
)


class EvidenceBuildError(ValueError):
    """Raised when the existing snapshot cannot satisfy the v1 contract."""


def build_observation_artifact(
    snapshot: Mapping[str, Any],
    macro_snapshot: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Convert market snapshot records without changing the source pipeline."""
    market_generated_at, records = _snapshot_header(snapshot)
    generated_at = _latest_generated_at(market_generated_at, macro_snapshot)
    run_id = _run_id(generated_at)
    warnings: List[str] = []
    observations: List[Observation] = []
    providers: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)

    for index, raw_record in enumerate(records):
        if not isinstance(raw_record, dict):
            warnings.append(f"record[{index}] ignored: record is not an object")
            continue

        symbol = raw_record.get("symbol")
        timestamp = raw_record.get("timestamp")
        provider = raw_record.get("source") or snapshot.get("source")
        status = raw_record.get("status")
        if not isinstance(symbol, str) or not symbol:
            warnings.append(f"record[{index}] ignored: symbol is missing")
            continue
        if not isinstance(timestamp, str) or not timestamp:
            warnings.append(f"{symbol} ignored: timestamp is missing")
            continue
        if not isinstance(provider, str) or not provider:
            warnings.append(f"{symbol} ignored: source is missing")
            continue
        if status == "failed":
            warnings.append(f"{symbol} omitted: market snapshot status is failed")
            providers[provider].append(raw_record)
            continue
        if status not in {"success", "stale"}:
            warnings.append(f"{symbol} ignored: unsupported status {status!r}")
            continue
        freshness = assess_record_freshness(raw_record, generated_at)
        if freshness.level is FreshnessLevel.STALE:
            status = "stale"
        if status == "stale":
            warnings.append(f"{symbol} observations are stale")

        providers[provider].append(raw_record)
        source_id = _source_id(provider)
        for metric, observation_type, default_unit, period, rule_id in METRICS:
            value = raw_record.get(metric)
            if value is None:
                warnings.append(f"{symbol}.{metric} omitted: value is missing")
                continue
            unit = _metric_unit(symbol, metric, default_unit)
            calculation = None
            if observation_type is ObservationType.MARKET_FEATURE:
                calculation = {
                    "rule_id": rule_id,
                    "input_ids": [],
                    "source_artifact": "market_snapshot.json",
                }
            observations.append(
                Observation(
                    observation_id=_observation_id(symbol, metric, timestamp),
                    observation_type=observation_type,
                    subject=symbol,
                    metric=_canonical_metric(metric),
                    value=value,
                    unit=unit,
                    period=period,
                    as_of=timestamp,
                    source_id=source_id,
                    status=status,
                    calculation=calculation,
                    asset_mapping=[symbol],
                    confidence_score=0.65 if status == "stale" else 0.95,
                    confidence_label=confidence_label(
                        0.65 if status == "stale" else 0.95
                    ),
                )
            )

    sources = [
        _build_source_reference(provider, market_generated_at, provider_records)
        for provider, provider_records in sorted(providers.items())
    ]
    if macro_snapshot is not None:
        macro_observations, macro_sources, macro_warnings = _macro_observations(
            macro_snapshot
        )
        observations.extend(macro_observations)
        sources.extend(macro_sources)
        warnings.extend(macro_warnings)
    status = _artifact_status(observations, warnings)
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "observations",
        "run_id": run_id,
        "report_date": _report_date(generated_at),
        "generated_at": generated_at,
        "status": status.value,
        "warnings": warnings,
        "sources": [source.to_dict() for source in sources],
        "observations": [observation.to_dict() for observation in observations],
    }


def build_evidence_artifact(
    observation_artifact: Mapping[str, Any],
) -> Dict[str, Any]:
    """Build one non-causal market-move evidence bundle per usable asset."""
    observations = observation_artifact.get("observations")
    if not isinstance(observations, list):
        raise EvidenceBuildError("observation artifact must contain observations")

    by_subject: Dict[str, Dict[str, Mapping[str, Any]]] = defaultdict(dict)
    for observation in observations:
        if not isinstance(observation, dict):
            continue
        subject = observation.get("subject")
        metric = observation.get("metric")
        if isinstance(subject, str) and isinstance(metric, str):
            by_subject[subject][metric] = observation

    warnings = list(_string_list(observation_artifact.get("warnings")))
    bundles: List[EvidenceBundle] = []
    for symbol in sorted(by_subject):
        indexed = by_subject[symbol]
        daily = indexed.get("daily_change_pct") or indexed.get("daily_change_bps")
        if daily is None or not _is_number(daily.get("value")):
            warnings.append(f"{symbol} evidence omitted: daily change is unavailable")
            continue

        referenced = [daily]
        price = indexed.get("price")
        if price is not None:
            referenced.insert(0, price)
        observation_ids = [str(item["observation_id"]) for item in referenced]
        source_ids = sorted({str(item["source_id"]) for item in referenced})
        stale = any(item.get("status") == "stale" for item in referenced)
        input_confidence = [
            float(item.get("confidence_score"))
            for item in referenced
            if _is_number(item.get("confidence_score"))
        ]
        confidence_score = min(input_confidence) if input_confidence else 0.0
        is_macro = daily.get("observation_type") == ObservationType.MACRO_VALUE.value
        limitations = [
            "Daily macro proxy observations do not identify the cause of the move."
            if is_macro
            else "Daily market observations do not identify the cause of the move."
        ]
        if stale:
            limitations.append("One or more supporting observations are stale.")
        bundles.append(
            EvidenceBundle(
                evidence_id=_evidence_id(symbol, str(daily.get("as_of"))),
                claim_type="macro_move" if is_macro else "market_move",
                statement=_move_statement(
                    symbol,
                    float(daily["value"]),
                    str(daily.get("unit")),
                ),
                relation=EvidenceRelation.OBSERVED,
                event_ids=[],
                observation_ids=observation_ids,
                supporting_source_ids=source_ids,
                contradicting_evidence_ids=[],
                confidence_score=confidence_score,
                confidence_label=confidence_label(confidence_score),
                affected_assets=sorted(
                    {
                        asset
                        for item in referenced
                        for asset in _string_list(item.get("asset_mapping"))
                    }
                ),
                limitations=limitations,
            )
        )

    inherited_status = observation_artifact.get("status")
    if not bundles:
        status = ArtifactStatus.FAILED
    elif inherited_status == "complete" and not warnings:
        status = ArtifactStatus.COMPLETE
    else:
        status = ArtifactStatus.PARTIAL
    return {
        "schema_version": observation_artifact.get("schema_version", SCHEMA_VERSION),
        "artifact_type": "evidence",
        "run_id": observation_artifact.get("run_id"),
        "report_date": observation_artifact.get("report_date"),
        "generated_at": observation_artifact.get("generated_at"),
        "status": status.value,
        "warnings": warnings,
        "evidence": [bundle.to_dict() for bundle in bundles],
    }


def _snapshot_header(
    snapshot: Mapping[str, Any],
) -> Tuple[str, Sequence[Any]]:
    generated_at = snapshot.get("generated_at")
    records = snapshot.get("records")
    if not isinstance(generated_at, str) or len(generated_at) < 10:
        raise EvidenceBuildError("market snapshot generated_at is missing")
    if not isinstance(records, list):
        raise EvidenceBuildError("market snapshot records must be a list")
    return generated_at, records


def _artifact_status(
    observations: Sequence[Observation],
    warnings: Sequence[str],
) -> ArtifactStatus:
    if not observations:
        return ArtifactStatus.FAILED
    if warnings or any(item.status == "stale" for item in observations):
        return ArtifactStatus.PARTIAL
    return ArtifactStatus.COMPLETE


def _build_source_reference(
    provider: str,
    generated_at: str,
    records: Sequence[Mapping[str, Any]],
) -> SourceReference:
    canonical = json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    publisher = "Yahoo Finance" if provider == "yahoo_finance" else provider
    return SourceReference(
        source_id=_source_id(provider),
        provider=provider,
        publisher=publisher,
        source_type="market_data",
        quality_tier=3,
        title=f"{publisher} market snapshot",
        url=SOURCE_URLS.get(provider),
        published_at=None,
        retrieved_at=generated_at,
        content_hash=f"sha256:{digest}",
    )


def _canonical_metric(metric: str) -> str:
    return {
        "daily_change": "daily_change_pct",
        "weekly_change": "weekly_change_pct",
    }.get(metric, metric)


def _metric_unit(
    symbol: str,
    metric: str,
    default_unit: Optional[str],
) -> Optional[str]:
    if metric in {"price", "sma20"}:
        return {
            "GOLD": "USD_per_troy_ounce",
            "EURUSD": "USD_per_EUR",
            "USDJPY": "JPY_per_USD",
        }.get(symbol, "USD")
    return default_unit


def _move_statement(symbol: str, value: float, unit: str) -> str:
    magnitude = _format_number(abs(value))
    suffix = " basis points" if unit == "basis_points" else "%"
    if value > 0:
        return f"{symbol} increased {magnitude}{suffix} over the latest daily interval."
    if value < 0:
        return f"{symbol} decreased {magnitude}{suffix} over the latest daily interval."
    return f"{symbol} was unchanged over the latest daily interval."


def _macro_observations(
    macro_snapshot: Mapping[str, Any],
) -> Tuple[List[Observation], List[SourceReference], List[str]]:
    generated_at = macro_snapshot.get("generated_at")
    records = macro_snapshot.get("records")
    if not isinstance(generated_at, str):
        raise EvidenceBuildError("macro snapshot generated_at is missing")
    if not isinstance(records, list):
        raise EvidenceBuildError("macro snapshot records must be a list")

    observations: List[Observation] = []
    sources: List[SourceReference] = []
    warnings: List[str] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            warnings.append(f"macro record[{index}] ignored: record is not an object")
            continue
        symbol = record.get("symbol")
        provider = record.get("source") or macro_snapshot.get("source")
        timestamp = record.get("timestamp")
        status = record.get("status")
        if not isinstance(symbol, str) or not symbol:
            warnings.append(f"macro record[{index}] ignored: symbol is missing")
            continue
        if not isinstance(provider, str) or not provider:
            warnings.append(f"{symbol} macro record ignored: source is missing")
            continue
        source_id = _source_id(f"{provider}_{symbol}")
        sources.append(
            _build_macro_source_reference(source_id, provider, generated_at, record)
        )
        if status == "failed":
            warnings.append(f"{symbol} macro observations omitted: status is failed")
            continue
        if status not in {"success", "stale"}:
            warnings.append(f"{symbol} macro record ignored: unsupported status {status!r}")
            continue
        if not isinstance(timestamp, str) or not timestamp:
            warnings.append(f"{symbol} macro record ignored: timestamp is missing")
            continue
        if status == "stale":
            warnings.append(f"{symbol} macro observations are stale")

        mapping = list(_string_list(record.get("asset_mapping")))
        score = record.get("confidence_score")
        confidence_score = float(score) if _is_number(score) else 0.0
        metrics = (
            (
                str(record.get("metric")),
                record.get("value"),
                str(record.get("value_unit")),
                "latest",
                None,
            ),
            (
                str(record.get("change_metric")),
                record.get("daily_change"),
                str(record.get("change_unit")),
                "daily",
                f"macro_{record.get('change_metric')}_v1",
            ),
            (
                str(record.get("change_metric")).replace("daily_", "weekly_"),
                record.get("weekly_change"),
                str(record.get("change_unit")),
                "weekly",
                f"macro_weekly_{record.get('change_metric')}_v1",
            ),
        )
        for metric, value, unit, period, rule_id in metrics:
            if value is None:
                warnings.append(f"{symbol}.{metric} omitted: value is missing")
                continue
            calculation = None
            if rule_id is not None:
                calculation = {
                    "rule_id": rule_id,
                    "input_ids": [],
                    "source_artifact": "macro_snapshot.json",
                }
            observations.append(
                Observation(
                    observation_id=_observation_id(symbol, metric, timestamp),
                    observation_type=ObservationType.MACRO_VALUE,
                    subject=symbol,
                    metric=metric,
                    value=value,
                    unit=unit,
                    period=period,
                    as_of=timestamp,
                    source_id=source_id,
                    status=status,
                    calculation=calculation,
                    asset_mapping=mapping,
                    confidence_score=confidence_score,
                    confidence_label=confidence_label(confidence_score),
                )
            )
    return observations, sources, warnings


def _build_macro_source_reference(
    source_id: str,
    provider: str,
    generated_at: str,
    record: Mapping[str, Any],
) -> SourceReference:
    canonical = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    publisher = "Yahoo Finance" if provider == "yahoo_finance" else provider
    url = record.get("source_url")
    return SourceReference(
        source_id=source_id,
        provider=provider,
        publisher=publisher,
        source_type="macro_market_data",
        quality_tier=3,
        title=f"{record.get('name', record.get('symbol'))} macro proxy",
        url=url if isinstance(url, str) else None,
        published_at=None,
        retrieved_at=generated_at,
        content_hash=f"sha256:{digest}",
    )


def _latest_generated_at(
    market_generated_at: str,
    macro_snapshot: Optional[Mapping[str, Any]],
) -> str:
    if macro_snapshot is None:
        return market_generated_at
    macro_generated_at = macro_snapshot.get("generated_at")
    if not isinstance(macro_generated_at, str):
        raise EvidenceBuildError("macro snapshot generated_at is missing")
    candidates = (market_generated_at, macro_generated_at)
    try:
        return max(
            candidates,
            key=lambda value: datetime.fromisoformat(value.replace("Z", "+00:00")),
        )
    except ValueError as exc:
        raise EvidenceBuildError("snapshot generated_at is invalid") from exc


def _format_number(value: float) -> str:
    return format(value, ".10g")


def _run_id(generated_at: str) -> str:
    return f"run_{_slug(generated_at)}"


def _report_date(generated_at: str) -> str:
    try:
        parsed = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceBuildError("market snapshot generated_at is invalid") from exc
    if parsed.tzinfo is None:
        raise EvidenceBuildError("market snapshot generated_at must include timezone")
    return parsed.astimezone(REPORT_TIMEZONE).date().isoformat()


def _source_id(provider: str) -> str:
    return f"src_{_slug(provider)}"


def _observation_id(symbol: str, metric: str, timestamp: str) -> str:
    return f"obs_{_slug(symbol)}_{_slug(_canonical_metric(metric))}_{_slug(timestamp)}"


def _evidence_id(symbol: str, timestamp: str) -> str:
    return f"evd_{_slug(symbol)}_market_move_{_slug(timestamp)}"


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _string_list(value: Any) -> Sequence[str]:
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, str))
