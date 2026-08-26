"""Canonical runtime schemas for Phase 6.2-C2 normalized news events."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from src.evidence.schema import SourceReference


@dataclass(frozen=True)
class EventNormalization:
    input_item_ids: List[str]
    method: str
    rule_version: str
    normalized_action: str
    event_key_fields: List[str]
    mapping_rule_ids: List[str]
    extraction_quality_score: float
    mapping_quality_score: float
    verification_level: str
    deduplication_rule_id: str
    deduplication_score: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NormalizedNewsEvent:
    event_id: str
    event_type: str
    status: str
    title: str
    summary: Optional[str]
    occurred_at: Optional[str]
    scheduled_at: Optional[str]
    country_codes: List[str]
    entity_ids: List[str]
    candidate_assets: List[str]
    topics: List[str]
    source_refs: List[SourceReference]
    canonical_hash: str
    duplicate_of: Optional[str]
    normalization: EventNormalization
    event_version: int
    lifecycle_status: str
    lifecycle_updated_at: str
    lifecycle_reason_code: str
    retraction_source_ids: List[str]

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["source_refs"] = [source.to_dict() for source in self.source_refs]
        payload["normalization"] = self.normalization.to_dict()
        return payload


@dataclass(frozen=True)
class NormalizationRejection:
    item_id: str
    reason_codes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EventsArtifact:
    run_id: str
    report_date: str
    generated_at: str
    status: str
    warnings: List[str]
    input_artifact: str
    input_run_id: str
    events: List[NormalizedNewsEvent]
    normalization_rejections: List[NormalizationRejection]
    schema_version: str = "1.1"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "artifact_type": "events",
            "run_id": self.run_id,
            "report_date": self.report_date,
            "generated_at": self.generated_at,
            "status": self.status,
            "warnings": list(self.warnings),
            "input_artifact": self.input_artifact,
            "input_run_id": self.input_run_id,
            "event_count": len(self.events),
            "normalization_rejection_count": len(
                self.normalization_rejections
            ),
            "normalization_rejections": [
                rejection.to_dict()
                for rejection in self.normalization_rejections
            ],
            "events": [event.to_dict() for event in self.events],
        }
