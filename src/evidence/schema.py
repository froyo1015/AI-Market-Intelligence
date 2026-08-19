"""Versioned schemas for Phase 6.1 observation and evidence artifacts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class ArtifactStatus(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    FAILED = "failed"


class ObservationType(str, Enum):
    MARKET_PRICE = "market_price"
    MARKET_FEATURE = "market_feature"


class EvidenceRelation(str, Enum):
    OBSERVED = "observed"
    ASSOCIATED = "associated"
    SUPPORTED_INTERPRETATION = "supported_interpretation"
    UNCONFIRMED = "unconfirmed"


class ConfidenceLabel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INSUFFICIENT = "insufficient"


@dataclass(frozen=True)
class SourceReference:
    source_id: str
    provider: str
    publisher: str
    source_type: str
    quality_tier: int
    title: str
    url: Optional[str]
    published_at: Optional[str]
    retrieved_at: str
    content_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Observation:
    observation_id: str
    observation_type: ObservationType
    subject: str
    metric: str
    value: Any
    unit: Optional[str]
    period: Optional[str]
    as_of: str
    source_id: str
    status: str
    calculation: Optional[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["observation_type"] = self.observation_type.value
        return payload


@dataclass(frozen=True)
class EvidenceBundle:
    evidence_id: str
    claim_type: str
    statement: str
    relation: EvidenceRelation
    event_ids: List[str]
    observation_ids: List[str]
    supporting_source_ids: List[str]
    contradicting_evidence_ids: List[str]
    confidence_score: float
    confidence_label: ConfidenceLabel
    limitations: List[str]

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["relation"] = self.relation.value
        payload["confidence_label"] = self.confidence_label.value
        return payload


def confidence_label(score: float) -> ConfidenceLabel:
    """Map a normalized score to the frozen data-contract label."""
    if score >= 0.80:
        return ConfidenceLabel.HIGH
    if score >= 0.55:
        return ConfidenceLabel.MEDIUM
    if score >= 0.30:
        return ConfidenceLabel.LOW
    return ConfidenceLabel.INSUFFICIENT
