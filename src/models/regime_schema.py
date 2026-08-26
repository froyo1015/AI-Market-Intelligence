"""Schemas for Phase 6.3-B current-condition market regimes."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class RegimeDimension:
    dimension_id: str
    weight: float
    signal_id: str
    rule_id: str
    eligibility: str
    observed_state: str
    contribution: Optional[float]
    weighted_contribution: Optional[float]
    observed_values: List[Dict[str, Any]]
    evidence_refs: Dict[str, List[str]]
    confidence: Dict[str, Any]
    reason_codes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MarketRegimeArtifact:
    run_id: str
    report_date: str
    generated_at: str
    status: str
    classification: Optional[str]
    input_refs: Dict[str, str]
    input_freshness: Dict[str, Any]
    score: Dict[str, Any]
    confidence: Dict[str, Any]
    dimensions: List[RegimeDimension]
    evidence_refs: Dict[str, List[str]]
    warnings: List[str]
    limitations: List[str]
    schema_version: str = "1.0"
    rule_set_version: str = "market_regime_rules_v1"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "artifact_type": "market_regime",
            "run_id": self.run_id,
            "report_date": self.report_date,
            "generated_at": self.generated_at,
            "status": self.status,
            "classification_scope": "current_observed_conditions",
            "classification": self.classification,
            "rule_set_version": self.rule_set_version,
            "input_refs": dict(self.input_refs),
            "input_freshness": dict(self.input_freshness),
            "score": dict(self.score),
            "confidence": dict(self.confidence),
            "dimensions": [item.to_dict() for item in self.dimensions],
            "evidence_refs": {
                key: list(value) for key, value in self.evidence_refs.items()
            },
            "warnings": list(self.warnings),
            "limitations": list(self.limitations),
        }
