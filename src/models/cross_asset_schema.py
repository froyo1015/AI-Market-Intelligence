"""Schemas for Phase 6.3-A descriptive cross-asset relationships."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ObservedValue:
    asset: str
    metric: str
    value: float
    unit: str
    as_of: str
    observation_id: str
    source_id: str
    evidence_bundle_ids: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RelationshipSignal:
    signal_id: str
    rule_id: str
    signal_type: str
    relationship_kind: str
    label: str
    state: str
    condition_met: Optional[bool]
    required_assets: List[str]
    observed_values: List[ObservedValue]
    rule_evaluation: Dict[str, Any]
    evidence_refs: Dict[str, List[str]]
    confidence: Dict[str, Any]
    data_quality: Dict[str, Any]
    limitations: List[str]

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["observed_values"] = [item.to_dict() for item in self.observed_values]
        return payload


@dataclass(frozen=True)
class MarketSignalsArtifact:
    run_id: str
    report_date: str
    generated_at: str
    status: str
    input_run_id: str
    warnings: List[str]
    signals: List[RelationshipSignal]
    schema_version: str = "1.0"
    rule_set_version: str = "cross_asset_rules_v1"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "artifact_type": "market_signals",
            "run_id": self.run_id,
            "report_date": self.report_date,
            "generated_at": self.generated_at,
            "status": self.status,
            "input_artifact": "evidence_bundle.json",
            "input_run_id": self.input_run_id,
            "rule_set_version": self.rule_set_version,
            "warnings": list(self.warnings),
            "signal_count": len(self.signals),
            "observed_count": sum(item.state == "observed" for item in self.signals),
            "signals": [item.to_dict() for item in self.signals],
        }
