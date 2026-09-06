"""Schemas for deterministic Top Market Intelligence output."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class TopIntelligenceItem:
    rank: int
    item_id: str
    type: str
    story_key: str
    source_object_id: str
    headline: str
    why: str
    monitor: str
    total_score: int
    score_breakdown: Dict[str, int]
    primary_theme: str
    related_assets: List[str]
    evidence_refs: Dict[str, List[str]]
    source_refs: List[str]
    timestamps: Dict[str, List[str]]
    freshness_status: str = "current"
    validation_status: str = "validated"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TopIntelligenceArtifact:
    run_id: str
    report_date: str
    generated_at: str
    status: str
    input_refs: Dict[str, str]
    candidate_count: int
    eligible_count: int
    items: List[TopIntelligenceItem]
    warnings: List[str]
    limitations: List[str]
    schema_version: str = "1.0"
    rule_set_version: str = "top_intelligence_rules_v1"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "artifact_type": "top_intelligence",
            "run_id": self.run_id,
            "report_date": self.report_date,
            "generated_at": self.generated_at,
            "status": self.status,
            "selection_scope": "current_validated_market_intelligence",
            "rule_set_version": self.rule_set_version,
            "input_refs": dict(self.input_refs),
            "candidate_count": self.candidate_count,
            "eligible_count": self.eligible_count,
            "selected_count": len(self.items),
            "items": [item.to_dict() for item in self.items],
            "warnings": list(self.warnings),
            "limitations": list(self.limitations),
        }
