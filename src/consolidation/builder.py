"""Build a loss-aware factual evidence boundary from existing artifacts."""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from src.models.evidence_bundle_schema import (
    ConsolidatedEvidenceArtifact,
    ConsolidatedEvidenceBundle,
    ConsolidationRejection,
    CoverageRecord,
)


REPORT_TIMEZONE = ZoneInfo("Asia/Taipei")
INPUT_STALE_AFTER = timedelta(hours=48)
CONSOLIDATION_RULE_ID = "exact_fact_consolidation_v1"
INPUT_ARTIFACT_TYPES = {
    "observations.json": "observations",
    "evidence.json": "evidence",
    "economic_calendar.json": "economic_calendar",
    "events.json": "events",
}
CAUSAL_OR_PREDICTIVE_LANGUAGE = re.compile(
    r"\b(?:because|because of|caused|causes|due to|led to|driven by|"
    r"bullish|bearish|will rise|will fall|will increase|will decrease)\b|"
    r"因為|由於|導致|造成|驅動|看漲|看跌|將會上升|將會下跌",
    re.IGNORECASE,
)


class ConsolidationBuildError(ValueError):
    """Raised when the consolidator itself cannot satisfy its contract."""


def build_consolidated_evidence_artifact(
    observations_artifact: Optional[Mapping[str, Any]],
    evidence_artifact: Optional[Mapping[str, Any]],
    calendar_artifact: Optional[Mapping[str, Any]],
    news_events_artifact: Optional[Mapping[str, Any]],
    now: Optional[datetime] = None,
    input_errors: Optional[Mapping[str, str]] = None,
) -> ConsolidatedEvidenceArtifact:
    generated = _as_utc(now or datetime.now(timezone.utc))
    generated_at = _iso_utc(generated)
    errors = dict(input_errors or {})
    rejections: List[ConsolidationRejection] = []
    stale_record_ids: Set[str] = set()

    sources, observations, observation_coverage = _collect_observations(
        observations_artifact,
        generated,
        rejections,
        stale_record_ids,
        errors.get("observations.json"),
    )
    events: Dict[str, Dict[str, Any]] = {}
    event_sources: Dict[str, Set[str]] = defaultdict(set)
    event_artifacts: Dict[str, str] = {}

    calendar_coverage = _collect_calendar_events(
        calendar_artifact,
        generated,
        sources,
        events,
        event_sources,
        event_artifacts,
        rejections,
        stale_record_ids,
        errors.get("economic_calendar.json"),
    )
    news_coverage = _collect_news_events(
        news_events_artifact,
        generated,
        sources,
        events,
        event_sources,
        event_artifacts,
        rejections,
        stale_record_ids,
        errors.get("events.json"),
    )

    evidence_records, evidence_coverage = _collect_evidence(
        evidence_artifact,
        observations,
        events,
        sources,
        generated,
        rejections,
        stale_record_ids,
        errors.get("evidence.json"),
    )

    input_run_ids = _input_run_ids(
        observations_artifact,
        evidence_artifact,
        calendar_artifact,
        news_events_artifact,
    )
    bundles, referenced_observations, referenced_events = _evidence_bundles(
        evidence_records,
        observations,
        events,
        sources,
        event_sources,
        event_artifacts,
        stale_record_ids,
        generated_at,
        input_run_ids,
    )
    for observation_id in sorted(set(observations).difference(referenced_observations)):
        observation = observations[observation_id]
        source_id = str(observation["source_id"])
        bundles.append(
            _build_bundle(
                bundle_type="observation",
                key_payload={"observation_id": observation_id},
                related_assets=_strings(observation.get("asset_mapping")),
                source_records=[sources[source_id]],
                observations=[observation],
                events=[],
                evidence_records=[],
                input_artifacts=["observations.json"],
                input_run_ids=input_run_ids.get("observations.json", []),
                stale_record_ids=stale_record_ids,
                generated_at=generated_at,
            )
        )
    for event_id in sorted(set(events).difference(referenced_events)):
        event = events[event_id]
        artifact_name = event_artifacts[event_id]
        bundle_type = (
            "calendar_event"
            if artifact_name == "economic_calendar.json"
            else "news_event"
        )
        bundles.append(
            _build_bundle(
                bundle_type=bundle_type,
                key_payload={"event_id": event_id, "type": bundle_type},
                related_assets=_event_assets(event),
                source_records=[
                    sources[source_id]
                    for source_id in sorted(event_sources[event_id])
                ],
                observations=[],
                events=[event],
                evidence_records=[],
                input_artifacts=[artifact_name],
                input_run_ids=input_run_ids.get(artifact_name, []),
                stale_record_ids=stale_record_ids,
                generated_at=generated_at,
            )
        )

    bundles.sort(key=lambda item: (item.type, item.id))
    coverage = [
        observation_coverage["market_observations"],
        observation_coverage["macro_observations"],
        calendar_coverage,
        news_coverage,
        evidence_coverage,
    ]
    warnings = _artifact_warnings(coverage, rejections)
    if not bundles:
        status = "unavailable"
    elif any(item.status != "available" for item in coverage) or rejections:
        status = "partial"
    elif any(item.data_quality["status"] != "available" for item in bundles):
        status = "partial"
    else:
        status = "available"

    run_digest = hashlib.sha256(
        "|".join(
            [generated_at]
            + sorted(run_id for values in input_run_ids.values() for run_id in values)
        ).encode("utf-8")
    ).hexdigest()[:16]
    return ConsolidatedEvidenceArtifact(
        run_id=f"run_{generated:%Y%m%dT%H%M%SZ}_consolidated_{run_digest}",
        report_date=generated.astimezone(REPORT_TIMEZONE).date().isoformat(),
        generated_at=generated_at,
        status=status,
        warnings=warnings,
        coverage=coverage,
        bundles=bundles,
        rejections=rejections,
    )


def _collect_observations(
    artifact: Optional[Mapping[str, Any]],
    now: datetime,
    rejections: List[ConsolidationRejection],
    stale_record_ids: Set[str],
    input_error: Optional[str],
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]], Dict[str, CoverageRecord]]:
    sources: Dict[str, Dict[str, Any]] = {}
    observations: Dict[str, Dict[str, Any]] = {}
    artifact_name = "observations.json"
    root_status, root_warnings = _input_header(artifact, artifact_name, input_error)
    if artifact is not None and root_status != "failed":
        for raw_source in _record_objects(
            artifact.get("sources"), "source", artifact_name, rejections
        ):
            source_id = _text(raw_source.get("source_id"))
            reasons = _source_reasons(raw_source)
            if source_id is None or source_id in sources:
                reasons.append("missing_or_duplicate_source_id")
            if reasons:
                rejections.append(
                    _rejection("source", source_id, artifact_name, reasons)
                )
                continue
            sources[source_id] = dict(raw_source)

        for raw_observation in _record_objects(
            artifact.get("observations"),
            "observation",
            artifact_name,
            rejections,
        ):
            observation_id = _text(raw_observation.get("observation_id"))
            reasons: List[str] = []
            if observation_id is None or observation_id in observations:
                reasons.append("missing_or_duplicate_observation_id")
            observation_type = raw_observation.get("observation_type")
            if observation_type not in {"market_price", "market_feature", "macro_value"}:
                reasons.append("unsupported_observation_type")
            source_id = _text(raw_observation.get("source_id"))
            if source_id not in sources:
                reasons.append("missing_source_reference")
            if not _valid_timestamp(raw_observation.get("as_of")):
                reasons.append("invalid_observation_timestamp")
            if raw_observation.get("status") not in {"success", "stale"}:
                reasons.append("invalid_observation_status")
            if raw_observation.get("value") is None:
                reasons.append("missing_observation_value")
            if not _is_string_list(raw_observation.get("asset_mapping")):
                reasons.append("invalid_asset_mapping")
            if reasons:
                rejections.append(
                    _rejection("observation", observation_id, artifact_name, reasons)
                )
                continue
            observations[str(observation_id)] = dict(raw_observation)

    artifact_stale = artifact is not None and _artifact_is_stale(artifact, now)
    if artifact_stale:
        stale_record_ids.update(observations)
    for observation_id, observation in observations.items():
        if observation.get("status") == "stale":
            stale_record_ids.add(observation_id)

    by_type = {
        "market_observations": [
            item
            for item in observations.values()
            if item.get("observation_type") in {"market_price", "market_feature"}
        ],
        "macro_observations": [
            item
            for item in observations.values()
            if item.get("observation_type") == "macro_value"
        ],
    }
    result: Dict[str, CoverageRecord] = {}
    for input_type, records in by_type.items():
        record_ids = {str(item["observation_id"]) for item in records}
        stale_count = len(record_ids.intersection(stale_record_ids))
        warnings = list(root_warnings)
        if artifact_stale:
            warnings.append(f"{artifact_name} is older than 48 hours.")
        if root_status == "failed" or not records:
            status = "unavailable"
        elif stale_count or root_status == "partial" or any(
            rejection.input_artifact == artifact_name
            and rejection.record_type in {"source", "observation"}
            for rejection in rejections
        ):
            status = "partial"
        else:
            status = "available"
        result[input_type] = CoverageRecord(
            input_type=input_type,
            artifact=artifact_name,
            run_id=_artifact_string(artifact, "run_id"),
            generated_at=_artifact_string(artifact, "generated_at"),
            status=status,
            record_count=len(records),
            stale_record_count=stale_count,
            warnings=_unique(warnings),
        )
    return sources, observations, result


def _collect_calendar_events(
    artifact: Optional[Mapping[str, Any]],
    now: datetime,
    sources: Dict[str, Dict[str, Any]],
    events: Dict[str, Dict[str, Any]],
    event_sources: Dict[str, Set[str]],
    event_artifacts: Dict[str, str],
    rejections: List[ConsolidationRejection],
    stale_record_ids: Set[str],
    input_error: Optional[str],
) -> CoverageRecord:
    artifact_name = "economic_calendar.json"
    root_status, warnings = _input_header(artifact, artifact_name, input_error)
    accepted: List[str] = []
    if artifact is not None and root_status != "failed":
        for raw_event in _record_objects(
            artifact.get("events"),
            "calendar_event",
            artifact_name,
            rejections,
        ):
            event_id = _text(raw_event.get("event_id"))
            reasons: List[str] = []
            for field in ("name", "source", "publisher"):
                if _text(raw_event.get(field)) is None:
                    reasons.append(f"missing_{field}")
            if event_id is None or event_id in events:
                reasons.append("missing_or_duplicate_event_id")
            if not _valid_timestamp(raw_event.get("scheduled_at")):
                reasons.append("invalid_scheduled_at")
            if not _valid_timestamp(raw_event.get("retrieved_at")):
                reasons.append("invalid_retrieved_at")
            if not _valid_https(raw_event.get("source_url")):
                reasons.append("invalid_source_url")
            if not _valid_hash(raw_event.get("content_hash")):
                reasons.append("invalid_content_hash")
            if not _is_string_list(raw_event.get("affected_assets")):
                reasons.append("invalid_affected_assets")
            if reasons:
                rejections.append(
                    _rejection("calendar_event", event_id, artifact_name, reasons)
                )
                continue
            event_id = str(event_id)
            source_id = _calendar_source_id(raw_event)
            source_record = {
                "source_id": source_id,
                "provider": raw_event["source"],
                "publisher": raw_event["publisher"],
                "source_type": "official_calendar",
                "quality_tier": 1,
                "title": raw_event["name"],
                "url": raw_event["source_url"],
                "published_at": None,
                "retrieved_at": raw_event["retrieved_at"],
                "content_hash": raw_event["content_hash"],
            }
            sources[source_id] = source_record
            events[event_id] = dict(raw_event)
            event_sources[event_id].add(source_id)
            event_artifacts[event_id] = artifact_name
            accepted.append(event_id)

    artifact_stale = artifact is not None and _artifact_is_stale(artifact, now)
    if artifact_stale:
        stale_record_ids.update(accepted)
        warnings.append(f"{artifact_name} is older than 48 hours.")
        if root_status != "failed":
            root_status = "partial"
    return _coverage(
        "economic_calendar",
        artifact_name,
        artifact,
        root_status,
        accepted,
        stale_record_ids,
        warnings,
        rejections,
    )


def _collect_news_events(
    artifact: Optional[Mapping[str, Any]],
    now: datetime,
    sources: Dict[str, Dict[str, Any]],
    events: Dict[str, Dict[str, Any]],
    event_sources: Dict[str, Set[str]],
    event_artifacts: Dict[str, str],
    rejections: List[ConsolidationRejection],
    stale_record_ids: Set[str],
    input_error: Optional[str],
) -> CoverageRecord:
    artifact_name = "events.json"
    root_status, warnings = _input_header(artifact, artifact_name, input_error)
    accepted: List[str] = []
    if artifact is not None and root_status != "failed":
        for raw_event in _record_objects(
            artifact.get("events"),
            "news_event",
            artifact_name,
            rejections,
        ):
            event_id = _text(raw_event.get("event_id"))
            reasons: List[str] = []
            if event_id is None or event_id in events:
                reasons.append("missing_or_duplicate_event_id")
            if _text(raw_event.get("event_type")) is None:
                reasons.append("missing_event_type")
            if _text(raw_event.get("title")) is None:
                reasons.append("missing_title")
            if raw_event.get("status") != "success":
                reasons.append("invalid_event_status")
            if not _is_string_list(raw_event.get("candidate_assets")):
                reasons.append("invalid_candidate_assets")
            raw_source_refs = raw_event.get("source_refs")
            if not isinstance(raw_source_refs, list) or any(
                not isinstance(item, dict) for item in raw_source_refs
            ):
                reasons.append("invalid_source_references")
                source_refs: List[Mapping[str, Any]] = []
            else:
                source_refs = raw_source_refs
            if not source_refs:
                reasons.append("missing_source_references")
            valid_sources: List[Tuple[str, Dict[str, Any]]] = []
            for raw_source in source_refs:
                source_id = _text(raw_source.get("source_id"))
                source_reasons = _source_reasons(raw_source)
                if source_id is None:
                    source_reasons.append("missing_source_id")
                if source_reasons:
                    reasons.extend(
                        f"source_{reason}" for reason in source_reasons
                    )
                else:
                    valid_sources.append((str(source_id), dict(raw_source)))
            if reasons:
                rejections.append(
                    _rejection("news_event", event_id, artifact_name, reasons)
                )
                continue
            event_id = str(event_id)
            for source_id, source_record in valid_sources:
                existing = sources.get(source_id)
                if existing is not None and existing != source_record:
                    rejections.append(
                        _rejection(
                            "news_event",
                            event_id,
                            artifact_name,
                            ["conflicting_source_id"],
                        )
                    )
                    break
                sources[source_id] = source_record
                event_sources[event_id].add(source_id)
            else:
                events[event_id] = dict(raw_event)
                event_artifacts[event_id] = artifact_name
                accepted.append(event_id)
                if raw_event.get("lifecycle_status") in {"expired", "retracted"}:
                    stale_record_ids.add(event_id)

    artifact_stale = artifact is not None and _artifact_is_stale(artifact, now)
    if artifact_stale:
        stale_record_ids.update(accepted)
        warnings.append(f"{artifact_name} is older than 48 hours.")
        if root_status != "failed":
            root_status = "partial"
    return _coverage(
        "news_events",
        artifact_name,
        artifact,
        root_status,
        accepted,
        stale_record_ids,
        warnings,
        rejections,
    )


def _collect_evidence(
    artifact: Optional[Mapping[str, Any]],
    observations: Mapping[str, Dict[str, Any]],
    events: Mapping[str, Dict[str, Any]],
    sources: Mapping[str, Dict[str, Any]],
    now: datetime,
    rejections: List[ConsolidationRejection],
    stale_record_ids: Set[str],
    input_error: Optional[str],
) -> Tuple[List[Dict[str, Any]], CoverageRecord]:
    artifact_name = "evidence.json"
    root_status, warnings = _input_header(artifact, artifact_name, input_error)
    accepted: List[Dict[str, Any]] = []
    seen_ids: Set[str] = set()
    if artifact is not None and root_status != "failed":
        for raw_evidence in _record_objects(
            artifact.get("evidence"),
            "evidence",
            artifact_name,
            rejections,
        ):
            evidence_id = _text(raw_evidence.get("evidence_id"))
            reasons: List[str] = []
            if evidence_id is None or evidence_id in seen_ids:
                reasons.append("missing_or_duplicate_evidence_id")
            statement = _text(raw_evidence.get("statement"))
            if statement is None:
                reasons.append("missing_statement")
            elif CAUSAL_OR_PREDICTIVE_LANGUAGE.search(statement):
                reasons.append("prohibited_causal_or_predictive_language")
            observation_ids = _strings(raw_evidence.get("observation_ids"))
            event_ids = _strings(raw_evidence.get("event_ids"))
            source_ids = _strings(raw_evidence.get("supporting_source_ids"))
            if not _is_string_list(raw_evidence.get("observation_ids")):
                reasons.append("invalid_observation_ids")
            if not _is_string_list(raw_evidence.get("event_ids")):
                reasons.append("invalid_event_ids")
            if not _is_string_list(raw_evidence.get("supporting_source_ids")):
                reasons.append("invalid_source_ids")
            if any(item not in observations for item in observation_ids):
                reasons.append("missing_observation_reference")
            if any(item not in events for item in event_ids):
                reasons.append("missing_event_reference")
            if any(item not in sources for item in source_ids):
                reasons.append("missing_source_reference")
            if not observation_ids and not event_ids:
                reasons.append("evidence_has_no_factual_record")
            if reasons:
                rejections.append(
                    _rejection("evidence", evidence_id, artifact_name, reasons)
                )
                continue
            seen_ids.add(str(evidence_id))
            accepted.append(dict(raw_evidence))

    accepted_ids = [str(item["evidence_id"]) for item in accepted]
    artifact_stale = artifact is not None and _artifact_is_stale(artifact, now)
    if artifact_stale:
        stale_record_ids.update(accepted_ids)
        warnings.append(f"{artifact_name} is older than 48 hours.")
        if root_status != "failed":
            root_status = "partial"
    coverage = _coverage(
        "existing_evidence",
        artifact_name,
        artifact,
        root_status,
        accepted_ids,
        stale_record_ids,
        warnings,
        rejections,
    )
    return accepted, coverage


def _evidence_bundles(
    evidence_records: Sequence[Dict[str, Any]],
    observations: Mapping[str, Dict[str, Any]],
    events: Mapping[str, Dict[str, Any]],
    sources: Mapping[str, Dict[str, Any]],
    event_sources: Mapping[str, Set[str]],
    event_artifacts: Mapping[str, str],
    stale_record_ids: Set[str],
    generated_at: str,
    input_run_ids: Mapping[str, List[str]],
) -> Tuple[List[ConsolidatedEvidenceBundle], Set[str], Set[str]]:
    groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    group_keys: Dict[str, Dict[str, Any]] = {}
    for record in evidence_records:
        key_payload = {
            "claim_type": record.get("claim_type"),
            "statement": " ".join(str(record.get("statement", "")).casefold().split()),
            "relation": record.get("relation"),
            "related_assets": sorted(_strings(record.get("affected_assets"))),
        }
        key = _hash_payload(key_payload)
        group_keys[key] = key_payload
        groups[key].append(record)

    bundles: List[ConsolidatedEvidenceBundle] = []
    referenced_observations: Set[str] = set()
    referenced_events: Set[str] = set()
    for key in sorted(groups):
        records = sorted(groups[key], key=lambda item: str(item["evidence_id"]))
        observation_ids = sorted(
            {
                item
                for record in records
                for item in _strings(record.get("observation_ids"))
            }
        )
        event_ids = sorted(
            {
                item
                for record in records
                for item in _strings(record.get("event_ids"))
            }
        )
        source_ids = {
            item
            for record in records
            for item in _strings(record.get("supporting_source_ids"))
        }
        source_ids.update(
            str(observations[item]["source_id"]) for item in observation_ids
        )
        for event_id in event_ids:
            source_ids.update(event_sources[event_id])
        related_assets = {
            item
            for record in records
            for item in _strings(record.get("affected_assets"))
        }
        for observation_id in observation_ids:
            related_assets.update(
                _strings(observations[observation_id].get("asset_mapping"))
            )
        for event_id in event_ids:
            related_assets.update(_event_assets(events[event_id]))
        input_artifacts = {"evidence.json"}
        if observation_ids:
            input_artifacts.add("observations.json")
        input_artifacts.update(event_artifacts[event_id] for event_id in event_ids)
        run_ids = sorted(
            {
                run_id
                for artifact_name in input_artifacts
                for run_id in input_run_ids.get(artifact_name, [])
            }
        )
        bundles.append(
            _build_bundle(
                bundle_type="evidence_fact",
                key_payload=group_keys[key],
                related_assets=sorted(related_assets),
                source_records=[sources[item] for item in sorted(source_ids)],
                observations=[observations[item] for item in observation_ids],
                events=[events[item] for item in event_ids],
                evidence_records=records,
                input_artifacts=sorted(input_artifacts),
                input_run_ids=run_ids,
                stale_record_ids=stale_record_ids,
                generated_at=generated_at,
            )
        )
        referenced_observations.update(observation_ids)
        referenced_events.update(event_ids)
    return bundles, referenced_observations, referenced_events


def _build_bundle(
    bundle_type: str,
    key_payload: Mapping[str, Any],
    related_assets: Iterable[str],
    source_records: Sequence[Dict[str, Any]],
    observations: Sequence[Dict[str, Any]],
    events: Sequence[Dict[str, Any]],
    evidence_records: Sequence[Dict[str, Any]],
    input_artifacts: Sequence[str],
    input_run_ids: Sequence[str],
    stale_record_ids: Set[str],
    generated_at: str,
) -> ConsolidatedEvidenceBundle:
    deduplication_key = _hash_payload(key_payload)
    observation_ids = sorted(str(item["observation_id"]) for item in observations)
    event_ids = sorted(str(item["event_id"]) for item in events)
    evidence_ids = sorted(str(item["evidence_id"]) for item in evidence_records)
    source_ids = sorted(str(item["source_id"]) for item in source_records)
    linked_ids = set(observation_ids + event_ids + evidence_ids)
    stale_ids = sorted(linked_ids.intersection(stale_record_ids))
    timestamps = _timestamps(
        observations,
        events,
        source_records,
        generated_at,
    )
    if stale_ids:
        freshness_status = "stale" if set(stale_ids) == linked_ids else "mixed"
    elif any(
        timestamps[field]
        for field in (
            "observed_at",
            "occurred_at",
            "scheduled_at",
            "published_at",
            "retrieved_at",
        )
    ):
        freshness_status = "fresh"
    else:
        freshness_status = "unknown"
    as_of_candidates = sorted(
        {
            timestamp
            for field in (
                "observed_at",
                "occurred_at",
                "published_at",
                "retrieved_at",
            )
            for timestamp in timestamps[field]
        }
    )
    issues = ["stale_record"] if stale_ids else []
    quality_status = "partial" if issues else "available"
    return ConsolidatedEvidenceBundle(
        id=f"ebd_{deduplication_key.removeprefix('sha256:')[:20]}",
        type=bundle_type,
        related_assets=sorted(set(related_assets)),
        source_records=sorted(source_records, key=lambda item: str(item["source_id"])),
        observations=sorted(
            observations, key=lambda item: str(item["observation_id"])
        ),
        events=sorted(events, key=lambda item: str(item["event_id"])),
        evidence_records=sorted(
            evidence_records, key=lambda item: str(item["evidence_id"])
        ),
        timestamps=timestamps,
        verification_level=_verification_level(
            source_records,
            observations,
            evidence_records,
        ),
        data_quality={
            "status": quality_status,
            "issues": issues,
            "source_count": len(source_records),
            "observation_count": len(observations),
            "event_count": len(events),
            "evidence_count": len(evidence_records),
        },
        freshness={
            "status": freshness_status,
            "as_of": as_of_candidates[-1] if as_of_candidates else None,
            "stale_record_ids": stale_ids,
        },
        provenance={
            "input_artifacts": sorted(set(input_artifacts)),
            "input_run_ids": sorted(set(input_run_ids)),
            "source_ids": source_ids,
            "observation_ids": observation_ids,
            "event_ids": event_ids,
            "evidence_ids": evidence_ids,
            "consolidation_rule_id": CONSOLIDATION_RULE_ID,
            "deduplication_key": deduplication_key,
        },
    )


def _timestamps(
    observations: Sequence[Mapping[str, Any]],
    events: Sequence[Mapping[str, Any]],
    sources: Sequence[Mapping[str, Any]],
    generated_at: str,
) -> Dict[str, Any]:
    return {
        "observed_at": _timestamp_values(observations, "as_of"),
        "occurred_at": _timestamp_values(events, "occurred_at"),
        "scheduled_at": _timestamp_values(events, "scheduled_at"),
        "published_at": _timestamp_values(sources, "published_at"),
        "retrieved_at": _timestamp_values(sources, "retrieved_at"),
        "consolidated_at": generated_at,
    }


def _verification_level(
    sources: Sequence[Mapping[str, Any]],
    observations: Sequence[Mapping[str, Any]],
    evidence_records: Sequence[Mapping[str, Any]],
) -> str:
    if any(
        source.get("quality_tier") == 1
        and source.get("source_type") in {"official", "official_calendar"}
        for source in sources
    ):
        return "official"
    independent_origins = {
        (str(item.get("provider")), str(item.get("publisher")))
        for item in sources
    }
    if len(independent_origins) >= 2:
        return "corroborated"
    if observations and any(item.get("relation") == "observed" for item in evidence_records):
        return "observed"
    if sources:
        return "single_source"
    return "unverified"


def _coverage(
    input_type: str,
    artifact_name: str,
    artifact: Optional[Mapping[str, Any]],
    root_status: str,
    accepted_ids: Sequence[str],
    stale_record_ids: Set[str],
    warnings: Sequence[str],
    rejections: Sequence[ConsolidationRejection],
) -> CoverageRecord:
    stale_count = len(set(accepted_ids).intersection(stale_record_ids))
    has_rejections = any(item.input_artifact == artifact_name for item in rejections)
    if root_status == "failed":
        status = "unavailable"
    elif root_status == "partial" or stale_count or has_rejections:
        status = "partial"
    else:
        status = "available"
    return CoverageRecord(
        input_type=input_type,
        artifact=artifact_name,
        run_id=_artifact_string(artifact, "run_id"),
        generated_at=_artifact_string(artifact, "generated_at"),
        status=status,
        record_count=len(accepted_ids),
        stale_record_count=stale_count,
        warnings=_unique(warnings),
    )


def _input_header(
    artifact: Optional[Mapping[str, Any]],
    artifact_name: str,
    input_error: Optional[str],
) -> Tuple[str, List[str]]:
    if artifact is None:
        reason = input_error or f"{artifact_name} is missing."
        return "failed", [reason]
    if artifact.get("artifact_type") != INPUT_ARTIFACT_TYPES[artifact_name]:
        return "failed", [f"{artifact_name} has an invalid artifact_type."]
    if _text(artifact.get("run_id")) is None:
        return "failed", [f"{artifact_name} has no run_id."]
    if not _valid_timestamp(artifact.get("generated_at")):
        return "failed", [f"{artifact_name} has an invalid generated_at."]
    status = artifact.get("status")
    if status not in {"complete", "partial", "failed"}:
        return "failed", [f"{artifact_name} has an invalid status."]
    warnings = _strings(artifact.get("warnings"))
    if input_error:
        warnings.append(input_error)
        status = "failed"
    return str(status), warnings


def _source_reasons(source: Mapping[str, Any]) -> List[str]:
    reasons: List[str] = []
    for field in ("provider", "publisher", "source_type", "title"):
        if _text(source.get(field)) is None:
            reasons.append(f"missing_{field}")
    if source.get("quality_tier") not in {1, 2, 3}:
        reasons.append("invalid_quality_tier")
    url = source.get("url")
    if url is not None and not _valid_https(url):
        reasons.append("invalid_source_url")
    if not _valid_timestamp(source.get("retrieved_at")):
        reasons.append("invalid_retrieved_at")
    published_at = source.get("published_at")
    if published_at is not None and not _valid_timestamp(published_at):
        reasons.append("invalid_published_at")
    if not _valid_hash(source.get("content_hash")):
        reasons.append("invalid_content_hash")
    return reasons


def _calendar_source_id(event: Mapping[str, Any]) -> str:
    key = f"{event['source']}|{event['source_url']}|{event['content_hash']}"
    return f"src_calendar_{hashlib.sha256(key.encode('utf-8')).hexdigest()[:16]}"


def _input_run_ids(*artifacts: Optional[Mapping[str, Any]]) -> Dict[str, List[str]]:
    names = (
        "observations.json",
        "evidence.json",
        "economic_calendar.json",
        "events.json",
    )
    result: Dict[str, List[str]] = {}
    for name, artifact in zip(names, artifacts):
        run_id = _artifact_string(artifact, "run_id")
        result[name] = [run_id] if run_id else []
    return result


def _artifact_warnings(
    coverage: Sequence[CoverageRecord],
    rejections: Sequence[ConsolidationRejection],
) -> List[str]:
    warnings = [
        f"{item.input_type} coverage is {item.status}."
        for item in coverage
        if item.status != "available"
    ]
    if rejections:
        warnings.append(
            f"{len(rejections)} invalid input record(s) were rejected during consolidation."
        )
    return warnings


def _event_assets(event: Mapping[str, Any]) -> List[str]:
    return sorted(
        set(
            _strings(event.get("affected_assets"))
            + _strings(event.get("candidate_assets"))
        )
    )


def _rejection(
    record_type: str,
    record_id: Optional[str],
    artifact: str,
    reasons: Iterable[str],
) -> ConsolidationRejection:
    return ConsolidationRejection(
        record_type=record_type,
        record_id=record_id,
        input_artifact=artifact,
        reason_codes=sorted(set(reasons)),
    )


def _hash_payload(payload: Mapping[str, Any]) -> str:
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return f"sha256:{digest}"


def _artifact_is_stale(artifact: Mapping[str, Any], now: datetime) -> bool:
    generated_at = artifact.get("generated_at")
    if not _valid_timestamp(generated_at):
        return True
    return now - _parse_timestamp(str(generated_at)) > INPUT_STALE_AFTER


def _timestamp_values(records: Iterable[Mapping[str, Any]], field: str) -> List[str]:
    return sorted(
        {
            _iso_utc(_parse_timestamp(str(record[field])))
            for record in records
            if record.get(field) is not None and _valid_timestamp(record.get(field))
        }
    )


def _record_objects(
    value: Any,
    record_type: str,
    artifact_name: str,
    rejections: List[ConsolidationRejection],
) -> List[Mapping[str, Any]]:
    if not isinstance(value, list):
        rejections.append(
            _rejection(
                record_type,
                None,
                artifact_name,
                ["record_collection_is_not_a_list"],
            )
        )
        return []
    records: List[Mapping[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            rejections.append(
                _rejection(
                    record_type,
                    None,
                    artifact_name,
                    ["record_is_not_an_object"],
                )
            )
            continue
        records.append(item)
    return records


def _strings(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _is_string_list(value: Any) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, str) and bool(item) for item in value
    )


def _text(value: Any) -> Optional[str]:
    return value if isinstance(value, str) and value.strip() else None


def _valid_hash(value: Any) -> bool:
    return isinstance(value, str) and bool(
        re.fullmatch(r"sha256:[0-9a-f]{64}", value)
    )


def _valid_https(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlsplit(value)
    return parsed.scheme.casefold() == "https" and bool(parsed.hostname)


def _valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return _parse_timestamp(value).tzinfo is not None
    except ValueError:
        return False


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _iso_utc(value: datetime) -> str:
    return _as_utc(value).isoformat().replace("+00:00", "Z")


def _artifact_string(
    artifact: Optional[Mapping[str, Any]], field: str
) -> Optional[str]:
    if artifact is None:
        return None
    return _text(artifact.get(field))


def _unique(values: Iterable[str]) -> List[str]:
    return list(dict.fromkeys(value for value in values if value))
